# Cool AI Projects

A weekly digest of open-source, non-business AI projects on GitHub,
in five areas: local LLMs, creative & animation tools, science,
robotics and games.

## How it works

1. **Find** - GitHub search queries per area (new repos and active
   established ones), plus GitHub links posted to Hacker News.
2. **Filter** - must have a license, recent pushes, and no business
   keywords (marketing, SEO, CRM, ...).
3. **Pre-rank** - by stars per week (measured from stored history,
   or estimated for young repos) and HN points.
4. **Classify** - a cheap LLM reads each top README and decides:
   is it AI, is it business-oriented, which area, interest 1-5.
   Verdicts are cached for 60 days.
5. **Write** - a better LLM writes a two-sentence blurb for each
   pick; a preview image is taken from the README.
6. **Publish** - a static page in `site/issues/`, an archive index,
   and GitHub Pages.

Repos are never featured twice.  State lives in `data/digest.db`
(SQLite), committed back by the workflow.

## Running locally

    pip install -r requirements.txt
    export OPENROUTER_API_KEY=...       # GitHub token comes from `gh`
    python -m aidigest --dry-run        # build without marking picks
    python -m aidigest --no-llm         # heuristics only, free
    python -m aidigest --force          # rebuild even if this week has an issue

Output goes to `site/`.  Everything tunable (queries, thresholds,
models, picks per area) is in `config.yaml`.

## Scheduled runs

`.github/workflows/weekly.yml` runs Mondays at 14:00 UTC (or on
demand from the Actions tab).  It needs one repo secret,
`OPENROUTER_API_KEY` - use a dedicated key with a spending limit.
A run costs roughly $0.15.
