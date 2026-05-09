import json
import os
import re
import time
from html import unescape
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


class DiceClient:
    """Utility client for monitoring Dice job listings and tracking apply queue state.

    This client does not submit applications automatically because most application
    flows require interactive auth, anti-bot checks, and dynamic forms.
    """

    def __init__(self, state_file: str = ".mr_agent_dice.json"):
        self.state_path = Path(state_file)
        self.state = self._load_state()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "seen_job_keys": [],
            "saved_jobs": [],
            "apply_queue": [],
            "preferences": {
                "query": "Senior Python Engineer",
                "location": "Remote",
                "remote": True,
                "auto_queue_new_jobs": True,
            },
        }

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self._default_state()

    def save_state(self) -> None:
        self.state_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def set_preferences(self, query: str, location: str, remote: bool, auto_queue: bool = True) -> None:
        self.state["preferences"] = {
            "query": query,
            "location": location,
            "remote": remote,
            "auto_queue_new_jobs": auto_queue,
        }
        self.save_state()

    def build_search_url(self, query: str, location: str, remote: bool) -> str:
        remote_flag = "true" if remote else "false"
        return (
            "https://www.dice.com/jobs?"
            f"q={quote_plus(query)}&location={quote_plus(location)}&radius=30&radiusUnit=mi&"
            f"countryCode=US&remote={remote_flag}"
        )

    def _download_html(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        cookie = os.getenv("DICE_COOKIE", "").strip()
        if cookie:
            headers["Cookie"] = cookie
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def _extract_next_data_json(self, html: str) -> Any:
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except Exception:
            return None

    def _walk_dicts(self, value: Any):
        if isinstance(value, dict):
            yield value
            for v in value.values():
                yield from self._walk_dicts(v)
        elif isinstance(value, list):
            for item in value:
                yield from self._walk_dicts(item)

    def _parse_jobs_from_next_data(self, data: Any) -> List[Dict[str, str]]:
        jobs = []
        seen = set()
        if not data:
            return jobs
        for obj in self._walk_dicts(data):
            title = obj.get("title") or obj.get("jobTitle")
            company = obj.get("companyName") or obj.get("company")
            job_id = obj.get("id") or obj.get("jobId") or obj.get("diceJobId")
            detail = obj.get("detailUrl") or obj.get("jobDetailUrl") or obj.get("url")
            location = obj.get("location") or obj.get("jobLocation") or "Unknown"
            posted = obj.get("postedDate") or obj.get("date") or "Unknown"

            if not title or not detail:
                continue
            if isinstance(detail, str) and detail.startswith("/"):
                detail = f"https://www.dice.com{detail}"
            if not isinstance(detail, str) or "dice.com" not in detail:
                continue

            key = str(job_id or detail)
            if key in seen:
                continue
            seen.add(key)

            jobs.append(
                {
                    "id": str(job_id or ""),
                    "title": str(title),
                    "company": str(company or "Unknown"),
                    "location": str(location),
                    "url": str(detail),
                    "posted": str(posted),
                }
            )
        return jobs

    def _parse_jobs_from_links(self, html: str) -> List[Dict[str, str]]:
        jobs = []
        seen = set()
        for href, text in re.findall(r'<a[^>]*href="([^"]*?/job-detail/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
            url = href if href.startswith("http") else f"https://www.dice.com{href}"
            title = re.sub(r"<[^>]+>", " ", unescape(text))
            title = re.sub(r"\s+", " ", title).strip()
            if not title:
                continue
            key = url
            if key in seen:
                continue
            seen.add(key)
            jobs.append(
                {
                    "id": "",
                    "title": title,
                    "company": "Unknown",
                    "location": "Unknown",
                    "url": url,
                    "posted": "Unknown",
                }
            )
        return jobs

    def fetch_jobs(self, query: str, location: str, remote: bool, max_results: int = 20) -> List[Dict[str, str]]:
        url = self.build_search_url(query, location, remote)
        html = self._download_html(url)

        jobs = self._parse_jobs_from_next_data(self._extract_next_data_json(html))
        if not jobs:
            jobs = self._parse_jobs_from_links(html)

        deduped = []
        seen_keys = set()
        for job in jobs:
            key = self._job_key(job)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(job)
        return deduped[:max_results]

    def _job_key(self, job: Dict[str, str]) -> str:
        return str(job.get("id") or job.get("url") or f"{job.get('title')}|{job.get('company')}")

    def detect_new_jobs(self, jobs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        seen = set(self.state.get("seen_job_keys", []))
        new_jobs = []
        for job in jobs:
            key = self._job_key(job)
            if key not in seen:
                new_jobs.append(job)
                seen.add(key)

        self.state["seen_job_keys"] = list(seen)[-500:]
        if self.state.get("preferences", {}).get("auto_queue_new_jobs", True):
            self.enqueue_jobs_for_apply(new_jobs)
        self.save_state()
        return new_jobs

    def enqueue_jobs_for_apply(self, jobs: List[Dict[str, str]]) -> int:
        queue = self.state.get("apply_queue", [])
        existing = {item.get("key") for item in queue}
        added = 0
        now = int(time.time())
        for job in jobs:
            key = self._job_key(job)
            if key in existing:
                continue
            queue.append(
                {
                    "key": key,
                    "status": "pending_manual_apply",
                    "created_at": now,
                    "job": job,
                }
            )
            existing.add(key)
            added += 1

        self.state["apply_queue"] = queue[-500:]
        self.save_state()
        return added

    def get_apply_queue(self, status: str = "pending_manual_apply") -> List[Dict[str, Any]]:
        queue = self.state.get("apply_queue", [])
        if not status:
            return queue
        return [item for item in queue if item.get("status") == status]

    def mark_applied(self, job_key: str) -> bool:
        changed = False
        queue = self.state.get("apply_queue", [])
        for item in queue:
            if item.get("key") == job_key:
                item["status"] = "applied"
                item["applied_at"] = int(time.time())
                changed = True
                break
        if changed:
            self.save_state()
        return changed
