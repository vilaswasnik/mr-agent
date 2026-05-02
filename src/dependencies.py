"""
Cross-repo dependency detection and orchestration.
Identifies shared dependencies, detects breaking changes, coordinates fixes.
"""
import json
import re

class DependencyGraph:
    def __init__(self, gh_manager):
        self.gh = gh_manager
        self.graph = {}  # repo -> {imports: [], depends_on: []}
        self.build()

    def build(self):
        """Scan all repos to detect dependencies."""
        repos = self.gh.get_repositories()
        for repo in repos:
            repo_obj = repo["obj"]
            self.graph[repo["name"]] = {
                "imports": self.extract_imports(repo_obj),
                "depends_on": [],
            }
        
        # Link dependencies
        for repo_name, data in self.graph.items():
            for imp in data["imports"]:
                for other_repo in self.graph.keys():
                    if repo_name != other_repo and self._is_internal_import(imp, other_repo):
                        if other_repo not in data["depends_on"]:
                            data["depends_on"].append(other_repo)

    def extract_imports(self, repo_obj):
        """Extract imports from Python/JS files in repo."""
        imports = []
        try:
            contents = repo_obj.get_contents("")
            for item in contents:
                if not item.name.endswith((".py", ".js")):
                    continue
                import base64
                try:
                    code = base64.b64decode(item.content).decode("utf-8", errors="replace")
                    # Extract imports
                    py_imports = re.findall(r"^(?:from|import)\s+([\w\.]+)", code, re.MULTILINE)
                    js_imports = re.findall(r"(?:import|require)\s+[\w*\s{},]*\s+from\s+['\"]([^'\"]+)['\"]", code)
                    imports.extend(py_imports + js_imports)
                except Exception:
                    pass
        except Exception:
            pass
        return list(set(imports))

    def _is_internal_import(self, import_name, repo_name):
        """Check if import refers to internal repo."""
        return import_name.replace("-", "_") == repo_name.replace("-", "_")

    def get_dependents(self, repo_name):
        """Get all repos that depend on this repo."""
        dependents = []
        for r, data in self.graph.items():
            if repo_name in data.get("depends_on", []):
                dependents.append(r)
        return dependents

    def get_fix_order(self, modified_repo):
        """Return order to apply fixes: modified repo first, then dependents."""
        order = [modified_repo]
        visited = {modified_repo}
        queue = [modified_repo]
        
        while queue:
            current = queue.pop(0)
            for dependent in self.get_dependents(current):
                if dependent not in visited:
                    order.append(dependent)
                    visited.add(dependent)
                    queue.append(dependent)
        
        return order

    def visualize(self):
        """Return ASCII graph visualization."""
        lines = []
        for repo, data in sorted(self.graph.items()):
            if data["depends_on"]:
                deps = " → ".join(data["depends_on"])
                lines.append(f"{repo} → {deps}")
            else:
                lines.append(f"{repo} (no cross-repo deps)")
        return "\n".join(lines)

    def detect_circular_deps(self):
        """Find circular dependencies."""
        circular = []
        for repo in self.graph:
            visited = set()
            path = [repo]
            if self._has_cycle(repo, visited, path):
                circular.append(path)
        return circular

    def _has_cycle(self, node, visited, path):
        visited.add(node)
        for neighbor in self.graph.get(node, {}).get("depends_on", []):
            if neighbor not in visited:
                path.append(neighbor)
                if self._has_cycle(neighbor, visited, path):
                    return True
                path.pop()
            elif neighbor in path:
                return True
        return False
