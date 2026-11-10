"""Small GitHub REST client with polite rate-limit handling."""

import os
import re
import subprocess
import time

import requests

API = "https://api.github.com"


def find_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:  # local convenience: reuse the gh CLI login
        out = subprocess.run(["gh", "auth", "token"], capture_output=True,
                             text=True, timeout=10)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


class GitHub:
    def __init__(self, token=None):
        self.s = requests.Session()
        self.s.headers["Accept"] = "application/vnd.github+json"
        self.s.headers["User-Agent"] = "aidigest"
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"
        self._last_search = 0.0

    def _get(self, url, params=None, accept=None, tries=4):
        headers = {"Accept": accept} if accept else {}
        for attempt in range(tries):
            r = self.s.get(url, params=params, headers=headers, timeout=30)
            if r.status_code in (403, 429) and (
                    r.headers.get("X-RateLimit-Remaining") == "0"
                    or "rate limit" in r.text.lower()):
                reset = int(r.headers.get("X-RateLimit-Reset", "0"))
                wait = min(max(reset - time.time(), 5), 120)
                print(f"  rate limited; sleeping {wait:.0f}s")
                time.sleep(wait)
                continue
            if r.status_code >= 500 and attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            return r
        return r

    def search_repos(self, q, per_page=40):
        # Search API allows 30 requests/minute when authenticated.
        gap = time.time() - self._last_search
        if gap < 2.2:
            time.sleep(2.2 - gap)
        self._last_search = time.time()
        r = self._get(f"{API}/search/repositories",
                      {"q": q, "sort": "stars", "order": "desc",
                       "per_page": per_page})
        if r.status_code != 200:
            print(f"  search failed ({r.status_code}): {q}")
            return []
        return r.json().get("items", [])

    def repo(self, full_name):
        r = self._get(f"{API}/repos/{full_name}")
        return r.json() if r.status_code == 200 else None

    def readme(self, full_name):
        r = self._get(f"{API}/repos/{full_name}/readme",
                      accept="application/vnd.github.raw")
        return r.text if r.status_code == 200 else ""


GITHUB_URL = re.compile(r"github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)")
NOT_OWNERS = {"orgs", "sponsors", "features", "topics", "marketplace",
              "settings", "login", "about", "pricing", "collections",
              "apps", "site", "trending", "explore", "enterprise"}


def repo_from_url(url):
    """'https://github.com/a/b/tree/main' -> 'a/b', or None."""
    m = GITHUB_URL.search(url or "")
    if not m or m.group(1).lower() in NOT_OWNERS:
        return None
    name = m.group(2)
    if name.endswith(".git"):
        name = name[:-4]
    return f"{m.group(1)}/{name}" if name else None
