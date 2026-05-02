import os
import shutil
import argparse
import time
from dotenv import load_dotenv
from src.github_client import GitHubManager
from src.ai_client import AIAssistant
from src.agents import Orchestrator
from src import memory as mem
from datetime import datetime


def type_print(text, delay=0.01):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()


def run_autonomous_mode(gh_manager, ai_assistant, dry_run=False, max_prs=5, max_comments=20):
    orchestrator = Orchestrator(gh_manager, ai_assistant, dry_run=dry_run, max_prs=max_prs, max_comments=max_comments)

    type_print("\n[🤖 SYSTEM] OVERRIDE ACCEPTED: INITIATING AUTONOMOUS ECOSYSTEM SCAN...")
    profile_data = gh_manager.get_user_profile()
    type_print(f"\n[🤖 SYSTEM] Analyzing profile matrix for subject '{profile_data['login']}'...")
    tips = ai_assistant.analyze_profile(profile_data)
    ideas = ai_assistant.suggest_new_projects(profile_data)

    type_print("\n[🤖 SYSTEM] Querying repository payload...")
    repos = gh_manager.get_repositories()
    actions_taken = []
    auto_prs = 0

    for repo in repos:
        if auto_prs >= max_prs:
            actions_taken.append("Safety cap reached: max PRs per run reached during README/description audit.")
            break
        if not repo["has_readme"]:
            type_print(f"   [🚀 AGENT] Missing README in '{repo['name']}'. Generating...")
            readme_content = ai_assistant.generate_readme(repo["name"], repo["description"])
            if dry_run:
                actions_taken.append(f"[DRY-RUN] Would create README PR for `{repo['name']}`")
                continue
            pr_url = gh_manager.create_readme_pr(repo["obj"], readme_content)
            if pr_url:
                auto_prs += 1
                type_print(f"      -> SUCCESS: PR at {pr_url}")
                mem.record_action(repo["name"], "add_readme", "README.md")
                actions_taken.append(f"README PR for `{repo['name']}`: {pr_url}")

        if repo["description"] == "No description" or not repo["description"]:
            type_print(f"   [🚀 AGENT] Missing description in '{repo['name']}'. Generating...")
            new_desc = ai_assistant.generate_repo_description(repo["name"], repo["language"])
            if dry_run:
                actions_taken.append(f"[DRY-RUN] Would update description for `{repo['name']}` to: {new_desc}")
                continue
            success = gh_manager.update_repo_description(repo["obj"], new_desc)
            if success:
                type_print(f"      -> SUCCESS: Description injected: {new_desc}")
                mem.record_action(repo["name"], "update_description", new_desc)
                actions_taken.append(f"Description for `{repo['name']}`: *\"{new_desc}\"*")

    # NEW: Run all advanced pipelines
    type_print("\n[🤖 SYSTEM] Running issue triage sweep...")
    triage_results = orchestrator.run_triage()
    actions_taken.extend(triage_results)

    type_print("\n[🤖 SYSTEM] Scanning for stale PRs...")
    stale_results = orchestrator.run_stale_pr_cleanup(stale_days=30)
    actions_taken.extend(stale_results)

    type_print("\n[🤖 SYSTEM] Reviewing open PRs...")
    review_results = orchestrator.run_pr_reviews()
    actions_taken.extend(review_results)

    type_print("\n[🤖 SYSTEM] Auditing dependencies...")
    dep_results = orchestrator.run_dependency_check()
    actions_taken.extend(dep_results)

    type_print("\n[🤖 SYSTEM] Running issue → fix pipeline...")
    fix_results = orchestrator.run_issue_fix_pipeline()
    actions_taken.extend(fix_results)

    type_print("\n[🤖 SYSTEM] Generating tests for uncovered files...")
    test_results = orchestrator.run_test_generation()
    actions_taken.extend(test_results)

    # Self-reflection
    type_print("\n[🤖 SYSTEM] Running self-reflection protocol...")
    reflection, _ = orchestrator.run_self_reflection(ai_assistant)

    # Final report
    type_print("\n[🤖 SYSTEM] Compiling autonomous operations report...")
    report_body = f"## 🤖 AUTONOMOUS RUN REPORT ({datetime.now().strftime('%Y-%m-%d')})\n\n"
    report_body += "### ⚡ Profile Optimizations\n" + tips + "\n\n"
    report_body += "### 🌐 New Project Ideas\n" + ideas + "\n\n"
    report_body += "### 🛠️ Actions Executed\n"
    if actions_taken:
        for action in actions_taken:
            report_body += f"1. {action}\n"
    else:
        report_body += "- Ecosystem structurally sound. No automated payloads deployed.\n"
    report_body += f"\n### 🧠 Self-Assessment\n{reflection}"

    if dry_run:
        issue_url = "[DRY-RUN] Would create autonomous run report issue in mr-agent"
    else:
        issue_url = gh_manager.create_weekly_report_issue(
            "mr-agent",
            f"🤖 Autonomous Run Report - {datetime.now().strftime('%Y-%m-%d')}",
            report_body
        )
    if issue_url:
        type_print(f"\n[🤖 SYSTEM] Report cataloged: {issue_url}")
    else:
        type_print("\n[❌ SYSTEM] Report generation failed.")


def main():
    parser = argparse.ArgumentParser(description="Mr. Agent - Your Autonomous GitHub Assistant")
    parser.add_argument('--profile', action='store_true', help="Analyze GitHub profile")
    parser.add_argument('--audit', action='store_true', help="Audit repos for missing files")
    parser.add_argument('--review', type=str, nargs=2, metavar=('REPO', 'FILE_PATH'), help="Review a file")
    parser.add_argument('--fix', type=str, nargs=2, metavar=('REPO', 'FILE_PATH'), help="Fix a file and create PR")
    parser.add_argument('--triage', action='store_true', help="Triage open issues across all repos")
    parser.add_argument('--stale-prs', action='store_true', help="Comment on stale PRs")
    parser.add_argument('--review-prs', action='store_true', help="AI-review open PRs across all repos")
    parser.add_argument('--gen-tests', action='store_true', help="Generate unit tests for uncovered files")
    parser.add_argument('--dep-check', action='store_true', help="Audit and update dependencies")
    parser.add_argument('--fix-issues', action='store_true', help="Auto-fix bug issues via PR")
    parser.add_argument('--reflect', action='store_true', help="Run self-reflection on last run log")
    parser.add_argument('--task', type=str, help="Run a natural-language task goal")
    parser.add_argument('--mid', action='store_true', help="Run Mid mode: triage + stale PR cleanup + PR review + dependency checks")
    parser.add_argument('--advanced', action='store_true', help="Run Advanced mode: Mid mode + issue fixes + test generation + self-reflection")
    parser.add_argument('--dry-run', action='store_true', help="Preview actions without writing to GitHub")
    parser.add_argument('--max-prs', type=int, default=5, help="Maximum PRs created in one run")
    parser.add_argument('--max-comments', type=int, default=20, help="Maximum comments posted in one run")
    parser.add_argument('--report', action='store_true', help="Generate report as a GitHub Issue")
    parser.add_argument('--auto', action='store_true', help="Full autonomous mode (all pipelines)")
    parser.add_argument('--chat', action='store_true', help="Interactive advisor session")
    args = parser.parse_args()

    if not os.path.exists(".env"):
        shutil.copy(".env.example", ".env")
        print("Created .env file. Please fill in your API keys and run again.")
        return

    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not github_token or not openai_key or github_token == "your_github_personal_access_token_here":
        print("[ERROR] Credentials not recognized. Aborting.")
        return

    gh_manager = GitHubManager(github_token)
    ai_assistant = AIAssistant(openai_key)
    orchestrator = Orchestrator(
        gh_manager,
        ai_assistant,
        dry_run=args.dry_run,
        max_prs=max(0, args.max_prs),
        max_comments=max(0, args.max_comments),
    )

    if args.auto:
        run_autonomous_mode(
            gh_manager,
            ai_assistant,
            dry_run=args.dry_run,
            max_prs=max(0, args.max_prs),
            max_comments=max(0, args.max_comments),
        )

    elif args.mid:
        print("\n[🤖 SYSTEM] Running MID mode...")
        actions = orchestrator.run_mid_mode()
        if actions:
            for action in actions:
                print(f"   -> {action}")
        else:
            print("   -> No actions required.")

    elif args.advanced:
        print("\n[🤖 SYSTEM] Running ADVANCED mode...")
        result = orchestrator.run_advanced_mode(include_reflection=True)
        actions = result.get("actions", [])
        if actions:
            for action in actions:
                print(f"   -> {action}")
        else:
            print("   -> No actions required.")
        if result.get("reflection_issue"):
            print(f"\nSelf-reflection issue: {result['reflection_issue']}")

    elif args.triage:
        print("\n[🤖 SYSTEM] Triaging open issues...")
        results = orchestrator.run_triage()
        for r in results:
            print(f"   -> {r}")

    elif args.stale_prs:
        print("\n[🤖 SYSTEM] Scanning for stale PRs...")
        results = orchestrator.run_stale_pr_cleanup()
        for r in results:
            print(f"   -> {r}")

    elif args.review_prs:
        print("\n[🤖 SYSTEM] Reviewing open PRs...")
        results = orchestrator.run_pr_reviews()
        for r in results:
            print(f"   -> {r}")

    elif args.gen_tests:
        print("\n[🤖 SYSTEM] Generating tests for uncovered files...")
        results = orchestrator.run_test_generation()
        for r in results:
            print(f"   -> {r}")

    elif args.dep_check:
        print("\n[🤖 SYSTEM] Auditing dependencies...")
        results = orchestrator.run_dependency_check()
        for r in results:
            print(f"   -> {r}")

    elif args.fix_issues:
        print("\n[🤖 SYSTEM] Running issue → fix pipeline...")
        results = orchestrator.run_issue_fix_pipeline()
        for r in results:
            print(f"   -> {r}")

    elif args.reflect:
        print("\n[🤖 SYSTEM] Running self-reflection...")
        reflection, issue_url = orchestrator.run_self_reflection(ai_assistant)
        print(reflection)
        if issue_url:
            print(f"\nReport issue: {issue_url}")

    elif args.task:
        print(f"\n[🤖 SYSTEM] Planning task: {args.task}")
        plan, results = orchestrator.run_natural_language_task(args.task, ai_assistant)
        print("\n[🤖 PLAN]")
        for step in plan:
            print(f"  Step {step.get('step')}: {step.get('tool')} — {step.get('reason')}")
        print("\n[🤖 RESULTS]")
        for r in results:
            print(f"  {r}")

    elif args.fix:
        repo_target, file_path = args.fix
        print(f"\n[🤖 SYSTEM] Fixing {file_path} in {repo_target}...")
        code = gh_manager.get_file_content(repo_target, file_path)
        if code:
            fixed_code = ai_assistant.fix_code(code, file_path)
            repo_obj = gh_manager.github.get_repo(f"{gh_manager.user.login}/{repo_target}")
            pr_url = gh_manager.create_fix_pr(repo_obj, file_path, fixed_code)
            print(f"   -> PR: {pr_url}" if pr_url else "   -> PR creation failed.")

    elif args.review:
        repo_target, file_path = args.review
        code = gh_manager.get_file_content(repo_target, file_path)
        if code:
            print(ai_assistant.review_code(code, file_path))

    elif args.chat:
        print("\n[🤖 SYSTEM] Mr. Agent Advisor Online. Type 'exit' to quit.")
        while True:
            try:
                user_input = input("\n👤 You: ")
                if user_input.strip().lower() in ['exit', 'quit']:
                    print("\n[🤖 SYSTEM] Shutting down advisor.")
                    break
                if not user_input.strip():
                    continue
                response = ai_assistant.chat_advisor(user_input)
                print(f"\n🤖 Mr. Agent: {response}")
            except KeyboardInterrupt:
                print("\n[🤖 SYSTEM] Aborted.")
                break

    elif args.profile or not any(vars(args).values()):
        print("\n[🤖 SYSTEM] Mr. Agent booting sequence initialized...")
        print("Run with --auto for full autonomous sweep, or --help to see all options.\n")


if __name__ == "__main__":
    main()
