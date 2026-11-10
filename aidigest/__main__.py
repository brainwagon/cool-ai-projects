"""Build one weekly issue.

    python -m aidigest                 # full run, today's date
    python -m aidigest --no-llm        # skip OpenRouter (heuristics only)
    python -m aidigest --dry-run       # don't mark picks as featured
"""

import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import yaml

from . import rank, readme, render, sources
from .db import DB
from .github import GitHub, find_token
from .llm import LLM


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--date", type=date.fromisoformat, default=date.today())
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--site", help="output directory (default from config)")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    today, areas = args.date, cfg["areas"]
    db = DB(cfg["paths"]["db"])
    gh = GitHub(find_token())
    llm = None if args.no_llm else LLM(cfg["llm"])

    print("Searching GitHub...")
    repos = sources.github_candidates(gh, cfg, today)

    if cfg["hacker_news"]["enabled"]:
        print("Checking Hacker News...")
        hn = sources.hn_candidates(cfg, today)
        missing = [n for n in hn if n not in repos]
        print(f"  {len(hn)} linked repos, {len(missing)} new to look up")
        for name in missing[:80]:
            item = gh.repo(name)
            if item:
                repos[item["full_name"]] = sources.slim(item)
                hn.setdefault(item["full_name"], hn.get(name, []))
        for name, links in hn.items():
            if name in repos:
                repos[name]["hn"] = links

    featured = db.featured_names()
    pool = []
    for r in repos.values():
        if not rank.passes_filters(r, cfg, today):
            continue
        r["growth"], r["growth_measured"] = rank.weekly_growth(
            r, db, today, cfg["search"]["new_within_days"])
        db.record_stars(r["full_name"], today, r["stars"])
        if r["full_name"] not in featured:
            pool.append(r)
    db.commit()
    print(f"{len(repos)} candidates, {len(pool)} pass filters")

    # Send the most promising few per area (plus HN finds) to the LLM.
    sel = cfg["selection"]
    pool.sort(key=rank.pre_score, reverse=True)
    chosen = {}
    for key in areas:
        for r in [r for r in pool if r["area_hint"] == key][: sel["llm_candidates_per_area"]]:
            chosen[r["full_name"]] = r
    for r in [r for r in pool if r["hn"]][: sel["llm_candidates_hn"]]:
        chosen[r["full_name"]] = r
    chosen = list(chosen.values())
    print(f"Reading {len(chosen)} READMEs...")

    def fetch(r):
        r["readme"] = gh.readme(r["full_name"])
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(fetch, chosen))

    for r in chosen:  # sqlite stays on the main thread
        r["verdict"] = db.verdict(r["full_name"], today,
                                  cfg["llm"]["reclassify_after_days"])

    def judge(r):
        v = r["verdict"]
        if v is None and llm:
            v = llm.classify(r, readme.excerpt(r["readme"]), areas)
            r["fresh_verdict"] = v is not None
        if v is None and not llm:
            v = {"ai": True, "business": False, "interest": 3,
                 "area": r["area_hint"] or "none", "reason": "no-llm mode"}
        r["verdict"] = v
    with ThreadPoolExecutor(cfg["llm"]["workers"]) as ex:
        list(ex.map(judge, chosen))
    for r in chosen:
        if r.get("fresh_verdict"):
            db.save_verdict(r["full_name"], today, r["verdict"])
    db.commit()

    keep = [r for r in chosen if r["verdict"] and r["verdict"]["ai"]
            and not r["verdict"]["business"] and r["verdict"]["area"] in areas
            and r["verdict"]["interest"] >= sel["min_interest"]]
    print(f"{len(keep)} look interesting")

    sections = []
    for key, area in areas.items():
        picks = sorted((r for r in keep if r["verdict"]["area"] == key),
                       key=rank.final_score, reverse=True)[: sel["picks_per_area"]]
        sections.append({"key": key, "name": area["name"], "repos": picks})
    picks = [r for s in sections for r in s["repos"]]

    print(f"Writing {len(picks)} blurbs...")
    def finish(r):
        r["image"] = readme.preview_image(r["readme"], r["full_name"],
                                          r["default_branch"])
        r["blurb"] = llm.blurb(r, readme.excerpt(r["readme"])) if llm else None
    with ThreadPoolExecutor(cfg["llm"]["workers"]) as ex:
        list(ex.map(finish, picks))

    stats = {"candidates": len(repos), "classified": len(chosen),
             "cost": llm.cost if llm else 0}
    path = render.write_issue(args.site or cfg["paths"]["site"], cfg, today,
                              sections, stats)
    if not args.dry_run:
        for s in sections:
            for r in s["repos"]:
                db.mark_featured(r["full_name"], today.isoformat(), s["key"])
    db.commit()
    print(f"Wrote {os.path.abspath(path)}")
    if llm:
        print(f"LLM cost: ${llm.cost:.4f}")


if __name__ == "__main__":
    main()
