import os
from github import Github
from src.ai_client import AIAssistant
from src.github_client import GitHubManager

def handle_issue_command():
    github_token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    repo_name = os.getenv("GITHUB_REPOSITORY")
    issue_number = int(os.getenv("ISSUE_NUMBER"))

    if not all([github_token, openai_key, repo_name, issue_number]):
        print("Missing required environment variables for issue handler.")
        return

    g = Github(github_token)
    gh_manager = GitHubManager(github_token)
    ai_assistant = AIAssistant(openai_key)
    
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(number=issue_number)
    
    title_lower = issue.title.strip().lower()
    body = issue.body if issue.body else ""
    
    response_text = ""
    
    if title_lower.startswith("command: update"):
        # Format: "Command: update <repo> <file_path>"
        # The body of the issue contains the PROMPT explaining WHAT to change in the file.
        parts = issue.title.split()
        if len(parts) >= 4:
            target_repo = parts[2]
            file_path = parts[3]
            code = gh_manager.get_file_content(target_repo, file_path)
            
            if code:
                # Custom AI call to update code based on the user's issue body (the prompt)
                update_prompt = f"""
                Act as an autonomous AI engineer updating a file.
                The user has requested the following change: "{body}"
                
                Apply this change to the following code from the file '{file_path}'.
                CRITICAL INSTRUCTION: Output ONLY the raw corrected code. Do NOT wrap in markdown code blocks like ```javascript or ```python. Do NOT include any explanations. Just the raw code text that can be directly written to the file.
                
                Code to update:
                {code}
                """
                response = ai_assistant.client.chat.completions.create(
                    model=ai_assistant.model,
                    messages=[{"role": "user", "content": update_prompt}]
                )
                updated_code = response.choices[0].message.content.strip()
                if updated_code.startswith("```"):
                    lines = updated_code.split('\n')
                    if len(lines) > 2:
                        updated_code = '\n'.join(lines[1:-1])
                        
                repo_obj = g.get_repo(f"{gh_manager.user.login}/{target_repo}")
                pr_url = gh_manager.create_fix_pr(repo_obj, file_path, updated_code)
                
                if pr_url:
                     response_text = f"✅ **SUCCESS:** Autonomous modification initiated remotely. I have updated `{file_path}` according to your instructions and deployed a payload here: {pr_url}"
                else:
                     response_text = "❌ **SYSTEM ERROR:** Failed to deploy PR payload. Branch might already exist or there is a permissions issue."
            else:
                response_text = f"❌ **SYSTEM ERROR:** Could not locate `{file_path}` in `{target_repo}`."
        else:
            response_text = "⚠️ **Invalid syntax.** Use: `Command: update <repo> <file_path>`"
            
    elif title_lower.startswith("command: fix"):
        parts = issue.title.split()
        if len(parts) >= 4:
            target_repo = parts[2]
            file_path = parts[3]
            code = gh_manager.get_file_content(target_repo, file_path)
            if code:
                fixed_code = ai_assistant.fix_code(code, file_path)
                repo_obj = g.get_repo(f"{gh_manager.user.login}/{target_repo}")
                pr_url = gh_manager.create_fix_pr(repo_obj, file_path, fixed_code)
                if pr_url:
                     response_text = f"✅ **SUCCESS:** Autonomous repair initiated remotely. I have rewritten `{file_path}` and deployed a payload here: {pr_url}"
                else:
                     response_text = "❌ **SYSTEM ERROR:** Failed to deploy PR payload. Branch might already exist or there is a permissions issue."
            else:
                response_text = f"❌ **SYSTEM ERROR:** Could not locate `{file_path}` in `{target_repo}`."
        else:
            response_text = "⚠️ **Invalid syntax.** Use: `Command: fix <repo> <file_path>`"
            
    elif title_lower.startswith("command: review"):
        parts = issue.title.split()
        if len(parts) >= 4:
            target_repo = parts[2]
            file_path = parts[3]
            code = gh_manager.get_file_content(target_repo, file_path)
            if code:
                review = ai_assistant.review_code(code, file_path)
                response_text = f"🕵️‍♂️ **Remote Review for `{file_path}` in `{target_repo}`:**\n\n{review}"
            else:
                response_text = f"❌ **SYSTEM ERROR:** Could not locate `{file_path}` in `{target_repo}`."
        else:
            response_text = "⚠️ **Invalid syntax.** Use: `Command: review <repo> <file_path>`"
            
    elif title_lower.startswith("command: fetch"):
        parts = issue.title.split()
        if len(parts) >= 4:
            target_repo = parts[2]
            file_path = parts[3]
            code = gh_manager.get_file_content(target_repo, file_path)
            if code:
                response_text = f"📄 **Contents of `{file_path}` in `{target_repo}`:**\n\n```\n{code[:4000]}\n```\n*(Truncated if exceedingly large)*"
            else:
                response_text = f"❌ **SYSTEM ERROR:** Could not locate `{file_path}` in `{target_repo}`."
        else:
            response_text = "⚠️ **Invalid syntax.** Use: `Command: fetch <repo> <file_path>`"

    else:
        # Default Chat / Advisor Mode
        user_input = f"Title: {issue.title}\nBody: {body}"
        context_prefix = "The user is communicating securely from a remote mobile device. Respond directly with high intelligence, offering action plans or troubleshooting steps.\n\n"
        response_text = ai_assistant.chat_advisor(context_prefix + user_input)

    final_comment = response_text + "\n\n---\n*🤖 Beep boop. Action authorized and executed via remote protocol.*"
    issue.create_comment(final_comment)
    print(f"Successfully posted comment to Issue #{issue_number}")

if __name__ == "__main__":
    handle_issue_command()
