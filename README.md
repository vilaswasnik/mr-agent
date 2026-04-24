# 🤖 Mr. Agent

**Mr. Agent** is a GitHub Action that automatically analyses a GitHub profile every week and opens an issue in your repository containing:

- **Profile Suggestions** – rule-based recommendations for improving your public GitHub presence (bio, repos, website link, topics, etc.)
- **Project Ideation** – creative project ideas tailored to your detected tech stack, optionally powered by OpenAI GPT.

---

## Example Report

> **Weekly Mr. Agent Report – 2026-04-24**
>
> ### 🔍 Profile Suggestions
> - Add a professional bio describing your expertise…
> - Increase the number of public repositories…
> - Consider adding a link to a personal website…
>
> ### 💡 Project Ideation
> 1. Develop a decentralized finance (DeFi) platform…
> 2. Build a machine learning-powered recommendation system…

---

## Setup

### 1. Fork / use this repository

Click **Use this template** or fork the repository into your own account.

### 2. (Optional) Add an OpenAI API key

For AI-generated project ideas, add your OpenAI API key as a repository secret:

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `OPENAI_API_KEY`, Value: your key

If the secret is not set, Mr. Agent falls back to built-in template ideas.

### 3. Enable Issues

Make sure **Issues** are enabled for your repository (**Settings → Features → Issues**).

### 4. The workflow runs automatically

The included workflow (`.github/workflows/weekly-report.yml`) runs **every Friday at 09:00 UTC**.  
You can also trigger it manually via **Actions → Weekly Mr. Agent Report → Run workflow**.

---

## Configuration

| Environment variable | Description | Default |
|---|---|---|
| `MR_AGENT_USERNAME` | GitHub username to analyse | Repository owner |
| `OPENAI_API_KEY` | OpenAI key for AI-powered ideas | *(fallback ideas used if absent)* |

---

## Local development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the script (requires GITHUB_TOKEN and GITHUB_REPOSITORY)
export GITHUB_TOKEN="ghp_..."
export GITHUB_REPOSITORY="your-org/your-repo"
export MR_AGENT_USERNAME="target-username"   # optional
python src/mr_agent.py
```

---

## How it works

1. **Fetch profile** – calls the GitHub REST API to retrieve the user's public profile and repositories.
2. **Analyse** – checks for missing bio, low repo count, missing website, undescribed repos, etc.
3. **Ideate** – either calls OpenAI GPT-4o-mini or uses built-in templates to generate two project ideas.
4. **Report** – formats everything into Markdown and opens a GitHub Issue titled *"Weekly Mr. Agent Report – YYYY-MM-DD"*.

---

*Generated automatically by [Mr. Agent](https://github.com/vilaswasnik/mr-agent).*
