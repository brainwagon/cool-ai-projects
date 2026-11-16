"""Write issue pages and the archive index as static HTML."""

import json
import os
import shutil
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = os.path.dirname(__file__)
env = Environment(loader=FileSystemLoader(os.path.join(HERE, "templates")),
                  autoescape=select_autoescape(["html"]))


def recent_issue(site, today, max_age_days=2):
    """Date of an issue that already covers this week, or None.

    An issue blocks a new one when it falls in the same ISO week as
    `today` (a second run inside one week), or when it is at most
    `max_age_days` old (a manual catch-up run the day before the
    scheduled one).  A weekly cron on a Monday sees the previous issue
    at 6 or 7 days old, which must not block this week's issue.
    """
    path = os.path.join(site, "issues.json")
    if not os.path.exists(path):
        return None
    this_week = today.isocalendar()[:2]
    with open(path) as f:
        for issue in json.load(f):
            published = date.fromisoformat(issue["date"])
            age = (today - published).days
            if age < 0:
                continue
            if age <= max_age_days or published.isocalendar()[:2] == this_week:
                return issue["date"]
    return None


def write_issue(site, cfg, issue_date, sections, stats):
    os.makedirs(os.path.join(site, "issues"), exist_ok=True)
    shutil.copy(os.path.join(HERE, "templates", "style.css"),
                os.path.join(site, "style.css"))
    name = issue_date.isoformat()
    html = env.get_template("issue.html").render(
        cfg=cfg, date=issue_date, sections=sections, stats=stats)
    with open(os.path.join(site, "issues", f"{name}.html"), "w") as f:
        f.write(html)

    # Small manifest keeps the archive index cheap to rebuild.
    manifest_path = os.path.join(site, "issues.json")
    issues = []
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            issues = json.load(f)
    issues = [i for i in issues if i["date"] != name]
    issues.append({"date": name,
                   "count": sum(len(s["repos"]) for s in sections),
                   "highlights": [r["full_name"] for s in sections
                                  for r in s["repos"][:1]]})
    issues.sort(key=lambda i: i["date"], reverse=True)
    with open(manifest_path, "w") as f:
        json.dump(issues, f, indent=1)
    with open(os.path.join(site, "index.html"), "w") as f:
        f.write(env.get_template("index.html").render(cfg=cfg, issues=issues))
    return os.path.join(site, "issues", f"{name}.html")
