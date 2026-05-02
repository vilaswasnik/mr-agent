"""
Feedback learning system for Mr. Agent.
Tracks PR outcomes, collects reasons for merges/rejections, learns from patterns.
"""
import json
import os
from datetime import datetime
from src import memory as mem

FEEDBACK_FILE = os.path.join(os.path.dirname(__file__), "..", ".mr_agent_feedback.json")


def _load():
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"pr_outcomes": [], "prompt_improvements": [], "patterns": {}}


def _save(data):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record_pr_outcome(repo_name, pr_number, pr_title, status, merged_at=None, closed_at=None, review_comments=None):
    """
    Record the outcome of a PR created by the agent.
    status: 'merged', 'rejected', 'closed', 'open'
    """
    data = _load()
    data["pr_outcomes"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "repo": repo_name,
        "pr_number": pr_number,
        "pr_title": pr_title,
        "status": status,
        "merged_at": merged_at,
        "closed_at": closed_at,
        "review_comments": review_comments or [],
    })
    # Keep last 200 outcomes
    data["pr_outcomes"] = data["pr_outcomes"][-200:]
    _save(data)


def record_prompt_improvement(improvement_type, original_prompt, new_prompt, reason):
    """Record a prompt improvement applied by self-patching."""
    data = _load()
    data["prompt_improvements"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "type": improvement_type,  # e.g., "fix_code_quality", "test_generation"
        "reason": reason,
        "original_prompt_hash": hash(original_prompt),
        "improvement_description": reason,
    })
    _save(data)


def get_merge_rate():
    """Calculate PR merge success rate."""
    data = _load()
    outcomes = data["pr_outcomes"]
    if not outcomes:
        return 0.0
    merged = len([o for o in outcomes if o["status"] == "merged"])
    return merged / len(outcomes)


def get_rejection_patterns():
    """Extract common themes in rejected PRs."""
    data = _load()
    outcomes = data["pr_outcomes"]
    rejected = [o for o in outcomes if o["status"] == "rejected"]
    
    patterns = {
        "most_common_rejection_reasons": [],
        "rejected_pr_titles": [r["pr_title"] for r in rejected[-10:]],
        "total_rejected": len(rejected),
        "total_prs": len(outcomes),
    }
    
    if rejected:
        all_comments = []
        for r in rejected:
            all_comments.extend(r.get("review_comments", []))
        
        # Simple keyword extraction from comments
        keywords = {}
        for comment in all_comments:
            words = comment.lower().split()
            for word in words:
                if len(word) > 4 and word not in keywords:
                    keywords[word] = keywords.get(word, 0) + 1
        
        patterns["most_common_rejection_reasons"] = sorted(
            keywords.items(), key=lambda x: x[1], reverse=True
        )[:5]
    
    return patterns


def get_recent_outcomes(limit=20):
    """Get recent PR outcomes."""
    data = _load()
    return data["pr_outcomes"][-limit:]


def get_improvement_suggestions(ai_assistant):
    """Use AI to suggest prompt improvements based on feedback patterns."""
    patterns = get_rejection_patterns()
    recent = get_recent_outcomes(limit=30)
    merge_rate = get_merge_rate()
    
    prompt = f"""
    You are Mr. Agent's self-improvement system.
    Analyze this feedback and suggest 2-3 specific prompt improvements to increase PR merge rates.
    
    Current merge rate: {merge_rate:.1%}
    Total PRs analyzed: {patterns['total_prs']}
    Recent rejection patterns: {patterns['most_common_rejection_reasons']}
    
    Recent PR outcomes:
    {json.dumps(recent[-10:], indent=2)}
    
    Return a JSON array with:
    - "prompt_type": which prompt to improve (e.g., "fix_code", "generate_tests")
    - "issue": what's going wrong
    - "suggestion": specific improvement
    - "priority": "high", "medium", "low"
    
    Return ONLY valid JSON array.
    """
    
    response = ai_assistant.client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[{"role": "user", "content": prompt}]
    )
    
    try:
        return json.loads(response.choices[0].message.content.strip())
    except Exception:
        return []
