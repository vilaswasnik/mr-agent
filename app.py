import streamlit as st
import os
import json
from dotenv import load_dotenv
from pathlib import Path
from io import BytesIO
import zipfile
import xml.etree.ElementTree as ET
import hashlib
import hmac
import time
import secrets
from src.github_client import GitHubManager
from src.ai_client import AIAssistant
from src.agents import Orchestrator
from src import memory as mem
from src.dice_client import DiceClient
from src.user_memory_db import (
    init_db,
    get_profile,
    upsert_profile,
    add_note,
    list_notes,
    record_interaction,
    get_recent_interactions,
)


def _load_runtime_secrets():
    """Load secrets from local .env and Render Secret Files."""
    # Do not override already-defined environment variables.
    load_dotenv(override=False)

    # Render Secret Files can expose a full .env file at /etc/secrets/.env
    secret_env_file = Path("/etc/secrets/.env")
    if secret_env_file.exists():
        load_dotenv(dotenv_path=secret_env_file, override=False)

    # Or individual secret files like /etc/secrets/GITHUB_TOKEN
    for key in (
        "GITHUB_TOKEN",
        "OPENAI_API_KEY",
        "APP_ADMIN_USERNAME",
        "APP_ADMIN_PASSWORD",
        "APP_ADMIN_PASSWORD_HASH",
    ):
        if os.getenv(key):
            continue
        key_file = Path(f"/etc/secrets/{key}")
        if key_file.exists():
            value = key_file.read_text(encoding="utf-8").strip()
            if value:
                os.environ[key] = value


_load_runtime_secrets()

st.set_page_config(page_title="Mr. Agent", page_icon="🤖", layout="wide")

# ==================== LOGIN AUTHENTICATION ====================
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCKOUT_SECONDS = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "300"))
PBKDF2_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "120000"))
APP_ADMIN_USERNAME = os.getenv("APP_ADMIN_USERNAME", "").strip()
APP_ADMIN_PASSWORD = os.getenv("APP_ADMIN_PASSWORD", "")
APP_ADMIN_PASSWORD_HASH = os.getenv("APP_ADMIN_PASSWORD_HASH", "").strip()


def _hash_password(password):
    """Return PBKDF2 hash string: pbkdf2_sha256$iters$salt$hash"""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${hashed}"


def _verify_password(password, stored_value):
    """Verify plain-text legacy or PBKDF2 hashed credential value."""
    if stored_value.startswith("pbkdf2_sha256$"):
        try:
            _, iter_str, salt, expected = stored_value.split("$", 3)
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iter_str),
            ).hex()
            return hmac.compare_digest(actual, expected)
        except ValueError:
            return False
    return hmac.compare_digest(password, stored_value)


def _save_credentials(users):
    creds_file = Path("credentials.json")
    with open(creds_file, "w") as f:
        json.dump({"users": users}, f, indent=2)


def load_credentials():
    """Load user credentials from credentials.json"""
    creds_file = Path("credentials.json")
    
    # If credentials.json doesn't exist, create from template or use default
    if not creds_file.exists():
        template_file = Path("credentials.json.example")
        if template_file.exists():
            # Copy from template
            with open(template_file) as f:
                creds = json.load(f)
        else:
            # Create default
            creds = {"users": {"admin": "change_me_after_first_login"}}
        
        # Save credentials.json
        with open(creds_file, "w") as f:
            json.dump(creds, f, indent=2)
    
    # Load and return credentials
    with open(creds_file) as f:
        return json.load(f).get("users", {})


def _authenticate_user(username, password):
    # Primary auth source for production: Render environment variables.
    if APP_ADMIN_USERNAME:
        if username != APP_ADMIN_USERNAME:
            return False
        if APP_ADMIN_PASSWORD_HASH:
            return _verify_password(password, APP_ADMIN_PASSWORD_HASH)
        if APP_ADMIN_PASSWORD:
            return hmac.compare_digest(password, APP_ADMIN_PASSWORD)

    users = load_credentials()
    stored = users.get(username)
    if not stored:
        return False

    is_valid = _verify_password(password, stored)
    if is_valid and not stored.startswith("pbkdf2_sha256$"):
        # One-time migration from legacy plain text to PBKDF2 hash.
        users[username] = _hash_password(password)
        _save_credentials(users)

    return is_valid


def _init_login_security_state():
    if "auth_attempts" not in st.session_state:
        st.session_state.auth_attempts = 0
    if "auth_locked_until" not in st.session_state:
        st.session_state.auth_locked_until = 0

def login_page():
    """Display login page"""
    _init_login_security_state()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🤖 Mr. Agent")
        st.markdown("---")
        st.write("### Login to Continue")

        now = int(time.time())
        is_locked = now < st.session_state.auth_locked_until
        if is_locked:
            wait_seconds = st.session_state.auth_locked_until - now
            st.error(f"Too many failed attempts. Try again in {wait_seconds} seconds.")
        
        username = st.text_input("Username", key="login_user", placeholder="Enter username")
        password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter password")
        
        if st.button("Login", use_container_width=True, disabled=is_locked):
            if _authenticate_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.auth_attempts = 0
                st.session_state.auth_locked_until = 0
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.session_state.auth_attempts += 1
                remaining = MAX_LOGIN_ATTEMPTS - st.session_state.auth_attempts
                if st.session_state.auth_attempts >= MAX_LOGIN_ATTEMPTS:
                    st.session_state.auth_locked_until = int(time.time()) + LOGIN_LOCKOUT_SECONDS
                    st.error(
                        f"❌ Too many failed attempts. Login locked for {LOGIN_LOCKOUT_SECONDS} seconds."
                    )
                else:
                    st.error(f"❌ Invalid credentials. {remaining} attempts remaining.")

def check_authentication():
    """Check if user is authenticated"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        login_page()
        st.stop()

check_authentication()

init_db()

# ================================================================

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stHeader"] { background-color: #0d1117; }
    h1, h2, h3 { color: #58a6ff; }
</style>
""", unsafe_allow_html=True)

github_token = os.getenv("GITHUB_TOKEN", "").strip()
openai_key = os.getenv("OPENAI_API_KEY", "").strip()

if not github_token or not openai_key or github_token.startswith("your_github"):
    missing = []
    if not github_token or github_token.startswith("your_github"):
        missing.append("GITHUB_TOKEN")
    if not openai_key:
        missing.append("OPENAI_API_KEY")
    st.error(
        "Missing required environment variables: "
        + ", ".join(missing)
        + ". Set them in Render Environment or Secret Files (/etc/secrets)."
    )
    st.stop()

@st.cache_resource
def init_clients():
    gh = GitHubManager(github_token)
    ai = AIAssistant(openai_key)
    return gh, ai, Orchestrator(gh, ai)

try:
    gh_manager, ai_assistant, orchestrator = init_clients()
    dice_client = DiceClient()
except Exception as e:
    st.error(f"Failed to connect: {e}")
    st.stop()

TOOLS = [
    {"type":"function","function":{"name":"get_profile","description":"Get the user's GitHub profile info.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"list_repos","description":"List all GitHub repositories owned by the user.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"review_code","description":"Review a specific file in a repo and return feedback.","parameters":{"type":"object","properties":{"repo":{"type":"string"},"file_path":{"type":"string"}},"required":["repo","file_path"]}}},
    {"type":"function","function":{"name":"fix_file","description":"Fix issues in a file and create a Pull Request.","parameters":{"type":"object","properties":{"repo":{"type":"string"},"file_path":{"type":"string"}},"required":["repo","file_path"]}}},
    {"type":"function","function":{"name":"analyze_profile","description":"Analyze GitHub profile and suggest improvements and new project ideas.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_dice_apply_queue","description":"Return pending Dice apply queue entries from local state.","parameters":{"type":"object","properties":{"limit":{"type":"integer","description":"Maximum queue items to return"}},"required":[]}}},
    {"type":"function","function":{"name":"rank_dice_apply_queue","description":"Rank pending Dice apply queue by fastest submission first (Easy Apply first), then recency.","parameters":{"type":"object","properties":{"limit":{"type":"integer","description":"Maximum ranked entries to return"}},"required":[]}}},
        {"type":"function","function":{"name":"audit_repos","description":"Audit all repos for missing READMEs and descriptions, auto-fix them.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"triage_issues","description":"Triage open issues across all repos: classify, label, and comment with priority.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"review_open_prs","description":"AI-review all open PRs and post code review comments.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"stale_pr_cleanup","description":"Detect and comment on PRs inactive for 30+ days.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"generate_tests","description":"Generate unit tests for source files missing test coverage and open PRs.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"check_dependencies","description":"Audit dependency files for outdated/vulnerable packages and open update PRs.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"fix_issue_pr","description":"Autonomously fix bug issues by writing code and opening a PR.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"self_reflect","description":"Run self-reflection on the last run log and post insights as a GitHub issue.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"run_task","description":"Run a natural-language goal using the multi-agent planner.","parameters":{"type":"object","properties":{"goal":{"type":"string","description":"The goal to accomplish"}},"required":["goal"]}}}
    ,{"type":"function","function":{"name":"run_mid_mode","description":"Run Mid mode autonomous sweep: triage issues, stale PR cleanup, PR reviews, dependency checks.","parameters":{"type":"object","properties":{"dry_run":{"type":"boolean"},"max_prs":{"type":"integer"},"max_comments":{"type":"integer"}},"required":[]}}}
    ,{"type":"function","function":{"name":"run_advanced_mode","description":"Run Advanced autonomous sweep: Mid mode + issue fix PRs + test generation + self-reflection.","parameters":{"type":"object","properties":{"dry_run":{"type":"boolean"},"max_prs":{"type":"integer"},"max_comments":{"type":"integer"}},"required":[]}}}
]

def execute_tool(name, args):
    if name == "get_profile":
        return json.dumps(gh_manager.get_user_profile())
    elif name == "list_repos":
        repos = gh_manager.get_repositories()
        return json.dumps([{k: v for k, v in r.items() if k != "obj"} for r in repos])
    elif name == "review_code":
        code = gh_manager.get_file_content(args["repo"], args["file_path"])
        if not code:
            return f"Could not retrieve {args['file_path']} from {args['repo']}."
        return ai_assistant.review_code(code, args["file_path"])
    elif name == "fix_file":
        code = gh_manager.get_file_content(args["repo"], args["file_path"])
        if not code:
            return f"Could not retrieve {args['file_path']} from {args['repo']}."
        fixed = ai_assistant.fix_code(code, args["file_path"])
        from github import Github
        g = Github(github_token)
        repo_obj = g.get_repo(f"{gh_manager.user.login}/{args['repo']}")
        pr_url = gh_manager.create_fix_pr(repo_obj, args["file_path"], fixed)
        return f"PR created: {pr_url}" if pr_url else "Failed to create PR."
    elif name == "analyze_profile":
        profile = gh_manager.get_user_profile()
        tips = ai_assistant.analyze_profile(profile)
        ideas = ai_assistant.suggest_new_projects(profile)
        return f"Profile Optimizations:\n{tips}\n\nProject Ideas:\n{ideas}"
    elif name == "get_dice_apply_queue":
        limit = max(1, int(args.get("limit", 50)))
        queue = dice_client.get_apply_queue("pending_manual_apply")[:limit]
        rows = []
        for item in queue:
            job = item.get("job", {})
            rows.append(
                {
                    "queue_key": item.get("key"),
                    "title": job.get("title", "Unknown"),
                    "company": job.get("company", "Unknown"),
                    "location": job.get("location", "Unknown"),
                    "url": job.get("url", ""),
                    "created_at": item.get("created_at", 0),
                }
            )
        return json.dumps({"pending_count": len(dice_client.get_apply_queue("pending_manual_apply")), "items": rows}, indent=2)
    elif name == "rank_dice_apply_queue":
        limit = max(1, int(args.get("limit", 10)))
        queue = dice_client.get_apply_queue("pending_manual_apply")
        ranked = []
        for item in queue:
            job = item.get("job", {})
            title = str(job.get("title", "")).lower()
            score = 0
            if "easy apply" in title:
                score += 100
            elif "apply now" in title:
                score += 80
            else:
                score += 50
            score += int(item.get("created_at", 0)) // 100000
            ranked.append((score, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        out = []
        for _, item in ranked[:limit]:
            job = item.get("job", {})
            out.append(
                {
                    "queue_key": item.get("key"),
                    "title": job.get("title", "Unknown"),
                    "company": job.get("company", "Unknown"),
                    "url": job.get("url", ""),
                }
            )
        return json.dumps({"pending_count": len(queue), "ranked": out}, indent=2)
    elif name == "audit_repos":
        repos = gh_manager.get_repositories()
        results = []
        for repo in repos:
            if not repo["has_readme"]:
                content = ai_assistant.generate_readme(repo["name"], repo["description"])
                pr = gh_manager.create_readme_pr(repo["obj"], content)
                results.append(f"README PR for `{repo['name']}`: {pr or 'already exists'}")
            if not repo["description"] or repo["description"] == "No description":
                desc = ai_assistant.generate_repo_description(repo["name"], repo["language"])
                gh_manager.update_repo_description(repo["obj"], desc)
                results.append(f"Description updated for `{repo['name']}`: {desc}")
        return "\n".join(results) if results else "All repositories are in good shape!"
    elif name == "triage_issues":
        results = orchestrator.run_triage()
        return "\n".join(results) if results else "No untriaged issues found."
    elif name == "review_open_prs":
        results = orchestrator.run_pr_reviews()
        return "\n".join(results) if results else "No open PRs found."
    elif name == "stale_pr_cleanup":
        results = orchestrator.run_stale_pr_cleanup()
        return "\n".join(results) if results else "No stale PRs found."
    elif name == "generate_tests":
        results = orchestrator.run_test_generation()
        return "\n".join(results) if results else "All source files already have tests or none detected."
    elif name == "check_dependencies":
        results = orchestrator.run_dependency_check()
        return "\n".join(results) if results else "All dependencies are up to date."
    elif name == "fix_issue_pr":
        results = orchestrator.run_issue_fix_pipeline()
        return "\n".join(results) if results else "No fixable bug issues found."
    elif name == "self_reflect":
        reflection, issue_url = orchestrator.run_self_reflection(ai_assistant)
        return f"{reflection}\n\nIssue: {issue_url}"
    elif name == "run_task":
        plan, results = orchestrator.run_natural_language_task(args["goal"], ai_assistant)
        plan_text = "\n".join(f"Step {s.get('step')}: {s.get('tool')} — {s.get('reason')}" for s in plan)
        result_text = "\n".join(results)
        return f"**Plan:**\n{plan_text}\n\n**Results:**\n{result_text}"
    elif name == "run_mid_mode":
        local = Orchestrator(
            gh_manager,
            ai_assistant,
            dry_run=args.get("dry_run", False),
            max_prs=max(0, int(args.get("max_prs", 5))),
            max_comments=max(0, int(args.get("max_comments", 20))),
        )
        actions = local.run_mid_mode()
        return "\n".join(actions) if actions else "Mid mode completed. No actions needed."
    elif name == "run_advanced_mode":
        local = Orchestrator(
            gh_manager,
            ai_assistant,
            dry_run=args.get("dry_run", False),
            max_prs=max(0, int(args.get("max_prs", 5))),
            max_comments=max(0, int(args.get("max_comments", 20))),
        )
        result = local.run_advanced_mode(include_reflection=True)
        actions = result.get("actions", [])
        reflection_issue = result.get("reflection_issue")
        text = "\n".join(actions) if actions else "Advanced mode completed. No actions needed."
        if reflection_issue:
            text += f"\n\nSelf-reflection issue: {reflection_issue}"
        return text
    return "Unknown tool."

def _build_user_memory_context(username):
    profile = get_profile(username)
    recent = get_recent_interactions(username, limit=5)

    profile_lines = [
        f"Current role: {profile.get('current_role', '').strip() or 'Not set'}",
        f"Target roles: {profile.get('target_roles', '').strip() or 'Not set'}",
        f"Preferred locations: {profile.get('preferred_locations', '').strip() or 'Not set'}",
        f"Core skills: {profile.get('core_skills', '').strip() or 'Not set'}",
        f"Work style: {profile.get('work_style', '').strip() or 'Not set'}",
        f"Goals: {profile.get('goals', '').strip() or 'Not set'}",
    ]

    recent_lines = []
    for item in recent:
        um = (item.get("user_message") or "")[:180]
        if um:
            recent_lines.append(f"- {um}")

    return (
        "User Memory Profile:\n"
        + "\n".join(profile_lines)
        + "\nRecent user requests:\n"
        + ("\n".join(recent_lines) if recent_lines else "- No prior requests yet")
    )


def run_agent(user_message, history, user_context=""):
    messages = [
        {"role": "system", "content": (
            "You are Mr. Agent, an elite autonomous GitHub assistant with direct access to the user's GitHub account. "
            "Use your tools to fetch real data, review code, create PRs, and audit repositories. "
            "Always take action when asked — don't just advise. Be concise, sharp, and technical. Use markdown."
        )}
    ]

    if user_context:
        messages.append(
            {
                "role": "system",
                "content": (
                    "Use this persistent user memory context to personalize responses and recommendations.\n"
                    + user_context
                ),
            }
        )

    messages = messages + history + [{"role": "user", "content": user_message}]

    while True:
        response = ai_assistant.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = execute_tool(tc.function.name, args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        else:
            return msg.content


def extract_resume_text(uploaded_file):
    """Extract plain text from uploaded resume files."""
    suffix = Path(uploaded_file.name).suffix.lower()
    raw = uploaded_file.getvalue()

    if suffix in {".txt", ".md"}:
        try:
            return raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="ignore").strip()

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise RuntimeError("PDF support requires 'pypdf'.") from exc
        reader = PdfReader(BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()

    if suffix == ".docx":
        try:
            from docx import Document
            doc = Document(BytesIO(raw))
            lines = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
            return "\n".join(lines).strip()
        except Exception:
            # Fallback parser: extract visible text from word/document.xml.
            try:
                with zipfile.ZipFile(BytesIO(raw)) as zf:
                    xml_bytes = zf.read("word/document.xml")
                root = ET.fromstring(xml_bytes)
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                paragraphs = []
                for para in root.findall(".//w:p", ns):
                    runs = para.findall(".//w:t", ns)
                    text = "".join(t.text for t in runs if t.text)
                    if text.strip():
                        paragraphs.append(text.strip())
                return "\n".join(paragraphs).strip()
            except Exception as exc:
                raise RuntimeError("Could not read DOCX file. Please upload TXT or PDF.") from exc

    raise ValueError("Unsupported file type. Use .txt, .md, .pdf, or .docx")

# Logout button in sidebar
with st.sidebar:
    st.write(f"👤 Logged in as: **{st.session_state.get('username', 'user')}**")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.auth_attempts = 0
        st.session_state.auth_locked_until = 0
        st.session_state.messages = []
        st.success("Logged out successfully!")
        st.rerun()

    username = st.session_state.get("username", "admin")
    user_profile = get_profile(username)

    with st.expander("My Memory Profile", expanded=False):
        current_role = st.text_input(
            "Current role",
            value=user_profile.get("current_role", ""),
            key="profile_current_role",
        )
        target_roles = st.text_input(
            "Target roles",
            value=user_profile.get("target_roles", ""),
            key="profile_target_roles",
        )
        preferred_locations = st.text_input(
            "Preferred locations",
            value=user_profile.get("preferred_locations", ""),
            key="profile_locations",
        )
        core_skills = st.text_area(
            "Core skills",
            value=user_profile.get("core_skills", ""),
            height=90,
            key="profile_skills",
        )
        work_style = st.text_input(
            "Work style",
            value=user_profile.get("work_style", ""),
            key="profile_work_style",
        )
        goals = st.text_area(
            "Career goals",
            value=user_profile.get("goals", ""),
            height=90,
            key="profile_goals",
        )

        if st.button("Save Profile Memory", use_container_width=True):
            upsert_profile(
                username=username,
                current_role=current_role,
                target_roles=target_roles,
                preferred_locations=preferred_locations,
                core_skills=core_skills,
                work_style=work_style,
                goals=goals,
            )
            st.success("Profile memory saved.")

        note = st.text_area("Quick note for Mr Agent", height=80, key="profile_note")
        if st.button("Add Note", use_container_width=True):
            add_note(username, note)
            st.success("Note saved to memory.")

        recent_notes = list_notes(username, limit=5)
        if recent_notes:
            st.caption("Recent notes")
            for n in recent_notes:
                st.markdown(f"- {n['note']}")

st.title("🤖 Mr. Agent")
st.markdown("Your autonomous GitHub assistant. Ask me anything about your repos — I can review code, create PRs, audit projects, and more.")

with st.expander("Resume Upload for Dice Job Matching", expanded=False):
    st.caption("Upload your resume and get targeted Dice profile edits for your role.")
    target_role = st.text_input(
        "Target role",
        value="Red Hat Linux DevOps AI Automation Engineer",
        key="resume_target_role",
    )
    uploaded_resume = st.file_uploader(
        "Upload resume",
        type=["txt", "md", "pdf", "docx"],
        key="resume_uploader",
    )

    if uploaded_resume is not None:
        try:
            resume_text = extract_resume_text(uploaded_resume)
            if resume_text:
                st.session_state.resume_text = resume_text
                preview = resume_text[:1200] + ("..." if len(resume_text) > 1200 else "")
                st.text_area("Extracted resume preview", value=preview, height=180, disabled=True)
            else:
                st.warning("Resume text appears empty after extraction.")
        except Exception as exc:
            st.error(f"Could not parse resume: {exc}")

    if st.button("Analyze Resume for Dice", use_container_width=True):
        resume_text = st.session_state.get("resume_text", "").strip()
        if not resume_text:
            st.error("Please upload a valid resume first.")
        else:
            with st.spinner("Analyzing resume against Dice demand..."):
                jobs = []
                queue = dice_client.get_apply_queue("pending_manual_apply")
                for item in queue[:20]:
                    job = item.get("job", {})
                    jobs.append(
                        {
                            "title": job.get("title", ""),
                            "company": job.get("company", ""),
                            "location": job.get("location", ""),
                            "url": job.get("url", ""),
                        }
                    )

                if not jobs:
                    try:
                        jobs = dice_client.fetch_jobs(
                            query=target_role,
                            location="Remote",
                            remote_only=True,
                            max_results=20,
                        )
                    except Exception:
                        jobs = []

                suggestions = ai_assistant.suggest_profile_modifications(
                    platform="Dice",
                    target_role=target_role,
                    current_profile_text=resume_text,
                    jobs=jobs,
                )
                st.session_state.resume_suggestions = suggestions

    if st.session_state.get("resume_suggestions"):
        st.markdown("### Dice Optimization Suggestions")
        st.markdown(st.session_state["resume_suggestions"])

st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Talk to Mr. Agent..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("🤖 Mr. Agent is working..."):
            try:
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1]
                    if m["role"] in ("user", "assistant")
                ]
                username = st.session_state.get("username", "admin")
                context = _build_user_memory_context(username)
                response = run_agent(prompt, history, user_context=context)
                record_interaction(username, prompt, response)
            except Exception as e:
                response = f"Error: {e}"
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
