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

### `rca-demo-documents` — Document set for an RCA bot demo
- **Status:** 🚧 In progress · **Owner:** Claude (for Willem) · **Branch:** `rca-demo-documents` · **PR:** [#1](https://github.com/itotinsider/cromley-hydraulics-uns/pull/1)
- **Goal:** a document library for a root cause analysis (RCA) bot used by Copper Canyon Dam's own maintenance and reliability team: supplier O&M manual, schematics and service bulletin (CH); asset register, FMECA, PM plan, work orders, oil analysis, MOC register, shift log, procedures and three previous RCA reports (DRWPA). Clues planted for scenarios A, G and C; answer key kept outside the library.
- **Touches:** new folder `rca-demo/` only (no code, topics, commands or scenarios change). One line in `CLAUDE.md` (layout).
- **Reserves:** —
- **Depends on:** —
- **Done when:** library and answer key reviewed by Willem; values match the simulators; `rca-demo/README.md` explains rebuild and use.
- **Notes:** 2026-11-03 Claude: next step is historian data (weeks of pre-event trends), see `rca-demo/README.md`.

### `rca-history-and-bot-run` — Recorded history and a first RCA bot test run
- **Status:** 🚧 In progress · **Owner:** Claude (for Willem) · **Branch:** `rca-demo-rebuild` · **PR:** [#2](https://github.com/itotinsider/cromley-hydraulics-uns/pull/2)
- **Goal:** three weeks of recorded plant history ending in scenario A (Unit 1 TGB pad 3), following the library's story, and a script that runs Claude Code as the RCA bot on it in an isolated workspace and grades the report against the answer key.
- **Touches:** `rca-demo/` only (`build/record_history.py`, `build/replay_history.py`, `history/`, `bot/`, `run_rca.sh`, `replay.sh`, README, the 3 Nov shift log entries). No topics, commands or scenarios change; the recorder reuses `tools/offline_sim.py` unchanged.
- **Reserves:** —
- **Depends on:** `rca-demo-documents`
- **Done when:** history recorded and committed (gzipped); a headless bot run produces a DRWPA-template report; the grade is reviewed by Willem.
- **Notes:** 2026-11-03 Willem: scenario A first; 13 Oct – 3 Nov window; history committed gzipped. G and C to follow with the same recorder.
  2026-11-04 Willem: no full failure, the controlled stop stays; the shift found the HH on the CH viewer (shift log 09:03–09:55); replay of the history on the stack for the operator's view.

### `interface-version` — One version number for the interface, tests in CI
- **Status:** 🚧 In progress · **Owner:** Willem (with Claude) · **Branch:** `interface-version` · **PR:** —
- **Goal:** a project that builds on Copper Canyon (pinned to a commit, with its own containers around it) can see from one number whether an update changes anything it reads.
- **Touches:** `common/namespace.py` (`INTERFACE_VERSION`, `INTERFACE_DIGEST`), `tools/inventory.py`, `inventory/interface.json` (new), `tests/test_inventory.py`, `.github/workflows/tests.yml` (new), the wiki's Interface reference. No topic, command, scenario or route changes.
- **Reserves:** nothing.
- **Depends on:** —
- **Done when:** changing the inventory without raising the version fails a test that says what to do; the tests run on GitHub for every pull request; the wiki explains how another project builds on Copper Canyon.
- **Notes:** `2026-11-14 Willem: asked for this, for a course lab that reuses the plant unchanged.` Not in the inventory yet: the environment variables (still only on the Configuration page).

### `scada-hp-hmi` — A high-performance (ISA-101) hydro SCADA for DRWPA
- **Status:** 🚧 In progress · **Owner:** Claude (for David and Willem) · **Branch:** `scada-hp-hmi` · **PR:** —
- **Goal:** replace the dark dashboard-style dam SCADA with a light-grey ISA-101 hydro SCADA in the style of HCW's operator console (data blocks, faceplates, alarm banner, display bar, deep links), plus what a hydro control room relies on: unit sequence and permissives, an operating chart (MW vs net head), a single-line, first-out and sequence of events, a persistent historian. Still customer tree only.
- **Touches:** `scada/web/*` (rewritten; the old HMI removed), `scada/main.py` (point names, alarm paths, later historian, SOE, routes), `common/namespace.py` (SCADA point names; step 2 the two sequence tags), `damsim/` (step 2), tests, `inventory/`, wiki (Dam-SCADA and screenshots), the RCA demo's SCADA screenshots (step 4).
- **Reserves:** step 2: `Powerhouse/<unit>/SequenceStep`, `Powerhouse/<unit>/StartPermissives`; step 4: `/api/soe`, `/api/points`.
- **Depends on:** —
- **Done when:** the four steps of the proposal are merged, each green: (1) shell, Plant overview, faceplates, point names; (2) unit displays, sequence and permissives; (3) water, single-line, joint control; (4) historian, SOE, docs and screenshots.
- **Notes:** `2026-11-19 David: decided: light-grey theme as HCW; ISA-5.1 point names with a unit prefix (U1-TI-304, CC-LI-101); publish SequenceStep and StartPermissives; add a persistent (SQLite) historian.` Open: single-line values (proposal: only what the tree has), when to remove `/scada-classic` (proposal: step 4).
  `2026-11-19 David: keep the old overview's physical picture of the dam.` Done in step 1 as the *Dam section* display (`#section`, header button *🎓 Dam view*): the cross-section to scale with teal training notes. The old HMI was then only needed for the unit, water and governor displays.
  `2026-11-19 Claude:` steps 1–4 built on the branch (interface 1.0 → 1.3: topics `SequenceStep` and `StartPermissives`, routes `/api/soe`, `/api/points`, `/api/historian`); `2026-11-19 David: remove scada classic.` Removed: the old HMI and `/scada-classic` are gone (the page was never on main, so no breaking change); the old `#reservoir` and `#governor` addresses map to Water and Powerhouse. Open: the RCA replay (`rca-demo/build/replay_history.py`, item `rca-history-and-bot-run`) doesn't publish the two new unit tags, so the unit display shows them stale during a replay, and the six `rca-scada-*.png` still show the previous HMI. Single-line built with only the tree's values (proposal default).

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
