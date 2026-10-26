# 🤖 Mr. Agent

**An autonomous Python agent that looks after your GitHub ecosystem and your job search.** Mr. Agent scans your repositories, audits them for missing READMEs and descriptions, reviews and fixes code via pull requests, generates job-profile optimisation packs, and watches Dice for new matching jobs — from the command line, from a login-protected Streamlit web app, or on a schedule via GitHub Actions.

Powered by Python and the OpenAI API. This is the cloud/CLI original; its local-first desktop successor is [MrVilsyAgent](https://github.com/vilaswasnik/MrVilsyAgent).

## What it does

**GitHub ecosystem management (CLI, `main.py`)**

- **`--auto`** — full autonomous sweep: scan all repos, inject missing descriptions, author missing READMEs, and post a summary report issue.
- **`--fix REPO FILE`** — scan a file for security issues, performance bottlenecks, and bad practices; rewrite it, branch, commit, and open a PR.
- **`--review REPO FILE`** — a markdown hit-list of the flaws in a file, without changing anything.
- **`--audit`** — find repos missing README files and draft custom ones.
- **`--triage` / `--stale-prs`** — work through open issues and nudge stale PRs.

**Career tools (CLI)**

- **`--profile`** — a recruiter-style analysis of your GitHub profile with concrete visibility improvements.
- **`--manage-profile`** — a platform-ready profile pack (Dice by default): headline options, summary, skills, experience bullets, role variants, and a 14-day improvement plan.
- **`--dice-watch`** — poll Dice for new listings matching your query and queue them for rapid manual apply. **Auto-submit is deliberately not enabled** — portals require interactive authentication and anti-bot checks, so Mr. Agent queues and you click.

**Web app (`app.py`, Streamlit)**

- Login-protected chat UI (PBKDF2-hashed credentials from environment variables, with login lockout) that runs the same agent tools conversationally.
- Per-user persistent memory — profile and interaction patterns are remembered between sessions.
- Resume upload with a built-in DOCX/PDF parser, matched against current Dice listings.
- `dashboard.py` is a companion monitoring dashboard: agent activity, deployment status, dependency graph, and Slack/Discord notifications.

**Automation**

- GitHub Actions cron (`mr_agent_cron.yml`) runs scheduled modes and posts weekly report issues.
- An issue bot (`mr_agent_issue_bot.yml`) responds to issues opened with chat/command titles, so the agent can be driven from a phone.

## Installation & setup

Prerequisites: Python 3.12 (see `runtime.txt`), a GitHub token, and an OpenAI API key.

```bash
git clone https://github.com/vilaswasnik/mr-agent.git
cd mr-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your GITHUB_TOKEN and OPENAI_API_KEY
```

> **⚠️ Security note:** `.env` is gitignored — never commit your tokens. For the web app, also set `APP_ADMIN_USERNAME` and `APP_ADMIN_PASSWORD` (or a precomputed `APP_ADMIN_PASSWORD_HASH`) in the environment.

## Usage

```bash
python main.py --auto                       # full autonomous sweep
python main.py --fix mr-agent main.py       # fix a file and open a PR
python main.py --review mr-agent main.py    # review only
python main.py --profile                    # profile analysis
python main.py --manage-profile --platform Dice --target-role "Senior Python Engineer"
python main.py --dice-watch --dice-query "Senior Python Engineer" --dice-location "Remote" --dice-remote --dice-cycles 6 --dice-interval 300
python main.py --dice-show-queue            # what's queued to apply to

streamlit run app.py                        # web app (login required)
streamlit run dashboard.py                  # monitoring dashboard
```

## Deployment

`render.yaml` and `Procfile` describe the Render deployment: the web service runs the Dice watcher in the background alongside the Streamlit app on `$PORT`. Set `GITHUB_TOKEN` and `OPENAI_API_KEY` as environment variables in Render (marked `sync: false` in `render.yaml` — they are never stored in the repo).

## Project layout

```text
main.py          CLI entry point (all modes above)
app.py           Streamlit web app (chat agent, memory, resume matching)
dashboard.py     Streamlit monitoring dashboard
src/
  github_client.py   PyGithub wrapper (scan, edit, PR)
  ai_client.py       OpenAI assistant layer
  agents.py          Orchestrator and tool agents
  dice_client.py     Dice search and apply queue
  memory.py, user_memory_db.py   Persistent user memory
  deployment.py, integrations.py, dependencies.py, feedback.py, issue_handler.py
```

## Current limitations (stated up front)

- The autonomous modes write to your GitHub account (descriptions, READMEs, PRs) using your token — review its PRs like any contributor's.
- Dice integration queues jobs for *manual* apply by design; it does not submit applications.
- The web app is single-instance oriented (in-process memory plus a local SQLite store).

## Contributing

See `CONTRIBUTING.md`. Bug reports and PRs are welcome — the issue tracker is also used by the agent's own scheduled reports, so actionable titles help everyone.

## License

MIT — see `LICENSE`.
