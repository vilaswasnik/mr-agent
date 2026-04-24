import os
import shutil
import argparse
import time
from dotenv import load_dotenv
from src.github_client import GitHubManager
from src.ai_client import AIAssistant
from datetime import datetime

def type_print(text, delay=0.01):
    """Simulates a robotic typing effect for the console."""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def run_autonomous_mode(gh_manager, ai_assistant):
    type_print("\n[🤖 SYSTEM] OVERRIDE ACCEPTED: INITIATING AUTONOMOUS ECOSYSTEM SCAN...")
    profile_data = gh_manager.get_user_profile()
    
    type_print(f"\n[🤖 SYSTEM] Analyzing profile matrix for subject '{profile_data['login']}'...")
    tips = ai_assistant.analyze_profile(profile_data)
    ideas = ai_assistant.suggest_new_projects(profile_data)
    
    type_print("\n[🤖 SYSTEM] Querying repository payload...")
    repos = gh_manager.get_repositories()
    
    actions_taken = []
    
    for repo in repos:
        # Check README
        if not repo["has_readme"]:
            type_print(f"   [🚀 AGENT] Anomaly detected: Missing README.md in '{repo['name']}'. Executing generation protocols...")
            readme_content = ai_assistant.generate_readme(repo["name"], repo["description"])
            pr_url = gh_manager.create_readme_pr(repo["obj"], readme_content)
            if pr_url:
                type_print(f"      -> SUCCESS: PR orchestrated at {pr_url}")
                actions_taken.append(f"Executed automated README.md generation PR for `{repo['name']}`: {pr_url}")
                
        # Check Description
        if repo["description"] == "No description" or not repo["description"]:
            type_print(f"   [🚀 AGENT] Anomaly detected: Missing description in '{repo['name']}'. Computing contextual bypass...")
            new_desc = ai_assistant.generate_repo_description(repo["name"], repo["language"])
            success = gh_manager.update_repo_description(repo["obj"], new_desc)
            if success:
                type_print(f"      -> SUCCESS: Core description injected: {new_desc}")
                actions_taken.append(f"Injected synthetic description into `{repo['name']}`: *\"{new_desc}\"*")

    type_print("\n[🤖 SYSTEM] Terminating scan loop. Formatting autonomous operations report log...")
    report_body = f"## 🤖 SYSTEM OVERRIDE REPORT ({datetime.now().strftime('%Y-%m-%d')})\n\n"
    report_body += "### ⚡ Strategic Profile Optimizations\n" + tips + "\n\n"
    report_body += "### 🌐 Next-Gen Architectural Directives\n" + ideas + "\n\n"
    report_body += "### 🛠️ Autonomous Actions Executed\n"
    
    if actions_taken:
        for action in actions_taken:
            report_body += f"1. {action}\n"
    else:
        report_body += "- Ecosystem is structurally sound. No automated payloads deployed.\n"
        
    issue_url = gh_manager.create_weekly_report_issue("mr-agent", f"🤖 Autonomous Run Result - {datetime.now().strftime('%Y-%m-%d')}", report_body)
    
    if issue_url:
        type_print(f"\n[🤖 SYSTEM] Report cataloged and verified: {issue_url}")
    else:
        type_print(f"\n[❌ SYSTEM] WARNING: Report generation failed due to unforeseen error vectors.")

def main():
    parser = argparse.ArgumentParser(description="Mr. Agent - Your Automated GitHub Assistant")
    parser.add_argument('--profile', action='store_true', help="Analyze GitHub profile")
    parser.add_argument('--audit', action='store_true', help="Audit repositories for missing files and auto-fix via PRs")
    parser.add_argument('--review', type=str, nargs=2, metavar=('REPO', 'FILE_PATH'), help="Review specific code file in a repository")
    parser.add_argument('--fix', type=str, nargs=2, metavar=('REPO', 'FILE_PATH'), help="Automatically fix issues in a file and create a PR")
    parser.add_argument('--report', action='store_true', help="Generate weekly report as a GitHub Issue")
    parser.add_argument('--auto', action='store_true', help="Initiate FULL Autonomous Robotic Overload Mode")
    parser.add_argument('--chat', action='store_true', help="Start an interactive Advisor session with Mr. Agent")
    args = parser.parse_args()

    if not os.path.exists(".env"):
        shutil.copy(".env.example", ".env")
        print("Created .env file. Please fill in your API keys and run the script again.")
        return

    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not github_token or not openai_key or github_token == "your_github_personal_access_token_here":
        print("[ERROR] Credentials not recognized. Aborting.")
        return

    gh_manager = GitHubManager(github_token)
    ai_assistant = AIAssistant(openai_key)

    if args.auto:
        run_autonomous_mode(gh_manager, ai_assistant)

    elif args.report:
        print("\n--- 📝 Generating Weekly Report ---")
        
    elif args.audit:
        print("\n--- 🔍 Auditing Repositories ---")

    elif args.fix:
        repo_target, file_path = args.fix
        print(f"\n[🤖 SYSTEM] INITIATING AUTONOMOUS REPAIR ON {file_path} IN {repo_target}...")
        code = gh_manager.get_file_content(repo_target, file_path)
        if code:
            print(f"   [🚀 AGENT] Analyzing and computing optimal logic structure...")
            fixed_code = ai_assistant.fix_code(code, file_path)
            
            print(f"   [🚀 AGENT] Code refactoring complete. Preparing payload delivery...")
            try:
                repo_obj = gh_manager.github.get_repo(f"{gh_manager.user.login}/{repo_target}")
                pr_url = gh_manager.create_fix_pr(repo_obj, file_path, fixed_code)
                if pr_url:
                    print(f"      -> SUCCESS: Repair payload delivered at {pr_url}")
                else:
                    print(f"      -> ERROR: Could not deliver payload.")
            except Exception as e:
                print(f"      -> SYSTEM ERROR: {e}")

    elif args.review:
        repo_target, file_path = args.review
        code = gh_manager.get_file_content(repo_target, file_path)
        if code:
            print("\n📝 Executing review protocols...")
            print(ai_assistant.review_code(code, file_path))


    elif args.chat:
        print("\n[🤖 SYSTEM] Mr. Agent Advisor Protocol Online. Type 'exit' or 'quit' to terminate session.")
        while True:
            try:
                user_input = input("\n👤 Master: ")
                if user_input.strip().lower() in ['exit', 'quit']:
                    print("\n[🤖 SYSTEM] Shutting down advisor subsystem. Awaiting your next command.")
                    break
                if not user_input.strip(): continue
                print("\n   [🚀 AGENT] Processing query...")
                response = ai_assistant.chat_advisor(user_input)
                print(f"\n🤖 Mr. Agent: {response}")
            except KeyboardInterrupt:
                print("\n[🤖 SYSTEM] Emergency abort detected. Shutting down.")
                break

    elif args.profile or not any(vars(args).values()):
        print("\n[🤖 SYSTEM] Mr. Agent booting sequence initialized...")
        print("Run with --auto to enable the full autonomous capability sweep.\n")
        
if __name__ == "__main__":
    main()
