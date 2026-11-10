"""Where candidate repos come from: GitHub search and Hacker News."""

import time
from datetime import timedelta

import requests

from .github import repo_from_url


def slim(item):
    """Keep only the repo fields the rest of the pipeline uses."""
    lic = (item.get("license") or {}).get("spdx_id")
    return {
        "full_name": item["full_name"],
        "html_url": item["html_url"],
        "description": item.get("description") or "",
        "topics": item.get("topics") or [],
        "stars": item.get("stargazers_count", 0),
        "created_at": item.get("created_at", ""),
        "pushed_at": item.get("pushed_at", ""),
        "license": lic,
        "language": item.get("language") or "",
        "default_branch": item.get("default_branch") or "main",
        "fork": item.get("fork", False),
        "archived": item.get("archived", False),
        "area_hint": None,
        "hn": [],
    }


def github_candidates(gh, cfg, today):
    s = cfg["search"]
    new_since = (today - timedelta(days=s["new_within_days"])).isoformat()
    active_since = (today - timedelta(days=s["active_within_days"])).isoformat()
    found = {}
    for key, area in cfg["areas"].items():
        for q in area["queries"]:
            for extra in (f"created:>{new_since} stars:>={s['new_min_stars']}",
                          f"pushed:>{active_since} stars:>={s['active_min_stars']}"):
                items = gh.search_repos(f"{q} {extra} archived:false fork:false",
                                        s["results_per_query"])
                for it in items:
                    repo = found.setdefault(it["full_name"], slim(it))
                    repo["area_hint"] = repo["area_hint"] or key
        print(f"  {area['name']}: {sum(1 for r in found.values() if r['area_hint'] == key)} repos")
    return found


def hn_candidates(cfg, today):
    """GitHub repos linked from Show HN / front-page stories this week."""
    hn = cfg["hacker_news"]
    since = int(time.mktime((today - timedelta(days=hn["lookback_days"])).timetuple()))
    hits = []
    for params in (
        {"tags": "show_hn", "hitsPerPage": 1000,
         "numericFilters": f"created_at_i>{since},points>={hn['min_points']}"},
        {"tags": "story", "query": "github.com", "hitsPerPage": 1000,
         "restrictSearchableAttributes": "url",
         "numericFilters": f"created_at_i>{since},points>={hn['min_points']}"},
    ):
        try:
            r = requests.get("https://hn.algolia.com/api/v1/search_by_date",
                             params=params, timeout=30)
            r.raise_for_status()
            hits.extend(r.json().get("hits", []))
        except requests.RequestException as e:
            print(f"  Hacker News fetch failed: {e}")
    out = {}
    for h in hits:
        name = repo_from_url(h.get("url"))
        if not name:
            continue
        entry = out.setdefault(name, [])
        link = f"https://news.ycombinator.com/item?id={h['objectID']}"
        if all(e["url"] != link for e in entry):
            entry.append({"url": link, "points": h.get("points") or 0,
                          "title": h.get("title") or ""})
    return out
