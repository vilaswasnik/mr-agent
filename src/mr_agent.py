"""
Mr. Agent - Weekly GitHub Profile Analysis Tool

Fetches a GitHub user's profile, generates profile improvement suggestions,
and creates project ideation ideas using the OpenAI API.
Finally, it opens a GitHub Issue with the full report.
"""

import os
import sys
import json
import datetime
import requests


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"


def _gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def fetch_profile(username: str, token: str) -> dict:
    """Fetch a GitHub user profile."""
    resp = requests.get(f"{GITHUB_API}/users/{username}", headers=_gh_headers(token), timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_repos(username: str, token: str, max_repos: int = 30) -> list:
    """Fetch public repositories for a GitHub user."""
    repos = []
    page = 1
    while len(repos) < max_repos:
        resp = requests.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=_gh_headers(token),
            params={"per_page": 30, "page": page, "type": "public", "sort": "updated"},
            timeout=15,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
        if len(batch) < 30:
            break
    return repos[:max_repos]


def create_github_issue(repo: str, token: str, title: str, body: str) -> str:
    """Create a GitHub issue and return its HTML URL."""
    owner, repo_name = repo.split("/", 1)
    resp = requests.post(
        f"{GITHUB_API}/repos/{owner}/{repo_name}/issues",
        headers=_gh_headers(token),
        json={"title": title, "body": body},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]


# ---------------------------------------------------------------------------
# Profile suggestions (rule-based)
# ---------------------------------------------------------------------------

def generate_profile_suggestions(profile: dict, repos: list) -> list[str]:
    """Return a list of profile improvement suggestions."""
    suggestions = []

    if not profile.get("bio"):
        suggestions.append(
            "Add a professional bio describing your expertise, skills, and areas of interest "
            "in the tech industry to give recruiters and potential collaborators a better "
            "understanding of who you are."
        )

    public_repos = profile.get("public_repos", 0)
    if public_repos < 10:
        suggestions.append(
            "Increase the number of public repositories by contributing to more open-source "
            "projects or creating your own projects to showcase your technical skills and knowledge."
        )

    if not profile.get("blog"):
        suggestions.append(
            "Consider adding a link to a personal website, portfolio, or blog that provides more "
            "information about your work experience, projects, and achievements to give viewers "
            "a more comprehensive view of your capabilities."
        )

    if not profile.get("twitter_username"):
        suggestions.append(
            "Link your Twitter/X account to your GitHub profile to extend your professional "
            "network and increase your visibility in the developer community."
        )

    if not profile.get("company"):
        suggestions.append(
            "Add your current company or affiliation to your GitHub profile to help collaborators "
            "and recruiters understand your professional background."
        )

    if not profile.get("location"):
        suggestions.append(
            "Adding your location to your profile can help local companies and communities "
            "discover you more easily."
        )

    # Repo-level suggestions
    repos_with_desc = [r for r in repos if r.get("description")]
    if repos and len(repos_with_desc) / len(repos) < 0.5:
        suggestions.append(
            "Many of your repositories lack descriptions. Adding clear, concise descriptions "
            "helps others discover and understand your projects."
        )

    repos_with_topics = [r for r in repos if r.get("topics")]
    if repos and len(repos_with_topics) / len(repos) < 0.4:
        suggestions.append(
            "Add relevant topics/tags to your repositories to improve discoverability and "
            "attract the right audience to your work."
        )

    # Keep the list sensible — top 3 are most actionable
    return suggestions[:3] if len(suggestions) > 3 else suggestions


# ---------------------------------------------------------------------------
# Project ideation (OpenAI-powered with fallback)
# ---------------------------------------------------------------------------

def _collect_tech_stack(repos: list) -> list[str]:
    """Derive dominant languages from repos."""
    langs: dict[str, int] = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    return sorted(langs, key=langs.get, reverse=True)[:5]  # type: ignore[arg-type]


def generate_project_ideas_openai(profile: dict, repos: list, api_key: str) -> list[str]:
    """Use OpenAI chat completions to generate two project ideas."""
    tech_stack = _collect_tech_stack(repos)
    bio = profile.get("bio") or "a software developer"
    username = profile.get("login", "developer")
    stack_str = ", ".join(tech_stack) if tech_stack else "various technologies"

    prompt = (
        f"You are a creative tech mentor. Given the GitHub profile of '{username}' "
        f"with bio '{bio}' and a tech stack of {stack_str}, suggest exactly 2 ambitious, "
        "innovative software project ideas. For each idea write 2-3 sentences describing "
        "the project concept and what skills it will demonstrate. "
        "Format each idea as a plain paragraph (no numbering, no bullet points). "
        "Separate the two ideas with a single blank line."
    )

    import urllib.request  # stdlib – avoids adding the openai package as hard dependency

    payload = json.dumps(
        {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": 400,
        }
    ).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    content = data["choices"][0]["message"]["content"].strip()
    # Split by blank line to get two ideas
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    return paragraphs[:2] if len(paragraphs) >= 2 else [content, ""]


def generate_project_ideas_fallback(profile: dict, repos: list) -> list[str]:
    """Fallback: return template project ideas based on detected tech stack."""
    tech_stack = _collect_tech_stack(repos)
    primary = tech_stack[0] if tech_stack else "Python"

    ideas = [
        (
            f"Build a {primary}-based CLI tool that automates repetitive developer workflows "
            "such as scaffolding projects, managing dotfiles, or batch-processing files. "
            "This project will sharpen your understanding of system-level programming, "
            "package distribution, and developer experience design."
        ),
        (
            "Develop a personal analytics dashboard that aggregates your GitHub activity, "
            "open-source contributions, and coding streaks into a single web interface. "
            "This will demonstrate your skills in data visualisation, REST API integration, "
            "and full-stack development while producing a portfolio piece recruiters will notice."
        ),
    ]
    return ideas


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_report(date_str: str, suggestions: list[str], ideas: list[str], repo_full_name: str) -> str:
    """Render the Markdown report body."""
    lines = [
        f"## 🤖 Mr. Agent Weekly Profile Analysis ({date_str})",
        "",
        "### 🔍 Profile Suggestions",
    ]

    for suggestion in suggestions:
        lines.append(f"- {suggestion}")

    lines += [
        "",
        "### 💡 Project Ideation",
    ]

    for i, idea in enumerate(ideas, start=1):
        lines.append(f"{i}. {idea}")
        lines.append("")

    lines.append(
        f'*Generated automatically by <a href="https://github.com/{repo_full_name}">Mr. Agent</a>.*'
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    # ---- required env vars ----
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not github_token:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # The repository that owns this Action (e.g. "vilaswasnik/mr-agent")
    repo_full_name = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo_full_name:
        print("ERROR: GITHUB_REPOSITORY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # Profile to analyse — defaults to the repo owner
    username = os.environ.get("MR_AGENT_USERNAME") or repo_full_name.split("/")[0]

    # Optional OpenAI key for richer project ideas
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")

    date_str = datetime.date.today().isoformat()

    print(f"[mr-agent] Analysing profile: {username}")
    profile = fetch_profile(username, github_token)
    repos = fetch_repos(username, github_token)
    print(f"[mr-agent] Fetched {len(repos)} public repos.")

    suggestions = generate_profile_suggestions(profile, repos)
    print(f"[mr-agent] Generated {len(suggestions)} profile suggestion(s).")

    if openai_api_key:
        try:
            ideas = generate_project_ideas_openai(profile, repos, openai_api_key)
            print("[mr-agent] Generated project ideas via OpenAI.")
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            print(f"[mr-agent] OpenAI call failed ({exc}); using fallback ideas.", file=sys.stderr)
            ideas = generate_project_ideas_fallback(profile, repos)
    else:
        print("[mr-agent] OPENAI_API_KEY not set; using fallback project ideas.")
        ideas = generate_project_ideas_fallback(profile, repos)

    report_body = render_report(date_str, suggestions, ideas, repo_full_name)
    issue_title = f"Weekly Mr. Agent Report - {date_str}"

    print(f"[mr-agent] Creating issue: {issue_title}")
    issue_url = create_github_issue(repo_full_name, github_token, issue_title, report_body)
    print(f"[mr-agent] Issue created: {issue_url}")


if __name__ == "__main__":
    main()
