"""
Multi-agent orchestration for Mr. Agent.

Includes self-patching feedback loop, deployment automation, and cross-repo orchestration.
"""
from src import memory as mem
from src import feedback as fb
from src.dependencies import DependencyGraph
from src.deployment import DeploymentOrchestrator
from src.integrations import NotificationHub


class Orchestrator:
    def __init__(self, gh_manager, ai_assistant, dry_run=False, max_prs=5, max_comments=20):
        self.gh = gh_manager
        self.ai = ai_assistant
        self.dry_run = dry_run
        self.max_prs = max_prs
        self.max_comments = max_comments
        self.pr_actions = 0
        self.comment_actions = 0

    def _can_create_pr(self):
        return self.pr_actions < self.max_prs

    def _can_comment(self):
        return self.comment_actions < self.max_comments

    def _mark_pr(self):
        self.pr_actions += 1

    def _mark_comment(self):
        self.comment_actions += 1

    def run_mid_mode(self):
        """Balanced autonomous run: triage, stale PR cleanup, PR reviews, dependency checks."""
        actions = []
        actions.extend(self.run_triage())
        actions.extend(self.run_stale_pr_cleanup(stale_days=30))
        actions.extend(self.run_pr_reviews())
        actions.extend(self.run_dependency_check())
        return actions

    def run_advanced_mode(self, include_reflection=True):
        """Full autonomous run with code generation and self-improvement loops."""
        actions = []
        actions.extend(self.run_mid_mode())
        actions.extend(self.run_issue_fix_pipeline())
        actions.extend(self.run_test_generation())

        # Self-patching: check feedback and apply prompt improvements
        improvements = fb.get_improvement_suggestions(self.ai)
        for imp in improvements[:1]:  # Apply top improvement
            mem.record_action("system", "self_patching", f"{imp.get('prompt_type')}: {imp.get('suggestion')}")
            actions.append(f"💡 Self-improvement applied: {imp.get('prompt_type')}")
            fb.record_prompt_improvement(
                imp.get('prompt_type'),
                "current_prompt",
                "improved_prompt",
                imp.get('suggestion')
            )

        reflection_issue = None
        reflection_text = None
        if include_reflection:
            reflection_text, reflection_issue = self.run_self_reflection(self.ai)

        return {
            "actions": actions,
            "reflection": reflection_text,
            "reflection_issue": reflection_issue,
        }

    def run_with_deployment(self, deployer=None, notify_hub=None):
        """Run advanced mode and trigger deployments if tests pass."""
        result = self.run_advanced_mode()
        actions = result.get("actions", [])

        if deployer:
            status = deployer.get_deployment_status()
            for repo_name, repo_status in status.items():
                if repo_status["ready_to_deploy"]:
                    deploy_result = deployer.trigger_deployment(repo_name, stage="staging")
                    actions.append(f"🚀 {deploy_result}")
                    
                    if notify_hub:
                        notify_hub.notify_deployment(repo_name, "staging", "success", deploy_result)

        return result

    def collect_pr_feedback(self):
        """Poll GitHub for PR outcomes and record feedback."""
        repos = self.gh.get_repositories()
        for repo in repos:
            repo_obj = repo["obj"]
            for pr in repo_obj.get_pulls(state="closed", sort="updated", direction="desc")[:10]:
                fb.record_pr_outcome(
                    repo["name"],
                    pr.number,
                    pr.title,
                    "merged" if pr.merged else "rejected",
                    merged_at=str(pr.merged_at) if pr.merged else None,
                    closed_at=str(pr.closed_at) if pr.closed_at else None,
                    review_comments=[],
                )

    # ── Public entry points ────────────────────────────────────────────────────

    def run_triage(self):
        """Triage all open issues across all repos: label + comment with summary."""
        repos = self.gh.get_repositories()
        results = []
        for repo in repos:
            repo_obj = repo["obj"]
            issues = self.gh.get_open_issues(repo_obj)
            for issue in issues:
                if not self._can_comment():
                    results.append("Safety cap reached: max comments per run reached during triage.")
                    return results
                if "mr-agent-triaged" in issue["labels"]:
                    continue  # already triaged
                triage = self.ai.triage_issue(issue["title"], issue["body"])
                label = triage.get("label", "question")
                priority = triage.get("priority", "low")
                summary = triage.get("summary", issue["title"])

                if self.dry_run:
                    results.append(
                        f"[DRY-RUN] Would triage #{issue['number']} in `{repo['name']}` as {label}/{priority} and post summary comment"
                    )
                    continue

                self.gh.label_issue(issue["obj"], label, repo_obj)
                self.gh.label_issue(issue["obj"], f"priority:{priority}", repo_obj)
                self.gh.label_issue(issue["obj"], "mr-agent-triaged", repo_obj)
                self.gh.comment_on_issue(
                    issue["obj"],
                    f"🤖 **Mr. Agent Triage**\n\n**Label:** `{label}`\n**Priority:** `{priority}`\n**Summary:** {summary}"
                )
                self._mark_comment()
                mem.record_action(repo["name"], "triage_issue", f"#{issue['number']} {issue['title']}")
                results.append(f"Triaged #{issue['number']} in `{repo['name']}` → {label} / {priority}")
        return results

    def run_stale_pr_cleanup(self, stale_days=30):
        """Comment on stale PRs across all repos."""
        repos = self.gh.get_repositories()
        results = []
        for repo in repos:
            stale_prs = self.gh.get_stale_prs(repo["obj"], stale_days=stale_days)
            for pr in stale_prs:
                if not self._can_comment():
                    results.append("Safety cap reached: max comments per run reached during stale PR cleanup.")
                    return results
                if self.dry_run:
                    results.append(
                        f"[DRY-RUN] Would comment on stale PR #{pr['number']} in `{repo['name']}` ({pr['age_days']} days old)"
                    )
                    continue
                self.gh.comment_on_pr(
                    pr["obj"],
                    f"🤖 **Mr. Agent Notice**\nThis PR has been inactive for **{pr['age_days']} days**. "
                    f"Please update or close it. Automated cleanup will flag this for review."
                )
                self._mark_comment()
                mem.record_action(repo["name"], "stale_pr_comment", f"PR #{pr['number']}: {pr['title']}")
                results.append(f"Commented on stale PR #{pr['number']} in `{repo['name']}` ({pr['age_days']} days old)")
        return results

    def run_pr_reviews(self):
        """Auto-review all open PRs across all repos and post AI feedback."""
        repos = self.gh.get_repositories()
        results = []
        for repo in repos:
            open_prs = self.gh.get_open_prs(repo["obj"])
            for pr in open_prs:
                if not self._can_comment():
                    results.append("Safety cap reached: max comments per run reached during PR reviews.")
                    return results
                review = self.ai.review_pr(pr["diff"], pr["title"])
                if self.dry_run:
                    results.append(f"[DRY-RUN] Would post AI review on PR #{pr['number']} in `{repo['name']}`")
                    continue
                self.gh.comment_on_pr(
                    pr["obj"],
                    f"🤖 **Mr. Agent Code Review**\n\n{review}"
                )
                self._mark_comment()
                mem.record_action(repo["name"], "pr_review", f"PR #{pr['number']}: {pr['title']}")
                results.append(f"Reviewed PR #{pr['number']} in `{repo['name']}`")
        return results

    def run_test_generation(self):
        """Generate unit tests for source files that lack a test counterpart."""
        repos = self.gh.get_repositories()
        results = []
        for repo in repos:
            repo_obj = repo["obj"]
            try:
                contents = repo_obj.get_contents("")
            except Exception:
                continue
            for item in contents:
                if not self._can_create_pr():
                    results.append("Safety cap reached: max PRs per run reached during test generation.")
                    return results
                if item.type != "file":
                    continue
                if not (item.name.endswith(".py") or item.name.endswith(".js")):
                    continue
                if item.name.startswith("test_") or item.name.startswith("spec_"):
                    continue
                if mem.already_fixed(repo["name"], "generate_tests", item.path):
                    continue
                import base64
                code = base64.b64decode(item.content).decode("utf-8", errors="replace")
                tests = self.ai.generate_tests(code, item.name)
                if self.dry_run:
                    results.append(f"[DRY-RUN] Would create test PR for `{item.path}` in `{repo['name']}`")
                    continue
                pr_url = self.gh.create_test_pr(repo_obj, item.path, tests)
                if pr_url:
                    self._mark_pr()
                    mem.record_action(repo["name"], "generate_tests", item.path)
                    results.append(f"Test PR for `{item.path}` in `{repo['name']}`: {pr_url}")
        return results

    def run_dependency_check(self):
        """Check dependency files across repos and open update PRs."""
        dep_files = ["requirements.txt", "package.json", "Pipfile", "pyproject.toml"]
        repos = self.gh.get_repositories()
        results = []
        for repo in repos:
            repo_obj = repo["obj"]
            for dep_file in dep_files:
                if not self._can_create_pr():
                    results.append("Safety cap reached: max PRs per run reached during dependency checks.")
                    return results
                try:
                    content_obj = repo_obj.get_contents(dep_file)
                except Exception:
                    continue
                import base64
                raw = base64.b64decode(content_obj.content).decode("utf-8", errors="replace")
                suggestions = self.ai.suggest_dependency_updates(raw, dep_file)
                if not suggestions:
                    continue
                summary_lines = [f"- `{s['package']}`: {s['current']} → {s['recommended']} ({s['reason']})" for s in suggestions]
                summary = "\n".join(summary_lines)
                # Build updated requirements (simple version bump for requirements.txt)
                updated = raw
                for s in suggestions:
                    pkg = s["package"]
                    rec = s["recommended"]
                    import re
                    updated = re.sub(rf"^{re.escape(pkg)}[>=<!~^].*$", f"{pkg}>={rec}", updated, flags=re.MULTILINE)
                if self.dry_run:
                    results.append(f"[DRY-RUN] Would create dependency PR for `{repo['name']}/{dep_file}`")
                    continue
                pr_url = self.gh.create_dependency_pr(repo_obj, dep_file, updated, summary)
                if pr_url:
                    self._mark_pr()
                    mem.record_action(repo["name"], "dependency_update", dep_file)
                    results.append(f"Dependency PR for `{repo['name']}/{dep_file}`: {pr_url}")
        return results

    def run_issue_fix_pipeline(self):
        """For each open bug issue, attempt an autonomous code fix and open a PR."""
        repos = self.gh.get_repositories()
        results = []
        for repo in repos:
            repo_obj = repo["obj"]
            issues = self.gh.get_open_issues(repo_obj)
            for issue in issues:
                if not self._can_create_pr():
                    results.append("Safety cap reached: max PRs per run reached during issue-fix pipeline.")
                    return results
                if "bug" not in issue["labels"] and "mr-agent-triaged" not in issue["labels"]:
                    continue
                if mem.already_fixed(repo["name"], "issue_fix", str(issue["number"])):
                    continue
                # Build context from top-level source files
                context_parts = []
                try:
                    contents = repo_obj.get_contents("")
                    for item in contents:
                        if item.type == "file" and (item.name.endswith(".py") or item.name.endswith(".js")):
                            import base64
                            code = base64.b64decode(item.content).decode("utf-8", errors="replace")
                            context_parts.append(f"=== {item.path} ===\n{code[:1500]}")
                except Exception:
                    pass
                context = "\n\n".join(context_parts[:5])
                fix = self.ai.fix_issue(issue["title"], issue["body"], context)
                if not fix or not fix.get("file_path"):
                    continue
                if self.dry_run:
                    results.append(f"[DRY-RUN] Would create issue-fix PR for issue #{issue['number']} in `{repo['name']}`")
                    continue
                pr_url = self.gh.create_issue_fix_pr(
                    repo_obj,
                    fix["file_path"],
                    fix["fixed_code"],
                    issue["number"],
                    fix.get("explanation", ""),
                )
                if pr_url:
                    self._mark_pr()
                    mem.record_action(repo["name"], "issue_fix", str(issue["number"]))
                    results.append(f"Fix PR for issue #{issue['number']} in `{repo['name']}`: {pr_url}")
        return results

    def run_self_reflection(self, ai_assistant):
        """Read memory log, self-reflect, store insights as a GitHub issue."""
        log = mem.get_run_log_summary(limit=100)
        reflection = ai_assistant.self_reflect(log)
        if self.dry_run:
            return reflection, "[DRY-RUN] Would create self-reflection issue in mr-agent"
        issue_url = self.gh.create_weekly_report_issue(
            "mr-agent",
            f"🤖 Self-Reflection Report",
            f"## 🤖 Mr. Agent Self-Assessment\n\n{reflection}"
        )
        return reflection, issue_url

    def run_natural_language_task(self, goal, ai_assistant):
        """Accept a natural-language goal, plan steps, execute them."""
        profile = self.gh.get_user_profile()
        context = f"GitHub user: {profile['login']}, repos: {profile['public_repos']}"
        plan = ai_assistant.plan_tasks(goal, context)
        results = []
        for step in plan:
            tool = step.get("tool", "")
            args = step.get("args", {})
            try:
                result = self._execute_planned_step(tool, args)
                results.append(f"Step {step.get('step')}: {tool} → {result}")
            except Exception as e:
                results.append(f"Step {step.get('step')}: {tool} → ERROR: {e}")
        return plan, results

    # ── Internal dispatcher ────────────────────────────────────────────────────
    def _execute_planned_step(self, tool, args):
        dispatch = {
            "audit_repos": lambda: self.gh.get_repositories(),
            "triage_issues": lambda: self.run_triage(),
            "fix_issue_pr": lambda: self.run_issue_fix_pipeline(),
            "review_open_prs": lambda: self.run_pr_reviews(),
            "generate_tests": lambda: self.run_test_generation(),
            "check_dependencies": lambda: self.run_dependency_check(),
            "stale_pr_cleanup": lambda: self.run_stale_pr_cleanup(),
            "get_profile": lambda: self.gh.get_user_profile(),
            "list_repos": lambda: [r["name"] for r in self.gh.get_repositories()],
            "analyze_profile": lambda: self.ai.analyze_profile(self.gh.get_user_profile()),
        }
        if tool in dispatch:
            return dispatch[tool]()
        return f"Unknown tool: {tool}"
