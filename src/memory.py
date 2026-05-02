"""
Multi-repo persistent memory for Mr. Agent.
Stores a JSON log of all actions taken, indexed by repo and date.
"""
import json
import os
from datetime import datetime

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", ".mr_agent_memory.json")


def _load():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"actions": [], "repo_context": {}}


def _save(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record_action(repo_name, action_type, detail, result="success"):
    """Record an action taken by Mr. Agent."""
    data = _load()
    data["actions"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "repo": repo_name,
        "action": action_type,
        "detail": detail,
        "result": result,
    })
    # Keep last 500 actions
    data["actions"] = data["actions"][-500:]
    _save(data)


def update_repo_context(repo_name, key, value):
    """Store arbitrary context about a repo (e.g. last fix, known issues)."""
    data = _load()
    if repo_name not in data["repo_context"]:
        data["repo_context"][repo_name] = {}
    data["repo_context"][repo_name][key] = value
    data["repo_context"][repo_name]["last_seen"] = datetime.utcnow().isoformat()
    _save(data)


def get_repo_context(repo_name):
    data = _load()
    return data["repo_context"].get(repo_name, {})


def get_recent_actions(limit=50):
    data = _load()
    return data["actions"][-limit:]


def get_run_log_summary(limit=100):
    """Return a text summary of recent actions for self-reflection."""
    actions = get_recent_actions(limit)
    if not actions:
        return "No previous actions recorded."
    lines = []
    for a in actions:
        lines.append(f"[{a['timestamp']}] {a['repo']} | {a['action']} | {a['detail']} -> {a['result']}")
    return "\n".join(lines)


def already_fixed(repo_name, action_type, detail):
    """Check if the same action was already done recently (avoid duplicates)."""
    data = _load()
    for a in reversed(data["actions"][-100:]):
        if a["repo"] == repo_name and a["action"] == action_type and a["detail"] == detail and a["result"] == "success":
            return True
    return False
