# Contributing to Mr. Agent

Thanks for looking. Mr. Agent is a Python automation agent with three surfaces sharing one core in `src/`: a CLI (`main.py`), a Streamlit web app (`app.py`) plus monitoring dashboard (`dashboard.py`), and GitHub Actions automation. Contributions of code, docs, and bug reports are all welcome.

## Run it locally

Prerequisites: Python 3.12, a GitHub token, and an OpenAI API key.

```bash
git clone https://github.com/vilaswasnik/mr-agent.git
cd mr-agent
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add GITHUB_TOKEN and OPENAI_API_KEY
python main.py --help
streamlit run app.py   # web app; set APP_ADMIN_USERNAME / APP_ADMIN_PASSWORD first
```

Ground rules:

- **Tokens live in `.env` or the deployment environment — never in code or commits.** The web app's admin credentials likewise come from `APP_ADMIN_*` environment variables; the PBKDF2 hashing and lockout in `app.py` are not to be weakened.
- **The agent writes to GitHub.** Any change to `--auto`, `--fix`, or the GitHub client must keep changes reviewable: fixes go through branches and pull requests, never direct pushes to `main`.
- **Dice stays queue-only.** Do not add auto-submit of job applications — portals require interactive authentication, and the queue-for-manual-apply design is deliberate (see the README).
- Keep `__pycache__` and local state (queues, memory DBs) out of commits.

## Filing an issue

Use GitHub Issues. Note: this tracker also receives the agent's own scheduled report issues — that's expected. For a bug, include: the surface (CLI mode / web app / workflow), the exact command or action, what you expected, what happened, and any traceback. Redact tokens from logs before pasting.

## PR process

1. Fork, branch from `main`, keep the change focused.
2. Exercise the mode or page you touched against a test repo/account where possible, and say what you ran in the PR description.
3. If you add a CLI flag or an agent tool, document it in the README in the same PR.
4. One approval from the maintainer merges.

## Good first issues

Concrete, evidence-based starting points (each cites where the gap is):

1. **Stop committing bytecode.** `src/__pycache__/` is in the repo tree — add it to `.gitignore` (with the other Python artefacts) and remove the tracked files.
2. **Document the Copilot agent definition.** `.github/agents/mr-agent-autonomy.agent.md` exists but nothing explains what it does or how to use it — a short section in this file or the README fixes that.
3. **Add a smoke test for the CLI.** There is no test suite: a minimal check that `python main.py --help` parses and that each documented flag exists in argparse would have caught documentation drift more than once.
4. **Separate the ops log from the issue tracker.** The agent's weekly reports and personal reminder issues (some about *other* projects) share this tracker. Move report output to Discussions or a dedicated label, and document the convention here.
