import streamlit as st
import os
import json
from dotenv import load_dotenv
from src.github_client import GitHubManager
from src.ai_client import AIAssistant

load_dotenv(override=True)

st.set_page_config(page_title="Mr. Agent", page_icon="🤖", layout="wide")

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
    st.error("API keys missing from .env")
    st.stop()

@st.cache_resource
def init_clients():
    return GitHubManager(github_token), AIAssistant(openai_key)

try:
    gh_manager, ai_assistant = init_clients()
except Exception as e:
    st.error(f"Failed to connect: {e}")
    st.stop()

TOOLS = [
    {"type":"function","function":{"name":"get_profile","description":"Get the user's GitHub profile info.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"list_repos","description":"List all GitHub repositories owned by the user.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"review_code","description":"Review a specific file in a repo and return feedback.","parameters":{"type":"object","properties":{"repo":{"type":"string"},"file_path":{"type":"string"}},"required":["repo","file_path"]}}},
    {"type":"function","function":{"name":"fix_file","description":"Fix issues in a file and create a Pull Request.","parameters":{"type":"object","properties":{"repo":{"type":"string"},"file_path":{"type":"string"}},"required":["repo","file_path"]}}},
    {"type":"function","function":{"name":"analyze_profile","description":"Analyze GitHub profile and suggest improvements and new project ideas.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"audit_repos","description":"Audit all repos for missing READMEs and descriptions, auto-fix them.","parameters":{"type":"object","properties":{},"required":[]}}}
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
    return "Unknown tool."

def run_agent(user_message, history):
    messages = [
        {"role": "system", "content": (
            "You are Mr. Agent, an elite autonomous GitHub assistant with direct access to the user's GitHub account. "
            "Use your tools to fetch real data, review code, create PRs, and audit repositories. "
            "Always take action when asked — don't just advise. Be concise, sharp, and technical. Use markdown."
        )}
    ] + history + [{"role": "user", "content": user_message}]

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

st.title("🤖 Mr. Agent")
st.markdown("Your autonomous GitHub assistant. Ask me anything about your repos — I can review code, create PRs, audit projects, and more.")
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
                response = run_agent(prompt, history)
            except Exception as e:
                response = f"Error: {e}"
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
