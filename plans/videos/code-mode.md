# Code Mode in Claude Code — notes and ideas

**Video:** [Code Mode Is Claude Code's BIGGEST Harness Change Yet](https://www.youtube.com/watch?v=DRNbxPk9Ab8),
Ray Amjad, 15 min, 2026-11-16.

These are ideas, not a build plan. Nothing here changes a rule or an agent until Tyler
picks it up.

## What the video says

**The problem.** A harness gives the model separate tools (Read, Edit, Bash, WebFetch,
each MCP server's tools) and loops through them one call at a time. Every call's output
lands in the context window and is reread on every later turn. Chaining tools across
MCP servers, such as Stripe data into a script and then into PostHog, means every
intermediate result sits in context. Cached tokens are cheap, but they still cost money
and attention.

**Code Mode as an idea.** Cloudflare's write-up ("Code Mode: the better way to use
MCP") swaps many tools for two: `search` to find a tool, and `execute` to run code that
calls tools as functions. Results pass from one call to the next inside the code and
never enter the context window. Cloudflare's own MCP server went from 2,600 tools
costing 1.1M tokens to 2 tools costing about 1,000. Gateways like executor.sh do the
same across many MCP servers on the client side.

**Claude Code's version.** It goes further: *every* harness tool sits behind Code Mode,
not only MCP. With it on, Claude has two tools:

- **REPL**: a JavaScript session that stays open for the whole conversation. Bash, Read,
  Edit, WebFetch, MCP calls and subagents become functions in it. A variable set in one
  call is there in the next, so Claude can fetch, filter, dedupe and loop before
  anything comes back into context. The video's point against "just write a bash
  script": bash can't reach MCP servers or spawn subagents, and the REPL can.
- **Poll**: a script that runs too long detaches into the background, and Claude polls it.

**The numbers it cites.** The presenter's own runs on real open-source issues: about
half the input tokens, and 71% of the cost of normal mode. Browser Use and a
TerminalBench run with a Python REPL report similar or larger gains. These are the
presenter's and third parties' figures, not measured here.

**Setup caveat.** In the demo, Code Mode refused to turn on until a mod that used Claude
Code hooks was disabled.

**What's coming, unreleased.** `spawn_context`, `list_contexts` and `release_context`
appeared in the binary: subagents as contexts that code can start, fork from the main
conversation, and combine. Forking lets Claude try five approaches and return only the
best three. With the prompt and the conversation history also held as variables, the
model could cut its own noisy tool results instead of compacting, which is the
recursive language model (RLM) idea from Alex Zhang's paper. The video expects only
the first two of RLM's three pieces soon.

## How it applies here

### 1. Developer workflow in Claude Code

| Idea | Fits? | Why |
| ---- | ----- | --- |
| Try Code Mode for the coordinating session | Yes, after the hook check below | `frontend-plan.md` › Keeping the main session small exists because the main session fills with tool output. Code Mode targets that directly |
| Use it in coder and reviewer agents | Later | Agents' tool lists live in their frontmatter (`.claude/agents/*.md`). How Code Mode treats a `tools:` allowlist is unknown |
| Spawn contexts for parallel agents | Wait | Unreleased. When it lands, compare it with the split in CLAUDE.md › Running agents in parallel |
| An MCP gateway such as executor.sh | No | The project has no `.mcp.json` and no MCP servers. Nothing to gateway |

**The hook check comes first, and it's High risk.** This repo leans on two guards that
assume the Bash tool:

- `.claude/settings.json` runs `.claude/hooks/check-before-commit.sh` as a `PreToolUse`
  hook with `matcher: "Bash"`. It blocks a commit when ruff, ty, oxfmt, oxlint, the
  build or the unit tests fail.
- The same file's `permissions.deny` blocks `git push` to `main` and `--force`, also
  matched on `Bash(...)`.

If Bash becomes a function called inside the REPL, it's unknown whether either guard
still sees the call. A commit could skip the checks, or a push to `main` could get
through. The demo already showed Code Mode and hooks conflicting.

**Proposal: verify before adopting.** On a throwaway branch, with Code Mode on:

1. Make a change that fails `ruff check`, ask Claude to commit it, and confirm the hook
   blocks it with ruff's output.
2. Ask Claude to `git push origin main` and confirm the deny rule refuses it.
3. If either fails, Code Mode stays off for this repo until the guards move somewhere
   that holds, such as a git `pre-commit` hook and branch protection on GitHub.

Item 3's fallback is worth considering anyway. A git `pre-commit` hook guards a commit
however it's made, while a Claude Code hook guards only the commits Claude Code makes
through the tool it matches.

**Proposal: measure it, don't take the 30% on trust.** Run the next comparable PR, such
as one frontend page through `react-coder` and `react-reviewer`, once with Code Mode on
and once off. Compare the session's tokens and cost, and whether either needed more
review rounds. One run each is enough to decide whether to keep it on.

### 2. The app's generation graph

The blog-post graph (`libs/generate_text/graphs/blog_post/`) is a fixed sequence of
single LLM calls (outline, draft, humanize) with review interrupts between them. No step
calls tools, so Code Mode has nothing to replace today. It becomes relevant when a step
gains tools.

| Future feature (`plan.md`) | Where Code Mode's ideas would help |
| -------------------------- | ---------------------------------- |
| Phase 3 › 5 Humanization, "possibly as several calls" | If humanize becomes an agent with checks it calls (an AI-tell rubric, a writing-style comparison), one code step can run every check and return only the failures, instead of each check's full output going back into the prompt |
| Phase 3 › 7 Tags suggested by an LLM | Fetching the existing tag list, matching and merging can happen in code, with only the final tags returned |
| Later › Models per request (an Anthropic client) | The Claude API's **programmatic tool calling** is the API form of Code Mode: Claude calls your tools from inside the code execution tool (`code_execution_20260120`, with `allowed_callers` on each tool), so intermediate results never enter the context |
| Any long agent loop | The API's **context editing** (`clear_tool_uses_20250919`, beta) clears old tool results, the managed version of "the model deletes its own noise". **Tool search** keeps a large tool list out of the prompt until it's needed |

All three API features are Anthropic-only. `build_llm_service` registers only
`OpenAiLlmService` (`launchdarkly-agentcontrol.md` › Where the model is chosen), so they
wait for the Anthropic client in Later › Models per request.

### 3. The broader point: less harness, more model

The video's claim is that harnesses are being simplified as models get better at writing
code. That's a reason to keep the graph's shape easy to change. `graph_version` already
pins a run's shape (`launchdarkly-agentcontrol.md` › The graph). When Humanization is
reworked, it's worth trying one capable call with good instructions before splitting it
into several fixed steps.

## To decide

- Whether to run the hook and deny-rule check, and whether to move the commit checks to
  a git `pre-commit` hook either way
- Whether to measure one PR with Code Mode on and one with it off
- Whether the Humanization rework should be one call or several (Phase 3 › 5), and
  whether it waits for the Anthropic client
