"""
Deployment automation orchestrator.
After tests pass and PRs merge, auto-deploy to staging/production.
"""
import json
import os
from datetime import datetime

class DeploymentOrchestrator:
    def __init__(self, gh_manager, config_file=None):
        self.gh = gh_manager
        self.config = self.load_config(config_file or ".mr_agent_deploy.json")

    def load_config(self, config_file):
        """Load deployment config (repos, stages, webhooks, etc.)"""
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "deployments": {},  # repo_name -> {staging_webhook, prod_webhook, auto_deploy}
            "deployment_log": [],
        }

    def save_config(self):
        """Save deployment config."""
        with open(".mr_agent_deploy.json", "w") as f:
            json.dump(self.config, f, indent=2)

    def register_deployment_webhook(self, repo_name, staging_url, prod_url, auto_deploy_staging=True):
        """Register webhooks for a repo's deployment."""
        if repo_name not in self.config["deployments"]:
            self.config["deployments"][repo_name] = {}
        self.config["deployments"][repo_name].update({
            "staging_webhook": staging_url,
            "prod_webhook": prod_url,
            "auto_deploy_staging": auto_deploy_staging,
            "last_deploy": None,
        })
        self.save_config()

    def get_merged_prs_since_last_deploy(self, repo_name):
        """Get PRs that merged since the last deployment."""
        repo_config = self.config["deployments"].get(repo_name, {})
        repo_obj = self.gh.github.get_repo(f"{self.gh.user.login}/{repo_name}")
        
        merged_prs = []
        for pr in repo_obj.get_pulls(state="closed"):
            if not pr.merged:
                continue
            if repo_config.get("last_deploy"):
                from datetime import datetime as dt
                last_deploy = dt.fromisoformat(repo_config["last_deploy"])
                if pr.merged_at < last_deploy:
                    continue
            merged_prs.append({"number": pr.number, "title": pr.title, "merged_at": str(pr.merged_at)})
        
        return merged_prs

    def check_tests_passing(self, repo_name):
        """Check if latest workflow run passed."""
        repo_obj = self.gh.github.get_repo(f"{self.gh.user.login}/{repo_name}")
        try:
            latest_runs = list(repo_obj.get_workflow_runs()[:1])
            if latest_runs:
                run = latest_runs[0]
                return run.conclusion == "success"
        except Exception:
            pass
        return False

    def trigger_deployment(self, repo_name, stage="staging", dry_run=False):
        """
        Trigger deployment to staging or production.
        stage: 'staging' or 'production'
        """
        repo_config = self.config["deployments"].get(repo_name)
        if not repo_config:
            return f"No deployment config for {repo_name}"

        webhook_url = repo_config.get(f"{stage}_webhook")
        if not webhook_url:
            return f"No {stage} webhook configured for {repo_name}"

        if not self.check_tests_passing(repo_name):
            return f"Cannot deploy {repo_name}: tests not passing"

        merged_prs = self.get_merged_prs_since_last_deploy(repo_name)
        if not merged_prs and stage == "staging":
            return f"No new PRs merged in {repo_name}, skipping deployment"

        if dry_run:
            return f"[DRY-RUN] Would deploy {repo_name} to {stage} with {len(merged_prs)} changes"

        # Trigger webhook (in real scenario, call webhook URL)
        import requests
        try:
            response = requests.post(webhook_url, json={
                "repo": repo_name,
                "stage": stage,
                "prs": merged_prs,
                "deployed_at": datetime.utcnow().isoformat(),
            })
            
            self.config["deployments"][repo_name]["last_deploy"] = datetime.utcnow().isoformat()
            self.config["deployment_log"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "repo": repo_name,
                "stage": stage,
                "status": "success" if response.status_code in [200, 201] else "failed",
                "prs_deployed": len(merged_prs),
            })
            self.save_config()
            
            return f"Deployed {repo_name} to {stage}. {len(merged_prs)} changes. Status: {response.status_code}"
        except Exception as e:
            self.config["deployment_log"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "repo": repo_name,
                "stage": stage,
                "status": "error",
                "error": str(e),
            })
            self.save_config()
            return f"Deployment failed: {e}"

    def auto_deploy_after_merge(self, repo_name):
        """Auto-deploy staging when PRs merge, prompt for prod."""
        result = self.trigger_deployment(repo_name, stage="staging")
        return result

    def get_deployment_status(self):
        """Return current deployment status for all repos."""
        status = {}
        for repo_name in self.config["deployments"]:
            config = self.config["deployments"][repo_name]
            last_deploy = config.get("last_deploy", "Never")
            tests_passing = self.check_tests_passing(repo_name)
            merged_prs = self.get_merged_prs_since_last_deploy(repo_name)
            status[repo_name] = {
                "last_deploy": last_deploy,
                "tests_passing": tests_passing,
                "pending_changes": len(merged_prs),
                "ready_to_deploy": tests_passing and len(merged_prs) > 0,
            }
        return status
