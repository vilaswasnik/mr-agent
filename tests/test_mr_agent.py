"""Tests for mr_agent.py core logic (no network calls required)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mr_agent import (
    generate_profile_suggestions,
    generate_project_ideas_fallback,
    render_report,
    _collect_tech_stack,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FULL_PROFILE = {
    "login": "testuser",
    "bio": "Full-stack developer with a passion for open source.",
    "blog": "https://testuser.dev",
    "company": "Acme Corp",
    "location": "London, UK",
    "twitter_username": "testuser",
    "public_repos": 25,
}

EMPTY_PROFILE = {
    "login": "emptyuser",
    "bio": None,
    "blog": None,
    "company": None,
    "location": None,
    "twitter_username": None,
    "public_repos": 2,
}

REPOS_WITH_METADATA = [
    {"language": "Python", "description": "A cool tool", "topics": ["python", "cli"]},
    {"language": "Python", "description": "Another project", "topics": []},
    {"language": "JavaScript", "description": None, "topics": []},
]

REPOS_WITHOUT_METADATA = [
    {"language": "Go", "description": None, "topics": []},
    {"language": "Go", "description": None, "topics": []},
]


# ---------------------------------------------------------------------------
# generate_profile_suggestions
# ---------------------------------------------------------------------------

class TestGenerateProfileSuggestions:
    def test_no_bio_triggers_suggestion(self):
        suggestions = generate_profile_suggestions(EMPTY_PROFILE, [])
        assert any("bio" in s.lower() for s in suggestions)

    def test_low_repo_count_triggers_suggestion(self):
        suggestions = generate_profile_suggestions(EMPTY_PROFILE, [])
        assert any("repositories" in s.lower() for s in suggestions)

    def test_missing_blog_triggers_suggestion(self):
        suggestions = generate_profile_suggestions(EMPTY_PROFILE, [])
        assert any("website" in s.lower() for s in suggestions)

    def test_result_capped_at_three(self):
        suggestions = generate_profile_suggestions(EMPTY_PROFILE, REPOS_WITHOUT_METADATA)
        assert len(suggestions) <= 3

    def test_returns_list(self):
        suggestions = generate_profile_suggestions(FULL_PROFILE, REPOS_WITH_METADATA)
        assert isinstance(suggestions, list)

    def test_complete_profile_fewer_suggestions(self):
        empty_suggestions = generate_profile_suggestions(EMPTY_PROFILE, [])
        full_suggestions = generate_profile_suggestions(FULL_PROFILE, REPOS_WITH_METADATA)
        # An empty profile should have at least as many suggestions as a full one
        assert len(empty_suggestions) >= len(full_suggestions)


# ---------------------------------------------------------------------------
# _collect_tech_stack
# ---------------------------------------------------------------------------

class TestCollectTechStack:
    def test_most_common_language_first(self):
        stack = _collect_tech_stack(REPOS_WITH_METADATA)
        assert stack[0] == "Python"

    def test_empty_repos(self):
        assert _collect_tech_stack([]) == []

    def test_repos_without_language(self):
        repos = [{"language": None}, {"language": None}]
        assert _collect_tech_stack(repos) == []

    def test_returns_at_most_five(self):
        repos = [{"language": f"Lang{i}"} for i in range(20)]
        stack = _collect_tech_stack(repos)
        assert len(stack) <= 5


# ---------------------------------------------------------------------------
# generate_project_ideas_fallback
# ---------------------------------------------------------------------------

class TestGenerateProjectIdeasFallback:
    def test_returns_two_ideas(self):
        ideas = generate_project_ideas_fallback(FULL_PROFILE, REPOS_WITH_METADATA)
        assert len(ideas) == 2

    def test_ideas_are_non_empty_strings(self):
        ideas = generate_project_ideas_fallback(FULL_PROFILE, REPOS_WITH_METADATA)
        for idea in ideas:
            assert isinstance(idea, str) and len(idea) > 0

    def test_fallback_with_no_repos(self):
        ideas = generate_project_ideas_fallback(EMPTY_PROFILE, [])
        assert len(ideas) == 2


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------

class TestRenderReport:
    def make_report(self):
        suggestions = ["Add a bio.", "Add a website."]
        ideas = ["Build a DeFi platform.", "Build an ML recommendation system."]
        return render_report("2026-04-24", suggestions, ideas, "vilaswasnik/mr-agent")

    def test_contains_date(self):
        report = self.make_report()
        assert "2026-04-24" in report

    def test_contains_suggestions_section(self):
        report = self.make_report()
        assert "Profile Suggestions" in report

    def test_contains_project_ideation_section(self):
        report = self.make_report()
        assert "Project Ideation" in report

    def test_suggestions_in_report(self):
        report = self.make_report()
        assert "Add a bio." in report
        assert "Add a website." in report

    def test_ideas_in_report(self):
        report = self.make_report()
        assert "Build a DeFi platform." in report
        assert "Build an ML recommendation system." in report

    def test_attribution_link(self):
        report = self.make_report()
        assert "vilaswasnik/mr-agent" in report
        assert "Mr. Agent" in report

    def test_numbered_ideas(self):
        report = self.make_report()
        assert "1." in report
        assert "2." in report
