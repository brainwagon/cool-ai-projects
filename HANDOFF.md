# Handoff — Cool AI Projects digest

Last updated: 2026-11-16

## What this is

A weekly digest of open-source, non-business AI projects on GitHub, published as
a static site on GitHub Pages at <https://mvandewettering.com/cool-ai-projects/>.
The pipeline (search → filter → pre-rank → LLM classify → write → publish) is
described in `README.md`; everything tunable is in `config.yaml`. State lives in
`data/digest.db` (SQLite: `stars`, `verdicts`, `featured`).

Scheduling: `.github/workflows/weekly.yml`, cron `0 14 * * 1` = Mondays 14:00
UTC (6–7am Pacific). One run costs roughly $0.15 of OpenRouter credit.

## State as of this writing

| | |
|---|---|
| Latest issue | `2026-11-16`, 20 picks, live (HTTP 200 verified) |
| Published by | workflow run [`43911501354`](https://github.com/brainwagon/cool-ai-projects/actions/runs/43911501354), manual dispatch |
| Data commit | `d206844 Issue 2026-11-16` (db + site, pushed by the workflow itself) |
| Code commit | `cf2adb7 Skip only same-week issues, not last week's` |
| Cost of that run | $0.1433 |

The repo was created 2026-11-10, so the 2026-11-16 14:00 UTC slot was the first
scheduled slot it ever had — and it did not fire. There is no evidence yet that
`schedule` triggers work on this repo at all; see the next section.

## What went wrong on Monday 2026-11-16

Two independent failures, both of which had to be cleared for an issue to appear.

**1. GitHub never fired the cron.** `gh run list` shows only three runs ever:
two `workflow_dispatch` on 2026-11-10 and the recovery dispatch on 2026-11-16.
Zero `schedule` events, none queued (`gh api repos/{owner}/{repo}/actions/runs`
→ `total_count: 2` before the dispatch). The workflow itself was and is
healthy: `state: active`, schedule present on `main`, `allowed_actions: all`.
There is no failure record to inspect — a dropped scheduled run is invisible.
Nothing in the repo caused this, so nothing in the repo fixed it.

**2. Even a fired run would have published nothing.** Commit `b45abf3` added a
guard that skipped the build when the most recent issue was 0–6 days old
(`render.recent_issue(site, today, days=6)`). The previous issue is
`2026-11-10`, which was *exactly 6 days* old on 2026-11-16, so the run would
have printed `Issue 2026-11-10 already covers this week; skipping`, exited 0,
and gone green with no new page. A weekly Monday cron always sees the previous
issue at 6 or 7 days old, so that window could never let the schedule through.
The Nov 10 issue was itself built a day late by hand, which is how the previous
issue ended up 6 instead of 7 days old — but the same trap arms whenever a
scheduled run lands late or is caught up manually.

## The guard, as it now behaves

`render.recent_issue(site, today, max_age_days=2)` (note: the parameter was
`days` before `cf2adb7`) returns the date of an issue that already covers this
week, or `None` to build. It reads `site/issues.json`, not the database.

| Situation | Result |
|---|---|
| Same ISO week already has an issue | skip |
| Latest issue 0–2 days old | skip |
| Latest issue 3–infinite days old, different ISO week | **build** |
| Latest issue dated in the future | ignore it, build |

Checked against the real manifest with `date(2026,11,16)` and neighbours:
2026-11-16 → builds; 11-10 rerun → skips; 11-11 → skips; 11-13 → skips;
11-23 → builds.

`--force` bypasses the guard entirely. It is not exposed as a workflow input, so
a forced rebuild today requires a local run or a temporary edit.

## Checking whether next Monday fired

```bash
gh run list --limit 10 --json event,createdAt,conclusion \
  --jq '.[] | [.event,.createdAt,.conclusion] | @tsv'
```

Expect a `schedule` row after Mon 2026-11-23 14:00 UTC. If the day passes with
no `schedule` row, the scheduler is unreliable for this workflow and one of
these is needed (none applied yet):

- a second cron entry, e.g. `0 15 * * 1`, so one dropped slot isn't fatal;
- move the trigger out of GitHub, e.g. a small job elsewhere that calls
  `gh workflow run weekly.yml`;
- accept manual dispatch as the weekly driver.

## Gotchas

- **A skipped run exits 0.** A week with no issue still shows a green run; the
  only evidence is a missing page. Making the skip print a `::warning` or a
  non-zero exit would make it visible — not done.
- **The cron is UTC and only runs on the default branch.** A push is not needed
  for it to fire, but the schedule must exist on `main` at evaluation time.
- **The workflow commits `data` and `site` itself** with message
  `Issue $(date -u +%F)`, then pushes and deploys via `actions/deploy-pages`.
  Source changes must be committed by hand; concurrency group is `digest`.
- **The guard reads the manifest, the duplicate gate reads the DB.** `featured`
  in `data/digest.db` is what stops a repo being picked twice; deleting a page
  without restoring the DB does not un-feature its repos.
- **Repos are never featured twice**, so rebuilding the same week reuses
  verdicts (cached 60 days) and changes the picks.

## Hands-on commands

`README.md` has the local-run incantations (`--dry-run`, `--no-llm`, `--force`).
The free check of the guard, no network and no LLM spend:

```bash
python -c "from datetime import date; from aidigest import render; \
print(render.recent_issue('site', date.today()))"
```

Recovery dispatch:

```bash
gh workflow run weekly.yml --ref main
gh run watch <id> --exit-status
```

## Suggested skills

None of the installed skills cover this repo's problem area. If the work turns
into a GitHub Actions scheduling investigation, no skill applies — read this
file and `README.md`. Use `opencode` only if the session is about OpenCode
itself, not about this digest.

## Open items

- Confirm the `schedule` trigger actually fires on Mon 2026-11-23 (see above).
- Make a skipped week visible in the Actions list instead of a silent green run.
- Consider exposing `--force` as a `workflow_dispatch` input.
- The `max_age_days=2` clause can still allow two issues three days apart if a
  manual run lands late in a week; accepted deliberately to keep the Monday
  cadence alive.
- 20 picks in `2026-11-16` were costed at $0.14; keep the OpenRouter key on a
  spending limit as `README.md` advises.
