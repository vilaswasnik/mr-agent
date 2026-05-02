"""
Third-party integrations: Slack, Discord, GitHub Projects.
"""
import requests
import json
import os

class SlackNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    def send(self, title, message, color="good", fields=None):
        if not self.webhook_url:
            return False
        
        payload = {
            "attachments": [{
                "title": title,
                "text": message,
                "color": color,
                "fields": fields or [],
            }]
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload)
            return response.status_code in [200, 201]
        except Exception:
            return False

    def notify_pr_created(self, repo_name, pr_number, pr_title, pr_url):
        return self.send(
            title=f"🤖 PR Created: {repo_name}",
            message=f"[{pr_number}] {pr_title}",
            color="good",
            fields=[{"title": "Link", "value": pr_url, "short": False}]
        )

    def notify_merge_rate(self, merge_rate):
        color = "good" if merge_rate > 0.7 else "warning" if merge_rate > 0.5 else "danger"
        return self.send(
            title="📊 Agent Performance",
            message=f"PR merge rate: {merge_rate:.1%}",
            color=color,
        )

class DiscordNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")

    def send(self, title, message, color_hex="00FF00"):
        if not self.webhook_url:
            return False
        
        embed = {
            "title": title,
            "description": message,
            "color": int(color_hex, 16),
        }
        
        try:
            response = requests.post(self.webhook_url, json={"embeds": [embed]})
            return response.status_code in [200, 201, 204]
        except Exception:
            return False

    def notify_pr_created(self, repo_name, pr_number, pr_title, pr_url):
        return self.send(
            title=f"🤖 PR Created in {repo_name}",
            message=f"**[#{pr_number}]** {pr_title}\n[View PR]({pr_url})",
            color_hex="00AA00"
        )

class GitHubProjectManager:
    def __init__(self, gh_manager, project_id=None):
        self.gh = gh_manager
        self.project_id = project_id

    def add_pr_to_project(self, pr_url, status="In Progress"):
        """Add a PR card to a GitHub Project board."""
        # This requires GraphQL queries to GitHub Projects API v2
        # Placeholder for now - would need actual implementation
        return True

    def update_project_card(self, card_id, status):
        """Update project card status."""
        # Placeholder
        return True

    def create_project_card_from_pr(self, repo_name, pr_number, pr_title):
        """Create a project card for a PR."""
        # Placeholder
        return True

class NotificationHub:
    """Central hub for all notifications."""
    def __init__(self):
        self.slack = SlackNotifier()
        self.discord = DiscordNotifier()
        self.github_project = None

    def notify_all(self, title, message, notification_type="info"):
        """Send notification to all configured channels."""
        results = {
            "slack": self.slack.send(title, message),
            "discord": self.discord.send(title, message),
        }
        return results

    def notify_pr_created(self, repo_name, pr_number, pr_title, pr_url):
        results = {
            "slack": self.slack.notify_pr_created(repo_name, pr_number, pr_title, pr_url),
            "discord": self.discord.notify_pr_created(repo_name, pr_number, pr_title, pr_url),
        }
        return results

    def notify_deployment(self, repo_name, stage, status, details=""):
        title = f"🚀 Deployment: {repo_name} → {stage}"
        message = f"Status: {status}\n{details}"
        color = "good" if status == "success" else "danger"
        return self.notify_all(title, message)

    def notify_feedback_loop(self, improvement_type, reason):
        title = f"🧠 Self-Improvement Applied"
        message = f"**Type:** {improvement_type}\n**Reason:** {reason}"
        return self.notify_all(title, message)
