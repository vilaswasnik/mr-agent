# 🤖 Mr. Agent

**Mr. Agent** is a fully autonomous, predictive ecosystem manager designed to maintain, optimize, and organize your GitHub Repositories. Powered by Python and the OpenAI API, Mr. Agent scans your profile, audits repositories, generates documentation, and directly fixes your code via automated pull requests.

## 🌟 Key Features

* **`--auto` (Full Autonomous Mode):** Mr. Agent takes the wheel. Scans your entire GitHub ecosystem, auto-injects missing repository descriptions, authors and PRs missing `README`s, and finishes by writing a comprehensive summary report as a GitHub Issue.
* **`--fix REPO FILE` (Auto-Repair):** Scans a target file for security vulnerabilities, performance bottlenecks, and bad practices, then completely rewrites the code. It then branches off, commits the fix, and opens a Pull Request for you.
* **`--review REPO FILE`:** Acts as a ruthless CI/CD mentor, dumping a markdown hit-list of code flaws found within a given file.
* **`--audit`:** Checks all public repositories for missing `README.md` files and automatically crafts custom ones based on context.
* **`--profile`:** Acts as a Senior Tech Recruiter and gives brutal, actionable optimizations to maximize the visibility of your GitHub profile.
* **`--manage-profile`:** Generates a platform-ready profile optimization pack (Dice by default) with headline options, summary, skills, experience bullets, role variants, and a 14-day improvement plan.
* **`--dice-watch`:** Polls Dice for latest jobs, detects new listings, and auto-queues them for rapid manual apply.
* **`--dice-suggest-mods`:** Uses latest Dice jobs to suggest exact profile modifications and ATS keyword updates.
* **`--report`:** Triggers a weekly GitHub workflow (via GitHub Actions) that posts your current progress, suggestions, and next-generation project ideas in an issue.

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/vilaswasnik/mr-agent.git
   cd mr-agent
   ```

2. **Set up the Virtual Environment & Dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Rename `.env.example` to `.env` and insert your tokens:
   ```env
   GITHUB_TOKEN=your_github_personal_access_token_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   > **⚠️ Security Note:** Ensure your `.env` file is in `.gitignore`. NEVER commit your API keys.

## 💻 Usage Commands

*   To trigger the autonomous loop:
    `python main.py --auto`
*   To ask Mr. Agent to optimize code inside one of your repositories (e.g., `mr-agent`'s `main.py` file):
    `python main.py --fix mr-agent main.py`
*   To just get profile advice:
    `python main.py --profile`
*   To generate a Dice-ready profile packet:
    `python main.py --manage-profile --platform Dice --target-role "Senior Python Engineer"`
*   To monitor latest Dice jobs and build an apply queue:
    `python main.py --dice-watch --dice-query "Senior Python Engineer" --dice-location "Remote" --dice-remote --dice-cycles 6 --dice-interval 300`
*   To view queued jobs for fast application:
    `python main.py --dice-show-queue`
*   To generate profile modifications from latest job demand:
    `python main.py --dice-suggest-mods --target-role "Senior Python Engineer" --dice-query "Senior Python Engineer" --dice-location "Remote" --dice-remote`

> **Note:** Dice auto-submit is not enabled in this project. Mr. Agent queues jobs quickly for manual apply because job portals often require interactive authentication and anti-bot checks.

## 🤖 GitHub Actions Automated Cron Job

Mr. Agent runs by default every Monday at 09:00 UTC using GitHub Actions (configured in `.github/workflows/mr_agent_cron.yml`). To enable it, navigate to your repository's **Settings > Secrets and variables > Actions** and add `OPENAI_API_KEY` as a repository secret.

---
*Maintained autonomously by [Mr. Agent](https://github.com/vilaswasnik/mr-agent)*
