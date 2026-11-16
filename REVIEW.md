# Review

How a review behaves in this repo, whether it's `/code-review`, `be-reviewer` or
`react-reviewer`. The conventions a change is held to live in `.claude/rules/`.

## What failure looks like here

- **A write without its guard.** A status change applied from a status it shouldn't
  leave, a charge or grant that can be written twice, writes that belong in one
  transaction split across two, or a read-then-write without the lock it needs.
- **A read that sees too much.** A soft-deleted row returned, or a row returned to a
  user who can't see it.
- **A responsibility in the wrong home.** A service doing a second job, or a lib
  reaching into another's tables.
- **A screen that breaks.** A stale cache after a mutation, or a missing loading, empty
  or error state.

## Risk

The PR description gives a tier: Low, Medium or High. A change touching any of these
is always High: `backend/migrations/sql/`, `libs/auth/`, `libs/google_auth/`,
`libs/users/`, `libs/permissions/`, `libs/invites/`, `libs/credits/`, the run lease,
pickup, handoff and status code in `libs/generate_text/services/`, session cookies,
`.github/workflows/`, `.railway/`, the Dockerfiles, and `config.toml` defaults. Raise
any other change to High when a missed bug would be expensive, with one line saying why.

## Findings

- Every finding gives `file:line` and the code read to confirm it, not a guess from a
  name. One that couldn't be confirmed is asked as a question.
- A problem the change didn't introduce is marked pre-existing and never blocks.
- A bug with several instances is one finding that lists every instance.
- Five nits at most.
- The summary starts with the number of findings, and says plainly when there's
  nothing to fix.

## Rounds

At most three review-and-fix rounds. After the third, step back and reconsider the
approach rather than starting a fourth. After the first round, review only the new
diff, and never repeat a finding that was already fixed or answered.

Skip generated and vendored files: `frontend/src/lib/api-schema.gen.ts`,
`frontend/src/components/ui/`, `uv.lock` and `package-lock.json`.
