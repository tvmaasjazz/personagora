# UI libraries for Claude Code — notes and ideas

**Video:** [UI Libraries for Claude Code (Ban the AI Look)](https://www.youtube.com/watch?v=zsCGS-Yzjnw),
Griffin Wooldridge, 4.5 min, 2026-11-07.

These are ideas, not a build plan. Every library below is a new dependency, and CLAUDE.md
says to ask before adding one.

The video's English captions read as machine-translated, so a few library names may be
garbled. Names are given as the video's spelling suggests and need checking before use.

## What the video says

When AI builds a toast, a command menu or a loading state from scratch, it gets the
default design every time and misses the details: how toasts stack, or how a drawer
should feel when dragged. Component libraries fix that. There are three kinds.

**1. Foundations: shadcn/ui, Base UI, Radix.** They handle behaviour, keyboard navigation,
focus and accessibility, which are easy to get wrong by hand. You style them. Use them for
most of the app: buttons, inputs, dialogs, lists, tabs. **The catch:** shadcn's default
look has become the signature of AI-built apps: the same radius, the same greys, the same
fonts. Change **radius, colors and fonts**, the three things that shape identity most. A
smaller radius and a serif heading make the same components read as an editorial product
rather than a SaaS template. shadcn copies the code into the project, so Claude can edit
all of it. Give Claude the brand colors and fonts up front.

**2. Specialists**, each doing one component well:

- **Sonner**: toasts that group, expand on hover and animate in and out
- **Vaul**: drawers that slide up from the bottom on mobile and close when dragged down
- **cmdk**: a ⌘K command menu and search
- **NumberFlow**: numbers that animate when they change, such as a price or a balance

You notice them when they're missing. AI-built toasts overlap or vanish too fast,
AI-built drawers don't respond to dragging, and AI-built command menus break on keyboard
use. Emil Kowalski, who made Sonner and Vaul, publishes a "pick UI library" skill: when
Claude needs a component, it suggests one library from a short list with a sentence on
why.

**3. Design components**: styled components copied into the project.

- **An AI-interface library** (the captions call it "Beautiful UI") built for AI
  products: streaming text, agent approval cards, diff views, agent screens. Most libraries
  predate AI products and don't cover these states. Look here first for an AI product
- **Magic UI**: 150+ free animated components built on shadcn
- **Aceternity**: landing-page effects, background beams, moving lines
- Others in the same vein, and **21st.dev**, a marketplace of components from many
  designers

The rule for this group: **one accent per page.** One animated heading or one interactive
background looks professional. Ten looks like another AI design where everything glows
and nothing stands out.

**Getting Claude to use them:** name the library in the request ("shadcn for the basics,
Sonner for toasts"), install through the CLI or registry so the code lives in the project,
or install the pick-a-library skill.

## How it applies here

### 1. Foundations: already in place, partly customised

The frontend already does what the video recommends. shadcn on Radix (`radix-ui`) is the
foundation, components are added through the CLI, and `react-styling.md` › Components
treats `components/ui/` as vendored, with deliberate variant edits only.

On the three identity levers:

| Lever | State | Gap |
| ----- | ----- | --- |
| Radius | Set from Substack: 8px buttons, 12px inputs, 16px cards (`--radius: 0.5rem`) | None |
| Colors | Dark-only tokens with a purple primary, measured from Substack | None |
| Fonts | `--font-serif` is Spectral, but `react-styling.md` notes Spectral isn't loaded, so posts render in Georgia | **The serif for reading is the one that matters most for a blog, and it isn't actually shipped** |

**Proposal:** load Spectral (or whichever serif is chosen) for post text, or change the
token to the font that's meant. A font file or a Google Fonts link isn't an npm
dependency, but it is a visible product choice, so it's Tyler's call. This also connects
to the Stripe talk's point about having a point of view
(`scaling-intent-quality-artistry.md`): the look is currently Substack's, and type is the
cheapest place to make it Personagora's.

### 2. Specialists: where each would fit

| Library | In the app? | Where it would fit |
| ------- | ----------- | ------------------ |
| Sonner | Yes (`components/ui/sonner.tsx`, `react-structure.md` › Toasts) | Done |
| Vaul | No | Below `md` the nav rail collapses to icons, and below `lg` a page's sidebar moves into the main column (`react-styling.md` › Layout). A bottom drawer could hold a run's review actions or a persona's actions on a phone. Only worth it if phone use matters for creators |
| cmdk | No | Search across personas and posts, if `plan.md` › Phase 1 › 7 Paging and search gets a global search. shadcn's own `command` component wraps cmdk, so it would come in through the CLI like the other components |
| NumberFlow | No | The credit balance, shown in `user-menu.tsx` and `account-details.tsx`, and, later, author stats and like counts (Phase 3 › 7). A balance that ticks down after a run reads as live. Low priority |

### 3. Design components: the AI-interface kind fits best

Personagora is an AI product, and its central screen is AI-shaped: the run page
(`routes/generate-text-run-page.tsx`, `features/generate-text/components/`) shows a step
tracker, the step's output, approve or request changes, and rewrites. That matches the
states the AI-interface library covers:

- **Approval cards**: `run-review-actions.tsx` and `request-changes-form.tsx`
- **Diff views**: there's no way to see what a rewrite changed from the previous pass.
  A diff between passes would let a reviewer check their feedback landed without
  rereading the whole post. This is the most useful idea in the video for this app
- **Streaming text**: only if generation moves to the SSE stream in `plan.md` › Later

**Proposal:** before building the diff view or the review cards by hand, look at that
library's versions of them as a reference, even if only to borrow the interaction. Adding
it as a dependency is a separate decision.

Magic UI and Aceternity effects fit only a future marketing or landing page. If one is
built, the "one accent per page" rule goes with it.

### 4. Encoding the choice so Claude follows it

The video's advice is to name the library in each request, or install a skill that
picks one. This repo already has the better form: `react-styling.md` › Components and
`react-structure.md` › Toasts tell `react-coder` what to use, and they load automatically
on frontend files.

**Proposal:** when a specialist is adopted, add one line to `react-styling.md` ›
Components naming it and its job ("A bottom drawer is Vaul, through `components/ui/drawer.tsx`"),
the way Toasts names Sonner. That covers what the third-party skill would do, without a
skill to install and keep current. The `all-code-is-slop.md` note applies too: where a
check can enforce the choice, such as banning a hand-rolled toast, a lint beats a rule
line.

## To decide

- Whether to load the reading serif, and which one
- Whether a diff between rewrite passes goes on the run page, and whether to borrow its
  design from an AI-interface library
- Whether Vaul, cmdk or NumberFlow is worth adding, each asked for separately as a
  dependency
- Whether the "pick UI library" skill is worth installing, or the rules lines are enough
