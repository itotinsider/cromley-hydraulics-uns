# Roadmap and progress

This file is where plans, ideas and progress for CH are tracked. People and AI agents use it to
propose work, discuss it, claim it and report on it. Several of them may work in parallel.

`CLAUDE.md` describes how the system *works*. This file lists what we are going to change, who
is on it, and what has been done.

## How to use this file

### Lifecycle

| Status | Meaning | Who moves it here |
|---|---|---|
| 💡 Idea | Anyone's proposal, open for discussion. Rough is fine. | anyone |
| 📋 Planned | Agreed scope and "done when". Ready to pick up. | Willem or David |
| 🚧 In progress | Claimed: it has an owner and a branch. | the owner |
| ✅ Done | Merged. One-line result plus a PR link; the item moves to [Done](#done). | the owner, in the PR |
| ⏸ Parked / ❌ Dropped | Not now, or not at all. Always give the reason, so it isn't proposed again. | Willem or David |

AI agents may add ideas, but they never move an item to Planned on their own, and they never
take an item that has a different owner.

### Item template

Copy it to the end of the right section. IDs are short slugs (not numbers), so two people
adding items at the same time don't collide.

```markdown
### `slug` — Title
- **Status:** 💡 Idea · **Owner:** — · **Branch:** — · **PR:** —
- **Goal:** what changes for a user of the demo, in one or two sentences.
- **Touches:** the source files and interfaces it changes (topics, commands, scenarios, screens, API).
- **Reserves:** new topic paths and scenario ids it takes (only when In progress).
- **Depends on:** other slugs, if any.
- **Done when:** checkable acceptance criteria.
- **Notes:** discussion and decisions, each dated and named: `2026-10-20 Willem: …`.
```

Topic names in Ideas and Planned may not exist yet. That is why this file is not part of the
"docs only name existing topics" test, unlike README, CLAUDE.md and the wiki.

### Rules for parallel work

1. **Check before you start.** Look at this file on `main` *and* on every other branch, because a
   claim is made on a branch:
   ```bash
   git fetch
   git grep -n -F "In progress ·" $(git branch -a --format='%(refname:short)') -- ROADMAP.md
   ```
2. **Claim with your first commit.** On your new branch, set Status, Owner and Branch, and fill in
   **Touches** and **Reserves**. Push the branch early (after an OK) so remote collaborators see it.
3. **Reserve shared names.** Topic paths and scenario ids are where parallel work collides.
   `common/namespace.py` is the single source of truth for both trees; reserve the paths you add.
4. **Watch the shared sources of truth.** `common/namespace.py`, `common/turbine.py`,
   `damsim/model.py`, `chplc/model.py`, `scada/web/scada.html` and `inventory/` change in almost
   every step. Two in-progress items that touch the same file should be sequenced, or agreed in
   their Notes.
5. **Edit only your own item.** Append new items at the end of their section. If this file
   conflicts in a merge, keep both sides.
6. **Decisions go into the item while it runs.** When it is merged, lasting knowledge (how
   something works, why it was built this way, gotchas) moves to `CLAUDE.md`. This file keeps only
   a short summary.
7. **Every item ends green.** Before the PR: `docker compose run --rm tests`, plus a regenerated
   `inventory/` if an interface changed. For new behaviour or graphics, also check the offline
   sim, MQTT Explorer and a headless screenshot. One branch and one PR per item.

### Several agents on one machine

1. **One agent, one worktree, one branch.** Never let two agents work in the same checkout.
   ```bash
   git fetch && git worktree add ../ch-<slug> -b <branch> origin/main
   # when merged:  git worktree remove ../ch-<slug>
   ```
2. **One stack per worktree.** A git-ignored `.env` in the worktree sets `CH_STACK` and the six
   `CH_*_PORT` host ports (see `docker-compose.yml`), so stacks don't fight over containers and
   ports. Without it the stack is `ch` on 8120…
3. **Never** `git checkout`/`switch`, `stash`, `reset` or `add -A` in a checkout another agent is
   using.

## In progress

(nothing yet)

## Planned

(nothing yet)

## Ideas

### `vendor-onboarding` — Edge vendor onboarding pack
- **Status:** 💡 Idea · **Owner:** — · **Branch:** — · **PR:** —
- **Goal:** a one-page checklist and a scripted run of scenarios A–H with timings, so each vendor
  demo uses the same sequence and the results are comparable.
- **Touches:** wiki (Edge-vendor-brief), maybe an instructor "playlist".

### `second-site` — A second customer site with a Kaplan unit
- **Status:** 💡 Idea · **Owner:** — · **Branch:** — · **PR:** —
- **Goal:** CH-Kaplan "Riverline" at a run-of-river site under the same broker or a second one, so
  the CH tree really is a fleet (several customers and sites) and data scoping becomes concrete.
- **Touches:** `common/namespace.py` (ASSETS, a second customer prefix), a Kaplan model (blade/gate
  cam, hub oil), viewer.

### `link-outage` — Simulated bad site connection
- **Status:** 💡 Idea · **Owner:** — · **Branch:** — · **PR:** —
- **Goal:** an instructor switch that drops or throttles a second "uplink" broker bridge, so
  vendors can show store-and-forward and backfill with original timestamps.
- **Touches:** mosquitto bridge config, instructor.

### `faster-behaviour-tests` — Shorter behaviour test run
- **Status:** 💡 Idea · **Owner:** — · **Branch:** — · **PR:** —
- **Goal:** the behaviour tests take ~2.5 min (40 tests, hours of simulated time). Share warm
  simulations between signatures or shorten compressed durations, target < 60 s.

## Parked / dropped

(nothing yet)

## Done

### `initial-build` — The first CH environment, from the design basis
- **Status:** ✅ Done · **Owner:** Claude (for Willem/David) · **Branch:** — · **PR:** —
- **Result:** dam simulator, three CH PLC simulators, dam SCADA, instructor station (scenarios
  A–H plus 11 further failure modes), CH asset viewer, Node-RED (3 tabs), MQTT Explorer, hub,
  wiki, tested inventory, four test layers. See `CLAUDE.md` for how it works.
