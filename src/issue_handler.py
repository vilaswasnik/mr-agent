import os
from github import Github
from src.ai_client import AIAssistant

def handle_issue_command():
    github_token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    repo_name = os.getenv("GITHUB_REPOSITORY")
    issue_number_str = os.getenv("ISSUE_NUMBER")

    if not all([github_token, openai_key, repo_name, issue_number_str]):
        print("Missing required environment variables for issue handler.")
        return

    try:
        issue_number = int(issue_number_str)
    except ValueError:
        print(f"Invalid ISSUE_NUMBER value: {issue_number_str!r}. ISSUE_NUMBER must be a positive integer.")
        return

    g = Github(github_token)
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(number=issue_number)
    
    # We only process issues that start with a specific format or label
    # E.g., title starts with "Command: " or "Chat: "
    user_input = f"Title: {issue.title}\nBody: {issue.body}"
    print(f"Processing issue command for Issue #{issue_number}: {issue.title}")

    ai_assistant = AIAssistant(openai_key)
    
    # Respond using the chat_advisor logic
    # We prefix a context to ensure the AI knows it's replying in a GitHub issue
    context_prefix = "The user is talking to you by opening a GitHub Issue from their mobile device. Respond directly to their request or question in a markdown format suitable for a GitHub issue comment.\n\n"
    
    response = ai_assistant.chat_advisor(context_prefix + user_input)
    
    # Add a signature
    final_comment = response + "\n\n---\n*🤖 Beep boop. I am Mr. Agent, responding from the cloud. Close this issue when you are satisfied with my response.*"
    
    issue.create_comment(final_comment)
    print(f"Successfully posted comment to Issue #{issue_number}")

if __name__ == "__main__":
    handle_issue_command()
