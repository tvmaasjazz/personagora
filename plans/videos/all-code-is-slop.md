# All code is slop (except mine) — notes and ideas

**Video:** [All Code Is Slop (Except Mine)](https://www.youtube.com/watch?v=O_zcc6Xl12g),
Lauren Tan (SpaceX SI), AI Engineer, 18 min, 2026-11-14.

These are ideas, not a build plan. Nothing here changes a rule, a lint config or an
agent until Tyler picks it up.

The video's English captions read as machine-translated and garble product names (the
team's app comes out as "Grokbot", "Graph Bot" and "Growth Bot"). The summary follows the
argument and leaves the garbled names out.

## What the video says

**The claim.** Tan shipped 3,000 PRs in a month, many while asleep, and her team shipped
11,000. Reverted PRs held at about 0.5%, and the app got faster over the same period. The
job of an engineer is now keeping quality steady while output grows. That comes down to
*trust*: not blind trust, but an agent environment built so agents do the right thing by
default. It took her six months to get there.

**Where her time goes**, as an inverted pyramid, most effort first:

1. **The codebase itself**: API design, architecture, refactoring. Deterministic.
2. **Static checks**: linters, type systems, compilers, tests. Deterministic.
3. **Verification**: runtime and formal, to catch bugs, check invariants, and check the
   agent understood the intent.
4. **Descriptive instructions**: rules, skills, `AGENTS.md`. Anything that needs judgement.
   Least effort.

**The codebase is the agent's biggest input.** Agents copy what they see, so a workaround,
an anti-pattern or dead code looks like an established pattern and spreads like weeds.
Keep the garden clean so agents only ever copy good code. When you fix something an agent
did, prefer a deterministic check over a new line in the rules.

**Examples from her team's framework:**

- **Ban what needs subtlety.** `useEffect` is easy to misuse and agents misuse it, so it's
  banned in product code and allowed only inside the framework's own API. The problem
  vanished from code review.
- **Context through directory structure.** Main-process and renderer code live in two
  top-level folders, and imports between them are blocked by a dependency-graph check and
  lint rules. At Cursor, her previous company, agents kept importing main-thread code into
  the renderer.
- **Agents use Markdown to justify shortcuts.** At Cursor, agents patched an architecture
  clash with timers (`setTimeout`, `requestAnimationFrame`) and wrote comments explaining
  why each patch was fine. The timers spread and performance suffered. Her team now bans
  99% of comments: they go stale, nobody reads them, and nothing enforces them. Agents also
  over-apply a small correction as an unbreakable rule.
- **Lint errors that teach.** Each rule's message tells the agent to fix the root cause,
  not patch around it.

Do this often enough and there's less and less to look for in review, until agents can
merge most of their own PRs.

**Review becomes reading verification artifacts**: videos, screenshots, diagrams, proofs.

- **Runtime verification**: the agent runs the app with the same tools a person uses, such
  as the Chrome DevTools protocol. A **feature map**, a sitemap of every feature from the
  user's side, gives agents and people shared names ("the thing in the left panel"). A CLI
  the skills reuse keeps token use down and is testable itself.
- **Formal verification**: TLA+ models of core flows such as notifications across devices,
  and Lean proofs for a virtualization library's no-flicker guarantee. It has already found
  bugs; she calls it one more layer, not a cure-all.
- **Property-based UI testing**, with a library the captions call "Bombadil".
- Most of her tokens, and 70% of one colleague's, now go to verification. None of these
  techniques is new; agents made them cheap enough to use.

**Order matters.** Before building a "software factory", fix the inner loop: lint rules to
stop new anti-patterns, then clean out the old ones, then robust verification. Automating
a loop that produces garbage produces more garbage, at more token cost. With the
foundation in place, her team runs a job on every release that uses the app like a user,
finds bugs, and opens and merges a fix PR for each.

## How it applies here

### 1. The pyramid is upside down here

| Layer | What this repo has |
| ----- | ------------------ |
| Static checks | ruff with 11 rule families and three docstring codes, `ty`, oxlint with 2 rules, oxfmt, `npm run build`. The commit hook runs them all |
| Verification | pytest, a migration stairway test, Vitest, 5 Playwright flows, `scripts/e2e/` walkthroughs |
| Descriptive rules | About 2,570 lines across 8 files in `.claude/rules/`, plus agent briefs and `REVIEW.md` |

`ai-code-review.md` already says a recurring finding becomes "a rule or lint". The talk
argues for **lint first, rule only when a check can't express it**, and for deleting the
rule line once a check enforces it. Rules load on every matching task, so every line moved
into a check is tokens saved on every task, and a finding the reviewer never has to raise.

**Proposal: a standing audit.** One pass over the rules files that tags each rule as
*checkable* (a lint, a type, a test or a script could enforce it) or *judgement*. The
checkable ones become a backlog. This fits `be-docs-auditor` and `fe-docs-auditor`, run as
a full audit with that question added.

### 2. Checks to try first

Each enforces a rule that already exists. None needs a new dependency.

| Check | Enforces | How |
| ----- | -------- | --- |
| No raw palette colors, arbitrary colors or `dark:` outside `components/ui/` | `react-styling.md` › Tokens only, which calls a bypass "a bug" | A small script, or a Vitest test, that greps `src/` for `-(zinc\|slate\|violet\|…)-\d`, `-\[#` and `dark:`, run by `npm run lint`. oxlint can't read Tailwind class strings |
| No raw clock reads outside `DateTimeUtils` | `database.md` › "A duration uses `DateTimeUtils`' monotonic clock" | ruff's `TID251` banned-api on `time.perf_counter`, `time.monotonic` and `time.time`, with a per-file ignore for `date_time_utils.py`. Today's code already complies, so this only guards the future |
| A lib doesn't import another lib's Orm classes or services except through allowed paths | `REVIEW.md` › "A responsibility in the wrong home … a lib reaching into another's tables" | A pytest that walks `libs/` with `ast` and checks each import against an allowed list. Which imports are allowed needs `fastapi-structure.md` › Services turned into data first |
| Error messages that teach | All of the above | Each check's failure names the rule's file and section, and the fix ("use `bg-card`; see `react-styling.md` › Tokens only"), so an agent fixes the cause |

`useEffect` is the talk's headline example. `react-structure.md` already limits it ("No
`useEffect` for fetching data or for deriving one value from another"), but a blanket ban
doesn't fit while some uses are allowed. A `no-restricted-imports`-style rule that warns,
with the allowed uses moved into a few hooks in `lib/`, would get there. That's a bigger
refactor; it only becomes worth doing if review keeps finding misused effects.

### 3. Comments: a deliberate difference

Her team bans almost all comments. This repo goes the other way on purpose:
`python-naming.md` wants a step comment above each block of a multi-step function, and a
comment beside a line for "a reason, a constraint or a trap", because Tyler reads the code
to learn it.

The talk's specific warning still applies: **a comment that justifies a workaround** is how
a bad pattern spreads. **Proposal:** one line in `REVIEW.md` › What failure looks like:
"A workaround explained by a comment instead of fixed: the comment is the finding." That
keeps explanatory comments and targets the failure she describes.

### 4. Verification as what Tyler reviews

| Idea | Where | Why |
| ---- | ----- | --- |
| Screenshots in frontend PRs | `.github/pull_request_template.md` › Testing; `react-coder` | Playwright can save a screenshot of each changed page at phone and desktop widths. Tyler reviews the picture, and `react-reviewer`'s "layout at every breakpoint" check gets something to look at |
| A feature map | `frontend/e2e/` or `frontend/README.md` | One list of pages and what each lets a user do, using the names the e2e flows use. Tyler can then say "the run page's review actions" and the agent knows where that is |
| Property-based tests for invariants | Backend tests, if Hypothesis is approved | Good targets: the Markdown format validator (`BLOG_POST_BODY_FORMAT_RULES`), paging cursors, and the credits ledger (a balance never goes negative, a step is never charged twice). Hypothesis is a new dependency, so ask first |
| A model of the run lease | The generation worker (`plan.md` › Phase 2 › 5) | The lease, pickup and handoff code is High risk in `REVIEW.md`, and it's a small state machine: "no two workers own a run", "a paused run always resumes". Hypothesis's stateful testing is a cheaper first step than TLA+. Later, and only if that worker gets complicated |
| A user-like sweep after each staging deploy | `plan.md` › Phase 2 › 6 Testing deployed environments | Her team fuzzes each release and files a fix PR per bug. A scheduled agent that walks staging's main flows and reports what broke is the small version. Fixing it automatically is a later step |

### 5. Sequencing

Her ordering suggests one change to how features are planned: when a plan adds a
convention, the plan says whether it ships as a check or as a rule line, and a rule line
needs a reason no check can express it. That's a proposed line for CLAUDE.md › Keeping the
rules current.

## To decide

- Whether to run the checkable-versus-judgement audit of `.claude/rules/`
- Which of the three checks in section 2 to build first; the color check is the cheapest
- Whether to add the "workaround justified by a comment" line to `REVIEW.md`
- Whether frontend PRs carry Playwright screenshots, and whether to write a feature map
- Whether to add Hypothesis, and for which invariants first
- Whether "check before rule" becomes a line in CLAUDE.md › Keeping the rules current
