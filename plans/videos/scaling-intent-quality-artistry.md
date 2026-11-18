# Scaling intent, quality and artistry with AI — notes and ideas

**Video:** [How to scale intent, quality, and artistry with AI](https://www.youtube.com/watch?v=GLvFTMtw4Jk),
Katie Dill (Stripe), Lenny's Podcast, 22 min, 2026-09-25.

These are ideas, not a build plan. Nothing here changes a rule, an agent or a prompt
until Tyler picks it up.

The video's English captions read as machine-translated, with lines like "even a
mother" (probably "even your mom") and "pipsing Pepsi" (a Stripe word for meticulous
polish). The summary follows the argument, not the captions' wording.

## What the video says

**The warning.** After World War II, builders copied modernism's look without its
intent, and cities filled with "zombie buildings" that ignore their context. AI is a new
building boom, and Dill sees three warning signs:

1. **LLMs give the most likely answer**: what was popular, not what's specific to your
   brand or your user. Her example is a Korean barbecue site that looks like a software
   company's.
2. **"Done" comes too fast.** Like a microwave burrito, a polished-looking result in 90
   seconds makes you overlook its flaws. Does it actually solve the problem?
3. **Fast work feels disposable**, and gets treated that way: nobody owns its long-term
   upkeep.

Together they make **zombie UI**: monotonous, empty or neglected interfaces. The
opposite is software with small signs of care, like a calendar icon showing today's
date, or a wallet that anticipates an agent's checkout problems.

**Four recommendations:**

1. **Have a point of view.** If you don't, the AI supplies a generic one. Define who you
   are to your users and what they care about; that becomes your standard. Stripe's is
   optimism, applied to colors, writing and products. In a design review, a partner
   asked what the quality bar is for something AI made. The answer: users don't care how
   it was made, only whether it's good. That review produced 17 fixes. The aim isn't
   perfection, it's "one level deeper than the customer can see". To build taste, learn
   to notice: what users need rather than what they say, and what's good in the world
   around you.
2. **Encode your standards into the machine.** Decisions now get made with no designer
   in the room: agents fix bugs overnight, and UI is generated live. Yesterday's design
   system scaled consistency; today's must scale *intent*. Gutenberg cut 290 characters,
   not 52, so machine type looked hand-set. Stripe first tried an MCP server over its
   design docs, and three people asking the same thing got three different answers. They
   replaced it with a CLI built on the design system that serves the right documentation
   at the right moment, to avoid context rot. It holds whole **patterns and flows**, not
   just components, so it knows how the product should behave, and it's deliberately
   opinionated.
3. **Don't confuse "done" with "good."** The quality filter used to run through every
   stage, because only one idea in 20 got built. Now 20 get built a week, so the filter
   has to come after creation, when saying no is harder. That's the **editor's** job:
   someone who looks at the whole and asks whether it solves the problem, matches how the
   user thinks, and holds together. AI is weak at the unexpected detail and the theme
   underneath. Her team iterated an event's intro animation 56 times; AI made that
   exploration affordable, but people judged each pass.
4. **Unleash creativity.** AI can make sameness, but it's also the biggest creative tool
   we've had. Give it specifics: what you believe, what's good, what worries you, and the
   source material behind your standards. Don't accept the first output. Use adversarial
   agents to critique it. For a team, make room to explore and "protect the strange".
   Use AI's savings to raise the ceiling, not only the floor.

## How it applies here

The talk is about product design, but Personagora's product is generated writing. Every
warning applies twice: to the app's screens, and to the posts the graph writes. A zombie
blog post is the most likely post, polished, generic, with no point of view.

### 1. A point of view for the posts

| Idea | Where it lands | Why |
| ---- | -------------- | --- |
| A persona's point of view drives the draft, not only its style | `blog_post_draft_prompt.py` | A persona has `bio`, `background`, `writing_style`, `default_tone`, `default_target_audience` and `sample_writing`. What a persona *believes* or argues for has no field, so the draft falls back to the likely take |
| A "point of view" or "beliefs" field on a persona | Persona form, `psg_persona`, Phase 3 › 3 Persona from voice or text | The "persona from voice or text" call is the natural place to ask for it, since people describing a persona usually say what it cares about |
| The humanize step gets standards, not a generic instruction | `blog_post_humanize_prompt.py`, Phase 3 › 5 Humanization | The system prompt says "remove anything that reads as AI-generated". That's the general version. Tyler's humanizing samples and notes are the source material the talk says to feed in |

### 2. Encode the standards

**For posts: a written AI-tell rubric.** The rework in Phase 3 › 5 is where the talk's
second recommendation lands. Keep the rubric as data the humanize step and a critic both
read, not as prose buried in one prompt: the tells to remove (filler, hedging,
throat-clearing openers, tidy three-part lists, the summary closer) and what good looks
like, with an example of each from Tyler's samples. This fits the existing pattern:
`BLOG_POST_BODY_FORMAT_RULES` is already one module that both feeds the prompt and
validates the output (`launchdarkly-agentcontrol.md` › Where the prompt is built).

**For the app: patterns and flows, not only tokens.** Stripe's point is that components
aren't enough; the system has to know how the product behaves. This repo is partway
there:

- `react-styling.md` holds tokens, shapes and layout.
- `react-structure.md` › States, Forms and Routing hold behaviour: every loading, empty,
  error and not-found state, confirm dialogs, and `CardListSkeleton`, `QueryErrorState`
  and `DataTable` as the building blocks.

Gap: there's no rule for a whole page pattern, such as "a list page", "a detail page
with a sidebar" or "a create form". Each new page is assembled from parts and checked
part by part. **Proposal:** when the next page of a kind that already exists gets built,
add one line per page kind to `react-structure.md` naming the existing page to copy
("the pattern is `routes/...`"), per CLAUDE.md › Keeping the rules current.

Stripe also moved from an MCP server to a CLI that serves the right doc at the right
time. The repo already does this: rules in `.claude/rules/` load by path glob, so an
agent editing a `.tsx` file gets `react-styling.md` and nothing about Alembic.

**The look itself.** `react-styling.md` opens with "the look follows substack.com …
Purple replaces Substack's orange." That's a reasonable starting point for reading
layouts, and exactly the borrowed-without-intent pattern the talk warns about.
**Proposal, low priority:** before the public launch, write two or three sentences on
what Personagora is to its readers, and let one or two deliberate details come from that
instead of from Substack. That's a product call, not a code change.

### 3. An editor for "done" versus "good"

The app already has an editor: the human-in-the-loop review of each outline, draft and
humanized version. The talk suggests two things.

| Idea | Where | Why |
| ---- | ----- | --- |
| A critic step before the human review | Blog-post graph, Phase 3 › 5 | An adversarial LLM pass that scores the output against the rubric and lists its failures. The reviewer then sees the critique beside the text, so their attention goes to judgement, not to spotting the tells. Changing the graph's shape bumps `graph_version` and breaks paused runs, so it ships with the Humanization rework, not alone |
| Show the critique in the review screen | `routes/generate-text-run-page.tsx` | The editor needs to see what the machine flagged, then decide. An approval with no flags reads as "done", not "good" |

**For the codebase: a whole-flow review.** The review chain (`be-reviewer` or
`react-reviewer`, then `/code-review`, `/simplify`) checks each PR against the rules.
Nothing checks whether a finished *feature* holds together for a user, the editor's
question. **Proposal:** when the last PR of a multi-PR feature merges, one pass walks the
flow end to end in the running app (the Playwright flows in `frontend/e2e/` already drive
it) and Tyler, or an agent briefed as a first-time user, answers: does it solve the
problem, does it match how the user thinks, does anything feel disjointed across screens?
This belongs in `REVIEW.md` as one line if adopted.

### 4. Creativity

- **Specific input beats a short brief.** The generate form takes `additional_context`
  (`features/generate-text/generate-blog-post-form-schema.ts`).
  Its placeholder or help text could ask for what the talk asks for: what you believe,
  what's good, what worries you, and a source to work from.
- **Don't take the first output.** The review loop already allows rewrites up to
  `max_rewrite_passes`. If generation cost allows, offering two drafts to choose between
  is a cheap way to "try 56 times".
- **Protect the strange.** When the Humanization rework tries prompts and models (Phase
  3 › 5), keep a variant that pushes for an unusual angle, and judge it on the same
  samples as the safe one.

## To decide

- Whether a persona gets a point-of-view field, and whether "persona from voice or text"
  asks for it
- Whether the Humanization rework adds a rubric module and a critic step, and whether
  the review screen shows the critique
- Whether to add page-pattern lines to `react-structure.md` as pages of an existing kind
  are built
- Whether a whole-flow review step goes into `REVIEW.md`
- Whether to write a short point of view for Personagora's own look before launch
