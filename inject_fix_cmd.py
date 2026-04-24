with open("main.py", "r") as f:
    text = f.read()

code_to_insert = """
    elif args.fix:
        repo_target, file_path = args.fix
        print(f"\\n[🤖 SYSTEM] INITIATING AUTONOMOUS REPAIR ON {file_path} IN {repo_target}...")
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
"""

text = text.replace("    elif args.review:", code_to_insert + "\n    elif args.review:")

with open("main.py", "w") as f:
    f.write(text)

