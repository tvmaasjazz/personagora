# AI code review — plan

How Personagora reviews code that Claude writes. The goal comes from the Claude Code
team's write-up on review at agent volume: spend as little of Tyler's time per change
as possible without more bugs reaching `main`. Machines do the reading they're good at,
and Tyler reads where judgement or risk calls for it.

This plan covers both sides of the stack. It starts with what the article recommends
and what fits a one-person repo, then what Tyler's backend review comments show, then
the options at each layer, a recommended rollout, and the decisions left open.

## From the article: what fits here

| Practice                                                       | Fits?     | Why                                                                                                        |
| -------------------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------- |
| Verify before the PR: run the checks and show their output     | Yes       | Partly done. CLAUDE.md lists the checks, and e2e scripts exist                                             |
| Fresh-context review of the diff before a person looks         | Yes       | `react-reviewer` does this for the frontend. The backend has no reviewer                                   |
| Find bugs in parallel, then verify each finding before posting | Yes       | Built-in `/code-review` already works this way                                                             |
| Fix at the source: a recurring finding becomes a rule or lint  | Yes       | Tyler already does this by hand. Most comments ended with "the rule is in …"                               |
| A short `REVIEW.md` saying what failure looks like here        | Yes       | None exists yet                                                                                            |
| Separate security review                                       | Yes       | Auth, sessions, invites, credits and the Cloudflare IP trust are all security-sensitive                    |
| Human attention scaled by risk                                 | Yes, bent | There's one human, so a tier sets how closely Tyler reads, not how many people approve                     |
| Converging review: round cap, re-review only the new diff      | Yes       | Agent reviewing agent loops without a cap                                                                  |
| Past incidents become the reviewer's eval                      | Later     | Few incidents so far; seed it from the correctness comments and the `fix(...)` PRs                         |
| Explainers in place of reading every diff to learn the code    | Yes       | A fifth of Tyler's comments are "explain this to me"                                                       |
| Merge queue, trusted-author lists, two approvers, on-call      | No        | Built for teams. Not worth it solo                                                                         |
| Flags, staged rollout, fast rollback                           | Partly    | Staging deploys from `main` first. `launchdarkly-agentcontrol.md` plans flags for models and prompts       |

## What the backend review history shows

Every PR comment in the repo's history is an inline comment from Tyler's account:
229 in all. On backend code and backend docs, 183 are Tyler's own and 41 are Claude's
replies posted from that account. Each of Tyler's was given one category by hand:

| Share | Count | Category                                     | Examples                                                                                                    |
| ----: | ----: | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
|   19% |    34 | Explain-to-me questions                      | `create_task`, `gather`, `with_for_update`, `on_conflict_do_update`, `Decimal` for money, Alembic `env.py`  |
|   18% |    33 | Placement and service boundaries             | Split `LlmCallService` from `LlmService`; `google_auth` as its own lib; lease and claim logic in their own service |
|   17% |    32 | Naming                                       | `_record` for rows; `Admin`/`Persona` prefixes; singular table and domain names; `validate_` not `ensure_`  |
|    8% |    14 | Correctness: data, concurrency, transactions | Charge once per step; lock the balance; role not saved on invite; `null` not `0` before a value exists      |
|    7% |    13 | Simplicity and redundant code                | "overkill?"; a redundant id field; dead code; mutating a record inside a helper                             |
|    6% |    11 | Types, data shapes, schema                   | Untyped `resume_payload`; keep Result classes plain; inline constraints; one revision per feature            |
|    5% |     9 | Shared utils and reuse                       | `DateTimeUtils` (asked for three times, PRs 12, 28, 42); a shared paging query builder                       |
|    5% |     9 | Add or clarify a comment or docstring        | "Doesn't describe the function"; "explain it to a 5 year old"                                               |
|    4% |     8 | Remove a comment                             | "remove comment", eight times across PRs 6–37                                                               |
|    3% |     6 | Scope and product calls                      | Google only for now; delete stale plans; should the invite check be its own endpoint                        |
|    3% |     6 | Rules or agent docs too long                 | "Too much text dedicated to what not to do"; "is this file bloated?"                                        |
|    3% |     5 | Config, constants, hard-coding               | Hard-coded Cloudflare ranges; settings location                                                             |
|    2% |     3 | Ordering within a file                       | GET routes before PUT; each dependency next to its alias                                                    |

### Patterns

1. **Conventions take up a third of the comments, and nearly all are now rules.** Naming,
   placement, utils, comments, ordering and config were raised, settled in a reply,
   and written into `fastapi-structure.md`, `python-naming.md` or `database.md`. Tyler
   shouldn't have to spot them again; a reviewer that reads the rules can.
2. **The repeats are the clearest thing to automate.** These came back after a rule or
   an earlier comment covered them: "remove comment" eight times, `DateTimeUtils` three
   times, domain-prefixed names three times, singular names twice. Comments came back
   after the rule existed because nothing checked the code against the rules before
   Tyler read it.
3. **The expensive comments were about structure, and they came after the code was
   written.** The longest threads (PR 15's graph builder registry, PR 28's leases and
   claims, PR 37's credits) each restructured finished code. Placement is now reviewed
   before coding (CLAUDE.md › Running agents in parallel), and placement comments mostly
   stop after PR 41. Keep that gate, and hold every new responsibility to it.
4. **Correctness is only 8%, but those comments matter most.** They caught a real bug
   (an invite's role not saved), a missing idempotency guarantee, missing row locks, a
   transaction boundary, soft-delete filtering and lease edge cases. Bug-hunting review
   targets exactly this, and it shouldn't depend on Tyler happening to spot it.
5. **A fifth of review is learning.** The questions are about Python async, SQLAlchemy,
   Postgres and LangGraph. Tyler is using review for the article's second job: building
   his understanding of the code. That's worth keeping, but it works better as an
   explainer Tyler can ask for at any time (section 6) than as questions asked while
   reviewing.
6. **Tyler weighs the token cost of the docs.** Six comments asked for shorter rules and
   agents. Anything this plan adds (`REVIEW.md`, a reviewer agent) points to the rules
   rather than restating them.
7. **Comment density has fallen as the rules grew.** Comments per 1,000 added backend
   lines: 4.1 on PRs 2–20, 2.7 on PRs 21–40, 1.1 on PRs 41–73. The comments alone can't
   tell whether the code got better or the reviewing got lighter, which is why the
   metrics below include a guardrail.

## Options, layer by layer

### 1. Before the PR

Three tools run once the PR is open, before Tyler is asked to review it. Each owns the
categories it's built for, so none of them repeats another's job:

| Tool             | Built for                                                                                                                                                                                                                       | Owns, from the categories above                                                                    |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `/code-review`   | Finding behaviour bugs. Agents hunt in parallel, verifiers vote on each finding, and style and cleanup findings are dropped                                                                                                    | Correctness: races, missing locks, lost writes, wrong transaction boundaries, edge cases           |
| `/simplify`      | Reuse, simplification and efficiency. It applies its fixes                                                                                                                                                                     | Simplicity and redundant code; part of shared utils                                                |
| Each side's reviewer: `react-reviewer` for the frontend, a new `be-reviewer` for the backend | Holding the change to this repo's rules and design. It reads the rules in full, has fresh context and never edits | Scope, placement, naming, types and data shapes, utils, comments and docstrings, config, ordering, rule gaps |

**`be-reviewer` doesn't hunt for bugs.** `/code-review`'s verifiers would filter
convention findings out as style, which is why a separate reviewer is needed. The other
way round, `be-reviewer` adds nothing by looking for bugs, because the bug hunter does
it better. One kind of correctness check stays with `be-reviewer`: what a rule writes
down. `database.md`'s database clock, soft delete, status-guarded writes and
nullability are conventions it checks line by line. `/code-review` finds the bugs no
rule anticipated. A little overlap between the two is fine.

`be-reviewer` mirrors `react-reviewer`. It gets the base and head refs plus the brief,
never an opinion of the code. Its checks, in order: scope; placement
(`fastapi-structure.md` › Services); the rules on writes and queries (`database.md`,
`fastapi-structure.md` › Querying and writing); types and data shapes; naming
(`python-naming.md`); comments and docstrings; config; ordering. Its report uses the
same sections as `react-reviewer`'s, including **Rule gaps**, plus **Risk**: the tier
it would give the change, and any reason to raise it (section 3).

Also before the PR opens: **evidence, not a claim that it's done**. The PR shows the
commands that ran, what they returned, and for a flow, the e2e script's output.

### 2. On every PR

- **Review stays local** (decided). The main session runs the tools in section 1 before
  opening the PR. It fixes what they find, or answers a finding in the PR description.
  The GitHub Action and the managed Code Review product are for teams; revisit them only
  if PRs start coming from somewhere other than a local session.
- **Security review** with `/security-review`, on every change `REVIEW.md` › Risk makes
  High.
- **Every finding gets an answer**: fix it, or reply with the reason. Tyler already
  does this.
- **CI gap:** the frontend job runs `fmt:check`, `lint` and `build` but not
  `npm run test`. Add it. The e2e suite needs the API and the seed, so it stays local.

### 3. Tyler's attention, by risk

With one human, the tier sets how closely Tyler reads, not how many approvals a change
needs. The tier goes in the PR description. Who wrote the change never lowers it.

The High paths below are a floor, not the whole list. A change that touches one is
always High. The reviewer or the main session also raises a change to High when it
judges that a missed bug would be expensive. Examples: money or permissions decided
outside the listed libs, a new background task, a change in what a public route
returns, or a pattern other code will copy. A raise always comes with one line saying
why, so Tyler can see the reasoning and the list can grow from it.

| Tier   | What                                                                                                           | Tyler reads                                                                                                  |
| ------ | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Low    | Plans and docs, tests only, copy, frontend styling                                                             | The reviewer's summary, then merges                                                                         |
| Medium | Ordinary features                                                                                              | The placement list (already approved before coding), the reviewers' findings, and spot-reads                |
| High   | The paths `REVIEW.md` › Risk lists, and any change a reviewer raises                                          | Every line, after the reviewers have run                                                                    |

### 4. Making review converge

Put these in `REVIEW.md` and in each reviewer: at most three review-and-fix rounds, then
step back and reconsider the approach; after the first round, review only the new diff;
report a whole class of bug once with every instance listed; never repeat a finding
already answered.

### 5. Closing the loop

Tyler already turns comments into rules by hand. Options for making that systematic:

- **The reviewers' Rule gaps section** (recommended; `react-reviewer` already has one).
  A gap becomes a proposed rule edit, which Tyler approves.
- **Tyler's GitHub comments go through the session.** Tyler tells the session he left a
  review, and it fetches the comments. CLAUDE.md › Keeping the rules current then turns
  each general correction into a proposed rule. No command is needed for this.
- **A lint rule first** where one exists. Docstring presence is already enforced by ruff
  (`D101`–`D103`). What's left (a docstring that doesn't describe its function, a
  comment that narrates code) needs judgement, so it belongs to the reviewer, not to a
  custom check.
- **An eval set**, later. Each case is the commit before a known problem: the
  correctness comments above, and the PRs that fixed something (#40, #47, #68, #72).
  When the reviewer's prompt changes, rerun it and confirm it still catches them. It's
  worth building once there are around ten cases.

### 6. Shared context

**What the article recommends:** explainers are generated when someone needs one, not
kept in the repo. "When someone wants to understand a part of the codebase, they ask
Claude to write an explainer for exactly that slice. It takes minutes and reflects the
code as it is today." Some people on the team also have Claude build a small artifact
that visualizes the slice. The point is that an explainer written on the day is never
stale, while a checked-in one starts going stale with the next commit.

This isn't an argument against committed docs. The article keeps CLAUDE.md and
REVIEW.md committed, and its reviewer flags a change that makes one out of date. What
decides where a piece of knowledge lives is how fast it changes:

- **A feature README for the high-level overview** (committed). It covers each feature
  whose workings aren't obvious from a single file. It's informational and as short as
  it can be, about a screen at most. It says what the feature does, the main flow from
  request to result as numbered steps, the services involved with one line each on what
  they own, and the states with how they move between them. It leaves out the reasons
  for decisions, alternatives that were considered, history, and anything one file's
  code already shows. A README names services and settings, and points to code rather
  than pasting it. It lives in the lib (`backend/libs/<lib>/README.md`). Start with
  `generate_text` (runs, steps, leases, pickup, human review), `credits` and `database`
  (the migration runner). Write one for a later feature when its plan item is built,
  and no sooner. Claude reads the README before changing that lib, so it serves both
  Tyler and Claude.
- **On-demand explainers for the detail** (not committed), as the article recommends.
  These cover what the README leaves out, or something new that comes up: what `gather`
  does here, how `with_for_update` protects a write, how the migration runner calls
  Alembic. Add a `/explain <path or question>` command so explainers have the same shape
  every time. The shape: what the slice is for, the flow through it in order, the
  library and language constructs it relies on, and where it touches other libs. The
  command starts from the lib's README when there is one. It writes a markdown file to
  the scratchpad, or an artifact when a diagram helps.

**Keeping READMEs current.** `be-reviewer` checks each change against the README of
every lib it touches. It flags a flow step, state or service that the change made
untrue, and a new one that should be added. Add lib READMEs to
`be-docs-auditor`'s scope too.

Concepts don't go in the PR description.

### 7. After the merge

Staging deploys from `main` after CI passes, so a broken build shows up there before a
release. Rolling back means redeploying the previous Railway deployment. Flags arrive
with the LaunchDarkly plan. Nothing new is needed here yet.

## Recommended rollout

**Phase 1: cheap, local, this week**

1. `REVIEW.md` at the repo root, kept to a screen. It says what failure looks like here
   (correctness: a write without its guard, lock or transaction; structure: a
   responsibility in the wrong service), lists the high-risk paths, caps nits, lists
   paths to skip (`api-schema.gen.ts`, `components/ui/`, lockfiles), asks for
   `file:line` evidence, sets the convergence rules, and points to `.claude/rules/` for
   everything else.
2. `.claude/agents/be-reviewer.md`, modelled on `react-reviewer.md`: conventions and
   design only, with the Risk section. Also add the Risk section to `react-reviewer.md`.
3. `.github/pull_request_template.md` with Summary, Testing (commands and output), Risk
   tier with the reason for any raise, and How to revert.
4. Changes to CLAUDE.md › Pull requests: the PR still opens as soon as the code is
   written. Before Tyler is asked to review it, run that side's reviewer,
   `/code-review`, `/simplify`, and `/security-review` on high-risk paths. Each finding
   is fixed or answered.
5. Add `npm run test` to the CI frontend job.
6. `.claude/commands/explain.md`.
7. Feature READMEs for `generate_text`, `credits` and `database`; a rule saying what a
   README holds and when a lib gets one; the `be-reviewer` check that flags a stale
   one; and lib READMEs added to `be-docs-auditor`'s scope.

**Later: once there are around ten cases**

8. The eval set, run whenever a reviewer's prompt changes.

## Measuring it

- **Tyler's comments per 1,000 added lines.** Baseline: 1.1 (PRs 41–73). Most of what's
  left should be judgement and questions, not conventions.
- **Repeats.** Tyler's comments that a rule already covered. Target: none.
- **Rounds to pass.** Reviewer rounds before a PR is clean.
- **Guardrail.** `fix(...)` PRs that touch a recently merged feature's files within two
  weeks, and anything found on staging. If these rise, time hasn't been saved, only
  moved.

## Decisions

- **Review stays local.** No GitHub Action or managed review for now.
- **The tools split by what each is built for.** `/code-review` finds bugs, `/simplify`
  cleans up, and `be-reviewer` checks conventions and design (including the
  correctness that rules write down) without hunting for bugs.
- **The High paths are a floor.** The reviewer or the main session can raise any change
  to High, with a one-line reason.
- **Committed feature READMEs give the high-level overview.** On-demand `/explain`
  covers the detail and anything new. `be-reviewer` keeps the READMEs current.
