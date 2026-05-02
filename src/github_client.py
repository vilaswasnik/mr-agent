from github import Github
from github.GithubException import UnknownObjectException

class GitHubManager:
    def __init__(self, token):
        self.github = Github(token)
        self.user = self.github.get_user()
        
    def get_user_profile(self):
        return {
            "login": self.user.login,
            "name": self.user.name,
            "bio": self.user.bio,
            "public_repos": self.user.public_repos,
            "followers": self.user.followers,
            "company": self.user.company,
            "blog": self.user.blog,
        }

    def get_repositories(self):
        repos = []
        for repo in self.user.get_repos(type="owner"):
            # skip a few to avoid taking too long in bulk commands
            try:
                repo.get_readme()
                has_readme = True
            except UnknownObjectException:
                has_readme = False
                
            repos.append({
                "name": repo.name,
                "description": repo.description or "No description",
                "language": repo.language or "Unknown",
                "stars": repo.stargazers_count,
                "has_readme": has_readme,
                "obj": repo
            })
        return repos

    def update_repo_description(self, repo_obj, new_description):
        try:
            repo_obj.edit(description=new_description)
            return True
        except Exception as e:
            print(f"[ERROR] SYSTEM OVERRIDE FAILED - Could not update description: {e}")
            return False

    def create_readme_pr(self, repo_obj, readme_content):
        default_branch = repo_obj.default_branch
        ref = repo_obj.get_git_ref(f"heads/{default_branch}")
        
        branch_name = f"🤖-mr-agent-add-readme"
        try:
            repo_obj.create_git_ref(ref=f"refs/heads/{branch_name}", sha=ref.object.sha)
        except Exception as e:
            # Branch exists, update instead
            return None
            
        repo_obj.create_file(
            path="README.md",
            message="docs(🤖): inject auto-generated README.md via autonomous protocol",
            content=readme_content,
            branch=branch_name
        )
        
        pr = repo_obj.create_pull(
            title="🤖 SYSTEM OVERRIDE: Automated README Injection",
            body="""The autonomous monitoring protocol detected a missing README.md payload.\n\nMr. Agent has successfully orchestrated documentation algorithms to build the requisite file.\n\nPlease review and merge human!""",
            head=branch_name,
            base=default_branch
        )
        return pr.html_url

    # ── NEW: Get open issues ───────────────────────────────────────────────────
    def get_open_issues(self, repo_obj, limit=20):
        issues = []
        for issue in repo_obj.get_issues(state="open"):
            if issue.pull_request:
                continue  # skip PRs listed as issues
            issues.append({
                "number": issue.number,
                "title": issue.title,
                "body": issue.body or "",
                "labels": [l.name for l in issue.labels],
                "created_at": str(issue.created_at),
                "obj": issue,
            })
            if len(issues) >= limit:
                break
        return issues

    def label_issue(self, issue_obj, label_name, repo_obj):
        try:
            try:
                repo_obj.get_label(label_name)
            except Exception:
                repo_obj.create_label(label_name, "0075ca")
            issue_obj.add_to_labels(label_name)
            return True
        except Exception as e:
            print(f"[ERROR] Could not label issue: {e}")
            return False

    def comment_on_issue(self, issue_obj, comment_body):
        try:
            issue_obj.create_comment(comment_body)
            return True
        except Exception as e:
            print(f"[ERROR] Could not comment on issue: {e}")
            return False

    # ── NEW: Stale PR detection ────────────────────────────────────────────────
    def get_stale_prs(self, repo_obj, stale_days=30):
        from datetime import datetime, timezone
        stale = []
        for pr in repo_obj.get_pulls(state="open"):
            age = (datetime.now(timezone.utc) - pr.updated_at).days
            if age >= stale_days:
                stale.append({"number": pr.number, "title": pr.title, "age_days": age, "obj": pr})
        return stale

    def comment_on_pr(self, pr_obj, comment_body):
        try:
            pr_obj.create_issue_comment(comment_body)
            return True
        except Exception as e:
            print(f"[ERROR] Could not comment on PR: {e}")
            return False

    # ── NEW: Get open PRs with diff ────────────────────────────────────────────
    def get_open_prs(self, repo_obj, limit=10):
        prs = []
        for pr in repo_obj.get_pulls(state="open"):
            files = list(pr.get_files())
            diff_summary = "\n".join(
                f"--- {f.filename} (+{f.additions}/-{f.deletions})\n{f.patch or ''}"
                for f in files[:5]
            )
            prs.append({
                "number": pr.number,
                "title": pr.title,
                "diff": diff_summary,
                "obj": pr,
            })
            if len(prs) >= limit:
                break
        return prs

    # ── NEW: Create test file PR ──────────────────────────────────────────────
    def create_test_pr(self, repo_obj, source_file_path, test_content):
        import time
        default_branch = repo_obj.default_branch
        ref = repo_obj.get_git_ref(f"heads/{default_branch}")
        branch_name = f"mr-agent-tests-{int(time.time())}"
        try:
            repo_obj.create_git_ref(ref=f"refs/heads/{branch_name}", sha=ref.object.sha)
        except Exception as e:
            print(f"Branch error: {e}")
            return None

        # Determine test file path
        parts = source_file_path.rsplit(".", 1)
        test_path = f"tests/test_{parts[0].replace('/', '_')}.{'py' if len(parts) < 2 else parts[1]}"

        try:
            existing = repo_obj.get_contents(test_path)
            repo_obj.update_file(test_path, f"test(🤖): update tests for {source_file_path}", test_content, existing.sha, branch=branch_name)
        except Exception:
            repo_obj.create_file(test_path, f"test(🤖): add unit tests for {source_file_path}", test_content, branch=branch_name)

        pr = repo_obj.create_pull(
            title=f"🤖 Auto-generated tests for {source_file_path}",
            body=f"Mr. Agent detected no test coverage for `{source_file_path}` and generated unit tests.\n\nPlease review and merge!",
            head=branch_name,
            base=default_branch,
        )
        return pr.html_url

    # ── NEW: Create dependency update PR ─────────────────────────────────────
    def create_dependency_pr(self, repo_obj, deps_file_path, updated_content, summary):
        import time
        default_branch = repo_obj.default_branch
        ref = repo_obj.get_git_ref(f"heads/{default_branch}")
        branch_name = f"mr-agent-deps-{int(time.time())}"
        try:
            repo_obj.create_git_ref(ref=f"refs/heads/{branch_name}", sha=ref.object.sha)
        except Exception as e:
            print(f"Branch error: {e}")
            return None

        file_sha = repo_obj.get_contents(deps_file_path).sha
        repo_obj.update_file(deps_file_path, "chore(🤖): update dependencies via autonomous audit", updated_content, file_sha, branch=branch_name)

        pr = repo_obj.create_pull(
            title=f"🤖 Dependency Updates for {repo_obj.name}",
            body=f"Mr. Agent identified outdated/vulnerable packages:\n\n{summary}\n\nPlease review and merge!",
            head=branch_name,
            base=default_branch,
        )
        return pr.html_url

    # ── NEW: Issue fix PR ─────────────────────────────────────────────────────
    def create_issue_fix_pr(self, repo_obj, file_path, new_content, issue_number, explanation):
        import time
        default_branch = repo_obj.default_branch
        ref = repo_obj.get_git_ref(f"heads/{default_branch}")
        branch_name = f"mr-agent-issue-{issue_number}-fix-{int(time.time())}"
        try:
            repo_obj.create_git_ref(ref=f"refs/heads/{branch_name}", sha=ref.object.sha)
        except Exception as e:
            print(f"Branch error: {e}")
            return None

        try:
            existing = repo_obj.get_contents(file_path)
            repo_obj.update_file(file_path, f"fix(🤖): resolve issue #{issue_number}", new_content, existing.sha, branch=branch_name)
        except Exception:
            repo_obj.create_file(file_path, f"fix(🤖): resolve issue #{issue_number}", new_content, branch=branch_name)

        pr = repo_obj.create_pull(
            title=f"🤖 Fix for Issue #{issue_number}",
            body=f"Closes #{issue_number}\n\nMr. Agent autonomously resolved this issue.\n\n**Changes:** {explanation}",
            head=branch_name,
            base=default_branch,
        )
        return pr.html_url

    # ── NEW: Get latest workflow run log ──────────────────────────────────────
    def get_latest_workflow_log(self, repo_obj):
        try:
            runs = list(repo_obj.get_workflow_runs()[:1])
            if not runs:
                return "No workflow runs found."
            run = runs[0]
            return f"Run: {run.name} | Status: {run.status} | Conclusion: {run.conclusion} | At: {run.created_at}"
        except Exception as e:
            return f"Could not fetch workflow runs: {e}"

    def get_file_content(self, repo_name, file_path):
        try:
            repo = self.github.get_repo(f"{self.user.login}/{repo_name}")
            file_content = repo.get_contents(file_path)
            import base64
            return base64.b64decode(file_content.content).decode('utf-8')
        except Exception as e:
            print(f"Could not get file {file_path} from {repo_name}: {e}")
            return None

    def create_weekly_report_issue(self, repo_name, report_title, report_body):
        try:
            repo = self.github.get_repo(f"{self.user.login}/{repo_name}")
            issue = repo.create_issue(title=report_title, body=report_body)
            return issue.html_url
        except Exception as e:
            print(f"Could not create issue: {e}")
            return None

    def create_fix_pr(self, repo_obj, file_path, new_content):
        import time
        default_branch = repo_obj.default_branch
        ref = repo_obj.get_git_ref(f"heads/{default_branch}")
        
        sanitized_path = file_path.replace('/', '-')
        branch_name = f"🤖-mr-agent-fix-{sanitized_path}-{int(time.time())}"
        
        try:
            repo_obj.create_git_ref(ref=f"refs/heads/{branch_name}", sha=ref.object.sha)
        except Exception as e:
            print(f"Branch error: {e}")
            return None
            
        file_sha = repo_obj.get_contents(file_path).sha
        
        repo_obj.update_file(
            path=file_path,
            message=f"refactor(🤖): autonomous logic optimization for {file_path}",
            content=new_content,
            sha=file_sha,
            branch=branch_name
        )
        
        pr = repo_obj.create_pull(
            title=f"🤖 SYSTEM OVERRIDE: Code Optimization for {file_path}",
            body=f"The autonomous anomaly detection protocol analyzed `{file_path}` and determined structural/security upgrades were required.\n\nChanges executed: Logic standardization, readability and performance enhancements.\n\nPlease review and merge human!",
            head=branch_name,
            base=default_branch
        )
        return pr.html_url
