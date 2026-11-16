---
description: Explain a slice of the codebase as it is today — a path, a feature, or a question
argument-hint: <path, feature or question>
---

Explain this, for Tyler: $ARGUMENTS

Read the code as it is now; don't explain from memory, plans or old PRs. Start from the
`README.md` of each lib involved when there is one, then read the files the question
touches in full, and follow calls into other libs as far as the answer needs.

Write the explainer as markdown in the scratchpad, not in the repo, and give Tyler its
full path. Build an artifact instead when a diagram of a flow or states would explain
it better than text. In order:

1. **What it's for**, in two or three sentences.
2. **How it works**: the flow in the order it runs, as numbered steps, each naming the
   function or service with `file:line`.
3. **Concepts**: each library, language or database construct the code relies on that
   isn't obvious from reading it (an `asyncio` primitive, a locking read, an upsert,
   `Decimal`), in one or two plain sentences on what it does here.
4. **Where it connects**: the other libs, tables, queues and settings it touches.

Keep it as short as the question allows. Don't propose changes unless asked. If the
answer shows a lib's README is wrong, say so at the end.
