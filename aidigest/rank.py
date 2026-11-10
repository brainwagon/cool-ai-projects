"""Cheap filtering and scoring before and after the LLM step."""

import math
from datetime import date, datetime


def _date(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date() if s else None


def passes_filters(repo, cfg, today):
    f = cfg["filters"]
    if repo["fork"] or repo["archived"]:
        return False
    if f["require_license"] and repo["license"] in (None, "NOASSERTION"):
        return False
    pushed = _date(repo["pushed_at"])
    if not pushed or (today - pushed).days > f["max_days_since_push"]:
        return False
    text = (repo["description"] + " " + " ".join(repo["topics"])).lower()
    return not any(k in text for k in f["exclude_keywords"])


def weekly_growth(repo, db, today, new_days):
    """Stars per week: measured from history when we have it, otherwise
    estimated from age.  The estimate is only fair for young repos; old
    ones wait until a week of history exists."""
    gain = db.weekly_gain(repo["full_name"], today, repo["stars"])
    if gain is not None:
        return gain, True
    age = (today - _date(repo["created_at"])).days
    if age > new_days:
        return 0.0, False
    return repo["stars"] * 7 / max(age, 7), False


def pre_score(repo):
    hn_points = sum(h["points"] for h in repo["hn"])
    return math.log1p(max(repo["growth"], 0)) + 0.5 * math.log1p(hn_points)


def final_score(repo):
    return pre_score(repo) * (0.4 + repo["verdict"]["interest"] / 5)
