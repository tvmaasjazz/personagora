# Review

How a review behaves in this repo, whether it's `/code-review`, `be-reviewer` or
`react-reviewer`. The conventions a change is held to live in `.claude/rules/`.

## What failure looks like here

- **A write without its guard.** A status change applied from a status it shouldn't
  leave, a charge or grant that can be written twice, writes that belong in one
  transaction split across two, or a read-then-write without the lock it needs.
- **A read that sees too much.** A soft-deleted row, or a row the user can't see.
- **A responsibility in the wrong home.** A service doing a second job, or a lib
  reaching into another's tables.
- **A screen that breaks or lies.** A stale cache after a mutation, a missing loading,
  empty or error state, or a hidden control with no path for the API refusing it.

## Risk

The PR description gives a tier. **Low:** plans, docs, tests only, copy, styling.
**Medium:** everything else, unless it's High. **High**, always, when it touches
`backend/migrations/sql/`; `libs/auth/`, `google_auth/`, `users/`, `permissions/`,
`invites/` or `credits/`; the run lease, pickup, handoff or status code in
`libs/generate_text/services/`; session cookies, CORS or client-IP trust;
`frontend/src/features/auth/`, `app/router.tsx` or `lib/api-client.ts`;
`.github/workflows/`, `.railway/`, a Dockerfile, or `config.toml` defaults. Raise any
other change to High when a missed bug would be expensive, with one line saying why.

## Findings

- Each gives `file:line` and the code read to confirm it, not a guess from a name. One
  that couldn't be confirmed is asked as a question.
- A problem the change didn't introduce is marked pre-existing and never blocks.
- A bug with several instances is one finding listing every instance.
- Five nits at most. The summary starts with the number of findings, and says plainly
  when there's nothing to fix.

## Rounds

At most three review-and-fix rounds; after the third, reconsider the approach instead.
After the first, review only the new diff, and never repeat a finding already fixed or
answered. Skip generated and vendored files: `frontend/src/lib/api-schema.gen.ts`,
`frontend/src/components/ui/`, `uv.lock` and `package-lock.json`.
