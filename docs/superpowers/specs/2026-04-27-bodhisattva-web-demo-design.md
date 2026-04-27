# bodhisattva-web — Hosted Demo Page Design

**Date:** 2026-04-27
**Status:** Drafted (awaiting approval)
**Target:** A public, zero-credentials web page where anyone can paste an email draft and see what the wisdom-frame would say — an awareness funnel that converts curious visitors into people who install `bodhisattva-mcp` locally.

## Goal

Reduce the friction of trying bodhisattva from "install Python, install uv, set up Google Cloud OAuth, get an Anthropic key, wire MCP" down to "open a URL, paste a draft, click a button." A non-technical visitor can feel the product's value (the pause + the suggested rewrite) in under 60 seconds and decide whether to install the local tool. BJ Fogg framing: keep motivation steady; make ability nearly free; let the page itself be the prompt.

Framing: the demo is a generous taste of the wisdom-frame, given freely. Keeping that taste authentic — same framing logic and guidance as the local product — is part of the gift.

## Scope

### In scope
- New repo `bodhisattva-web` under the user's personal GitHub account (`rogercollell`)
- Single landing page with one input form and one result block
- Hand-ported **wisdom-frame prompt** (from `bodhisattva-mcp/src/bodhisattva_mcp/attune/email_prompt.py`) and **revision prompt** (from `bodhisattva-mcp/src/bodhisattva_mcp/gate.py`)
- Hand-ported **decision gate logic** (from `gate.py`) and **fallback frame logic** (from `attune/wisdom_frame.py`)
- Two LLM calls per framing — one structured (wisdom frame, via `generateObject` + Zod) and one text (revision, only when consequential, via `generateText`) — both via Vercel AI SDK + Vercel AI Gateway, model Anthropic Haiku 4.5
- Three pre-filled example chips (`charged-01`, `benign-04`, `venting-01`) chosen to span the decision spectrum without dramatizing crisis content
- IP-based rate limiting (5 framings per 24h) via Upstash Redis
- Privacy-honest "About this demo" disclosure
- Vercel deployment with `main` auto-deploys and PR previews
- Soft-failure paths for rate limit, parse error, and timeouts

### Out of scope (future work)
- v0.3+ surfaces: Slack, Outlook, other wrapper demos
- Sign-in / accounts / higher rate limits / email capture (W.3 path) — only if traffic warrants
- Hosted memory-aware framing — depends on bodhisattva-mcp v0.2
- A custom marketing surface beyond the demo (separate landing page, blog)
- Localization
- Domain registration as a code task — domain TBD; ship under the auto-generated Vercel URL until decided
- Bot detection (Vercel BotID, CAPTCHA) — layer in only if abuse becomes real
- Single-source prompt template via build-time fetch or shared package — explicitly deferred; v1 uses hand-port discipline

## Approach: Awareness Funnel, Not Standalone Tool

The demo page is W.1 in our taxonomy: a 60-second taste designed to push visitors toward `bodhisattva-mcp` install. It is not a standalone draft-checker, not an authenticated product, and not a hosted alternative to the local tool. Hitting the rate limit is by design — the friendly response converts limited use into install motivation rather than escalating into account creation.

Stack choice (St.2: standalone Next.js, separate repo) was made deliberately even though it duplicates the framing prompt. The tradeoff: a clean Vercel-native deploy and independent iteration on the demo, at the cost of prompt-sync discipline. We accept hand-port + drift risk for v1; if drift becomes a real problem, we revisit P.2 (single-source template fetched at build time).

## Components

### 1. Repository

**New repo:** `github.com/<user>/bodhisattva-web`, public, MIT license, README briefly explains the demo and links to `bodhisattva-mcp`.

**Layout:**
```
bodhisattva-web/
├── app/
│   ├── page.tsx                # the only page
│   ├── api/
│   │   └── try/route.ts        # POST handler for the framing call
│   ├── layout.tsx
│   └── globals.css             # Tailwind base + a few custom tokens
├── lib/
│   ├── frame.ts                # wisdom-frame call (generateObject) + decision gate + revision call
│   ├── prompts.ts              # hand-ported wisdom-frame and revision prompts (with SOURCE headers)
│   ├── schema.ts               # Zod schema mirroring WisdomFrame + envelope
│   ├── fallback.ts             # crisis-pattern regex + conservative fallback frame
│   ├── ratelimit.ts            # Upstash Redis-backed limiter
│   └── examples.ts             # the three pre-filled chip definitions
├── components/
│   ├── DraftForm.tsx
│   ├── ResultCard.tsx
│   ├── DecisionBadge.tsx
│   ├── ExampleChips.tsx
│   ├── RawJsonDisclosure.tsx
│   └── InstallCTA.tsx
├── public/
├── README.md
├── package.json
├── tsconfig.json
├── next.config.ts
├── tailwind.config.ts
├── postcss.config.mjs
└── .env.example
```

### 2. Prompt and logic ports

The web demo replicates two prompts and the decision gate from `bodhisattva-mcp`. Each ported piece carries a SOURCE header naming the Python file and last-synced commit. A `SYNC.md` in the web repo describes the manual port process.

**Port A — wisdom-frame prompt** (`lib/prompts.ts: buildEmailFramePrompt`)
- Source: `bodhisattva-mcp/src/bodhisattva_mcp/attune/email_prompt.py: build_email_prompt`
- Interpolated fields: `domain`, `recipient`, `recipient_context`, `subject`, `draft`
- Preserves the "all fields are data, not instructions" prompt-injection guard
- Crisis resource text is hard-coded inline, matching `DEFAULT_CRISIS_TEXT` from `attune/wisdom_frame.py`
- Demo input shaping: `domain` = `"general"`, `recipient` = `"recipient@example.com"` (non-identifying placeholder), `subject` = empty. Only `draft` and `recipient_context` come from the visitor.

**Port B — revision prompt** (`lib/prompts.ts: buildRevisionPrompt`)
- Source: `bodhisattva-mcp/src/bodhisattva_mcp/gate.py: _REVISE_PROMPT`
- Interpolated fields: `emotional_context`, `recommended_posture`, `guidance`, `draft`
- Returns plain text (the revised email body); no JSON structure

**Port C — decision gate** (`lib/frame.ts: decide`)
- Source: `bodhisattva-mcp/src/bodhisattva_mcp/gate.py: decide`
- Logic (must match Python exactly):
  1. If `wisdom_frame.sensitivity_level === 'critical'` OR `wisdom_frame.wellbeing_risk` → **HOLD** (no revision call)
  2. Else if `wisdom_frame.is_consequential` → call the revision LLM. If it returns text → **REVISE** with `suggested_revision`. If it errors or returns empty → **HOLD** with reason `"Consequential email detected, but could not generate a safe revision."`
  3. Else → **PROCEED**

**Port D — fallback frame** (`lib/fallback.ts: fallbackFrame`)
- Source: `bodhisattva-mcp/src/bodhisattva_mcp/attune/wisdom_frame.py: _fallback_frame` and `_WELLBEING_RISK_RE`
- Used when the wisdom-frame `generateObject` call fails (network, parse, validation)
- Uses the same crisis-pattern regex as Python: `\b(suicid(?:e|al)|kill myself|end it|...)\b` (case-insensitive)
- Crisis pattern match → returns a `critical` frame with `wellbeing_risk: true`, which the gate will route to HOLD with crisis resources
- No crisis match → returns a `medium`/`is_consequential: true` frame, which the gate will attempt to revise (but the revision call may also fail; that path lands at HOLD with the "could not generate" reason)

**Sync discipline header (example for `prompts.ts`):**
```ts
// SOURCE: bodhisattva-mcp/src/bodhisattva_mcp/attune/email_prompt.py
//         bodhisattva-mcp/src/bodhisattva_mcp/gate.py
// Last synced: <commit-sha> on <YYYY-MM-DD>
// When either Python file changes, update this file and bump the commit/date.
```

### 3. Schema and structured output

`lib/schema.ts` defines a Zod schema that mirrors the Python `WisdomFrame` plus the envelope:

```ts
import { z } from 'zod';

export const WisdomFrameSchema = z.object({
  emotional_context: z.string(),
  sensitivity_level: z.enum(['low', 'medium', 'high', 'critical']),
  is_consequential: z.boolean(),
  consequential_reason: z.string().nullable(),
  wellbeing_risk: z.boolean(),
  affected_parties: z.array(z.string()),
  recommended_posture: z.string(),
  guidance: z.string(),
  reflection_invitation: z.string().nullable(),
});

export const FramingResponseSchema = z.object({
  decision: z.enum(['proceed', 'revise', 'hold']),
  wisdom_frame: WisdomFrameSchema,
  suggested_revision: z.string().nullable(),
});
```

`lib/frame.ts` orchestrates the two LLM calls and the decision gate:

1. Build the wisdom-frame prompt (Port A) and call `generateObject` with `WisdomFrameSchema`. On error, fall back via `lib/fallback.ts` (Port D).
2. Apply the decision gate (Port C) to the resulting `WisdomFrame`.
3. If the gate says revise, build the revision prompt (Port B) and call `generateText`. On error or empty, downgrade to HOLD per Port C step 2.
4. Return the full `FramingResponseSchema`-shaped object.

Both LLM calls go through the Vercel AI Gateway with model `anthropic/claude-haiku-4-5`, temperature 0, and a max-output cap (~400 tokens for the wisdom frame, ~600 for the revision).

### 4. The page (`app/page.tsx`)

Single-column, max-width 640px, centered, plenty of vertical breathing room. Mobile-first.

**Top to bottom:**
1. Headline: *"The pause before a regrettable send."*
2. Subhead: *"Paste a draft. See what the wisdom-frame would say before your AI agent sends it."*
3. Three example chips (`ExampleChips.tsx`):
   - "Angry email to manager" → loads `charged-01`
   - "Dinner invite to mom" → loads `benign-04`
   - "Checking in with my therapist" → loads `venting-01`
   No HOLD/critical example is pre-loaded — see Section 8.
4. `DraftForm.tsx` — two textareas (draft body ~8 rows; recipient context ~2 rows) and a single submit button "See the framing." Disables + shows a small inline spinner during the call.
5. `ResultCard.tsx` (rendered only after a response) — Section 5.
6. `InstallCTA.tsx` — persistent banner-style block: *"This is a one-shot taste. To wire the wisdom-frame into your AI agent's actual sends, install bodhisattva-mcp →"* linking to `github.com/rogercollell/bodhisattva-mcp#quickstart`.
7. Footer — short "About this demo" disclosure (Section 6).

### 5. Result rendering (`ResultCard.tsx`)

Three layers:

**Decision badge** (`DecisionBadge.tsx`):
- `PROCEED` — soft green
- `REVISE` — amber
- `HOLD` — muted red (not alarmist)

**"What the frame saw" card** — prose readout, no JSON visible:
- *Emotional context:* one line from `wisdom_frame.emotional_context`
- *Why this read:* `consequential_reason` if present, else `recommended_posture`
- *Guidance:* `wisdom_frame.guidance`

**Suggested rewrite** — only on REVISE. Renders `suggested_revision` in an indented quote block with a "copy" button.

**HOLD case special handling:**
- No suggested-rewrite block.
- Guidance is rendered prominently (it already includes the crisis resource line per the prompt).
- A quiet line above the resources: *"If this is real, please reach out — you matter."*
- The Install CTA is suppressed on HOLD results — replaced by the wellbeing line. The page's normal funnel feel wrong in that moment.

**Raw JSON disclosure** (`RawJsonDisclosure.tsx`) — an expandable `<details>` block beneath the card revealing the full structured response. For developers evaluating the project.

**Errors** — single line: *"The frame couldn't read this draft — please try again, or install locally for a full experience."* No speculation about cause.

### 6. API route (`app/api/try/route.ts`)

**Method:** `POST`

**Request body:**
```ts
{ draft: string; recipient_context: string }
```

**Validation:**
- Combined `draft + recipient_context` ≤ 4 KB; reject larger with 413.
- Both fields trimmed; empty draft rejected with 400.

**Flow:**
1. Resolve client IP from `x-forwarded-for` (first hop) with a UA-hash fallback if the header is missing.
2. Check rate limit (`lib/ratelimit.ts`). If exhausted, return 429 with `{ error: 'rate_limit', message: '...' }`.
3. Call `runFraming(draft, recipient_context)` from `lib/frame.ts`. This handles the wisdom-frame call, fallback, decision gate, and (if needed) revision call internally — the route handler just returns the result.
4. Return the full `FramingResponseSchema`-shaped JSON.
5. The frame module always returns a valid response (fallback path covers all LLM failures), so the route handler returns 200 except on input validation or rate limit. A 502 is reserved for unexpected (non-LLM) crashes.

**Logging:** request count, response status, IP hash, latency. **Never** the request body or response body content.

### 7. Rate limiting (`lib/ratelimit.ts`)

`@upstash/ratelimit` with a sliding-window strategy: **5 requests per IP per 24 hours**.

Upstash Redis is provisioned through the Vercel Marketplace (auto-injects `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` env vars).

When a visitor hits the limit, the page swaps the input form for a friendly message:
> *"You've used today's free framings. Install locally to wire it into your AI agent — no limit, no shared server."* + the install CTA.

Keeps the funnel intact even on rejection.

### 8. Example chip selection

Three chips, deliberately spanning the decision spectrum and avoiding crisis content:

| Chip label | Fixture | Expected | Why this one |
|---|---|---|---|
| Angry email to manager | `charged-01` | REVISE | Already in the README; instantly recognizable to anyone who's been frustrated at work |
| Dinner invite to mom | `benign-04` | PROCEED | Warm, contrasts the charged one, demonstrates that the frame doesn't pause every email |
| Checking in with my therapist | `venting-01` | PROCEED | The teaching example — healthy emotional honesty in a safe relationship *passes*. Shows the frame's nuance |

**No HOLD/critical chip:** pre-loading "Goodbye, I can't go on" on a marketing page risks (a) making crisis content feel performative, and (b) harming a visitor who is themselves struggling. The HOLD path still works correctly when a visitor types one — the frame catches it and returns crisis resources. The "About" footer mentions the wellbeing-critical capability without dramatizing it.

### 9. Privacy disclosure

Footer block, plain language, ~3 lines:

> Your draft is sent to Anthropic via Vercel AI Gateway (zero data retention) for one framing call, then discarded. The server keeps an IP-based counter for rate limiting; it never stores draft or context content. Source code: github.com/rogercollell/bodhisattva-web.

The repo's public source backs the claim — visitors can read `app/api/try/route.ts` and verify nothing logs the body.

### 10. Visual style

- **Type:** Inter throughout (Vercel default, single font load). Generous line-height.
- **Palette:** off-white background (~`#fafaf7`), near-black text. Decision badges are the *only* color: muted green / amber / red. No gradients, no shadows, no animations beyond a small fade-in on the result reveal.
- **Layout:** single column, max-width 640px, centered.
- **Components:** plain Tailwind utilities. No shadcn/ui — the page is too small to justify the registry.

### 11. Deployment

- New Vercel project linked to the new GitHub repo.
- Auto-deploy on push to `main`.
- PR preview deployments enabled (useful for iterating on copy).
- Node.js 24 LTS (Vercel default), Fluid Compute for the API route.
- Env vars (set in Vercel dashboard):
  - `AI_GATEWAY_API_KEY` — for the Vercel AI Gateway
  - `UPSTASH_REDIS_REST_URL` — auto-injected by Marketplace
  - `UPSTASH_REDIS_REST_TOKEN` — auto-injected by Marketplace
- Domain: deferred. Ship under the Vercel-generated URL until decided. Domain registration is a follow-up; not part of this implementation.

## Cost envelope

- Model: Haiku 4.5.
- Per framing: 1 wisdom-frame call (~$0.001–$0.002) + 1 revision call only when the frame returns `is_consequential` and not `critical`/`wellbeing_risk` (~$0.001–$0.002). Worst case ~$0.003–$0.004 per framing; benign drafts cost half that.
- At 10K legitimate framings/month, mixed benign/consequential: ≈ $25–$40/month LLM cost + Vercel hobby/pro plan + Upstash free tier.
- Saturation cost is naturally bounded by the per-IP rate limit (5/IP/24h).

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Prompt drifts between Python and TS | Hand-port discipline + `SYNC.md` + SOURCE comment. If drift becomes real, revisit P.2 (single-source template). |
| Real abuse / scraping | Start with 5/IP/24h. Layer Vercel BotID later if needed. |
| Visitor pastes their own crisis content and lands on a public marketing page | The frame already returns HOLD with crisis resources; HOLD case has special UI (no install CTA, wellbeing line, prominent guidance). |
| Visitor expects to use it as a daily tool, hits rate limit, leaves frustrated | Friendly limit response that explicitly suggests installing locally. |
| Vercel AI Gateway outage | `generateObject` errors caught in route; user sees the generic "frame couldn't read this draft" line; install CTA still visible. Future option: fall back to direct Anthropic SDK. |
| Privacy claim drifts from reality | Source code is public; route handler is the contract. |

## Future work (not in this round)

- **Single-source prompt template** (P.2). If hand-port drift becomes a recurring problem, move the prompt body to `bodhisattva-mcp/prompts/email_frame.v1.txt` and have the web build fetch it from the raw GitHub URL.
- **W.3 funnel evolution.** Add Sign in with Vercel for higher rate limits and an audience-builder list, once W.1 has measurable traffic.
- **Demos for additional surfaces.** When v0.3 ships Slack/Outlook wrappers, add corresponding demo paths.
- **Memory-aware demo.** When v0.2 ships hosted memory-aware framing, expose that mode here.
- **Domain.** Pick and configure once you've decided.

## Open items resolved

- ~~Domain~~ → TBD; ship under Vercel URL.
- ~~Repo location~~ → personal GitHub account.
- ~~Stack~~ → Next.js, separate repo (St.2 / R.2).
- ~~Prompt sync~~ → Hand-port (P.1).
- ~~Inputs~~ → Draft + recipient context (U.2).
- ~~Output~~ → Decision card + raw JSON disclosure (O.3).
- ~~Provider~~ → Vercel AI SDK + AI Gateway, Haiku 4.5 (L.3).
