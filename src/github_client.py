import base64
import time
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

    def get_file_content(self, repo_name, file_path):
        try:
            repo = self.github.get_repo(f"{self.user.login}/{repo_name}")
            file_content = repo.get_contents(file_path)
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
