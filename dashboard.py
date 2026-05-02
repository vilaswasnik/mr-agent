"""
Real-time monitoring dashboard for Mr. Agent.
Streamlit-based visualization of agent activity, performance, deployment status.
"""
import streamlit as st
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.github_client import GitHubManager
from src.ai_client import AIAssistant
from src import memory as mem
from src import feedback
from src.dependencies import DependencyGraph
from src.deployment import DeploymentOrchestrator
from src.integrations import NotificationHub

load_dotenv(override=True)

st.set_page_config(page_title="Mr. Agent Dashboard", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3 { color: #58a6ff; }
    .metric { background-color: #161b22; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Mr. Agent Mission Control")

# Initialize clients
github_token = os.getenv("GITHUB_TOKEN", "").strip()
openai_key = os.getenv("OPENAI_API_KEY", "").strip()

try:
    gh_manager = GitHubManager(github_token)
    ai_assistant = AIAssistant(openai_key)
except Exception as e:
    st.error(f"Failed to connect: {e}")
    st.stop()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Activity", "🧠 Feedback", "🔗 Dependencies", "🚀 Deployments", "⚙️ Config"])

# ── TAB 1: Activity Dashboard ──────────────────────────────────────────────────
with tab1:
    st.subheader("Recent Agent Activity")
    
    col1, col2, col3 = st.columns(3)
    
    recent_actions = mem.get_recent_actions(limit=50)
    
    with col1:
        st.metric("Actions (24h)", len([a for a in recent_actions if (datetime.utcnow() - datetime.fromisoformat(a["timestamp"])).days < 1]))
    
    with col2:
        repos = gh_manager.get_repositories()
        st.metric("Total Repos", len(repos))
    
    with col3:
        merge_rate = feedback.get_merge_rate()
        st.metric("PR Merge Rate", f"{merge_rate:.0%}")
    
    st.divider()
    
    if recent_actions:
        st.write("#### Latest 10 Actions")
        for action in reversed(recent_actions[-10:]):
            with st.container():
                col1, col2, col3 = st.columns([2, 3, 1])
                with col1:
                    st.caption(action["timestamp"][-5:])
                with col2:
                    st.write(f"`{action['repo']}` • {action['action']}")
                with col3:
                    status_color = "🟢" if action["result"] == "success" else "🔴"
                    st.caption(f"{status_color} {action['result']}")
    
    st.divider()
    
    st.write("#### Run History")
    history = mem.get_recent_actions(limit=100)
    action_counts = {}
    for h in history:
        action_counts[h["action"]] = action_counts.get(h["action"], 0) + 1
    
    if action_counts:
        st.bar_chart(action_counts)

# ── TAB 2: Feedback & Learning ─────────────────────────────────────────────────
with tab2:
    st.subheader("🧠 Agent Learning & Feedback")
    
    col1, col2, col3 = st.columns(3)
    
    merge_rate = feedback.get_merge_rate()
    patterns = feedback.get_rejection_patterns()
    
    with col1:
        st.metric("PR Merge Rate", f"{merge_rate:.0%}")
    with col2:
        st.metric("Total PRs", patterns["total_prs"])
    with col3:
        st.metric("Rejected", patterns["total_rejected"])
    
    st.divider()
    
    if patterns["most_common_rejection_reasons"]:
        st.write("#### Common Rejection Reasons")
        reasons = patterns["most_common_rejection_reasons"][:5]
        for word, count in reasons:
            st.write(f"- `{word}`: {count} mentions")
    
    st.divider()
    
    st.write("#### AI Improvement Suggestions")
    suggestions = feedback.get_improvement_suggestions(ai_assistant)
    if suggestions:
        for s in suggestions[:3]:
            st.info(f"**{s.get('prompt_type', 'N/A')}** [{s.get('priority', 'N/A')}]\n{s.get('suggestion', '')}")
    else:
        st.caption("No suggestions available yet (need more PR history)")

# ── TAB 3: Dependency Graph ────────────────────────────────────────────────────
with tab3:
    st.subheader("🔗 Cross-Repo Dependencies")
    
    dep_graph = DependencyGraph(gh_manager)
    
    st.write("#### Dependency Graph")
    graph_viz = dep_graph.visualize()
    st.code(graph_viz, language="text")
    
    st.divider()
    
    circular = dep_graph.detect_circular_deps()
    if circular:
        st.warning(f"⚠️ Circular dependencies detected: {circular}")
    else:
        st.success("✅ No circular dependencies")

# ── TAB 4: Deployments ─────────────────────────────────────────────────────────
with tab4:
    st.subheader("🚀 Deployment Status")
    
    deployer = DeploymentOrchestrator(gh_manager)
    status = deployer.get_deployment_status()
    
    if status:
        for repo_name, repo_status in status.items():
            with st.container():
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**{repo_name}**")
                with col2:
                    tests_emoji = "🟢" if repo_status["tests_passing"] else "🔴"
                    st.caption(f"{tests_emoji} Tests: {'Passing' if repo_status['tests_passing'] else 'Failing'}")
                with col3:
                    st.caption(f"Pending: {repo_status['pending_changes']} changes")
                with col4:
                    if repo_status["ready_to_deploy"]:
                        if st.button(f"Deploy {repo_name}", key=f"deploy_{repo_name}"):
                            result = deployer.trigger_deployment(repo_name, stage="staging")
                            st.success(result)
                    else:
                        st.caption("Not ready")
    else:
        st.info("No deployments configured. Configure webhooks in .mr_agent_deploy.json")

# ── TAB 5: Configuration ───────────────────────────────────────────────────────
with tab5:
    st.subheader("⚙️ Configuration")
    
    st.write("#### Environment Variables")
    st.code(f"""
GITHUB_TOKEN: {'✅ Set' if github_token else '❌ Missing'}
OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Missing'}
SLACK_WEBHOOK_URL: {'✅ Set' if os.getenv('SLACK_WEBHOOK_URL') else '❌ Not configured'}
DISCORD_WEBHOOK_URL: {'✅ Set' if os.getenv('DISCORD_WEBHOOK_URL') else '❌ Not configured'}
    """)
    
    st.divider()
    
    st.write("#### Quick Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Dashboard"):
            st.rerun()
    
    with col2:
        if st.button("🚨 Trigger Dry-Run"):
            st.info("Use CLI: `python main.py --advanced --dry-run`")

if __name__ == "__main__":
    pass
