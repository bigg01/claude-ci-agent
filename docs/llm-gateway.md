---
icon: lucide/route
---

# LLM Gateway (optional)

An **LLM Gateway** is a reverse proxy that sits between the Claude CI agent and
the Anthropic API. Claude Code routes through it by pointing `ANTHROPIC_BASE_URL`
at the gateway instead of `api.anthropic.com`. The gateway then gives you two
things this project otherwise leaves to the API: **prompt-response caching** and
**guardrails**.

```text
Claude CI Agent ──(ANTHROPIC_BASE_URL)──▶ LLM Gateway ──▶ Anthropic API
                                          │  cache + guardrails
                                          └─ metrics / budget / audit
```

It is **optional and opt-in**: with `ANTHROPIC_BASE_URL` unset the agent talks to
`api.anthropic.com` directly, exactly as before. See the
[Architecture](architecture.md) diagram for where it fits.

## Why a gateway

The agent already streams every action through the
[OTel Collector](observability.md) for secret-scrubbed audit— but that is
*post-hoc* telemetry. A gateway acts *in-line* on the model traffic itself, so it
can cache responses and block bad requests **before** they reach the API.

## Prompt caching

Two distinct layers— a gateway uses both:

| Layer | Where | What it caches | TTL |
| --- | --- | --- | --- |
| **Native prompt caching** | Anthropic API (`cache_control`) | Large stable prefixes within a single request— system prompt, `CLAUDE.MD`, tool definitions | 5 min / 1 h |
| **Gateway response cache** | The gateway | Whole identical `(model, messages, tools)` requests across CI runs | Configurable |

The gateway passes `cache_control` through untouched, so **native caching keeps
working**. On top of that, its response cache deduplicates *repeated* calls— the
Advisor re-reviewing an unchanged file, or identical lint-summary prompts across
pipelines— and returns the stored completion without spending tokens. This is the
big lever in CI, where the same prompts recur run after run.

!!! tip "Cache key hygiene"

    The gateway keys on the **exact** request. Anything that varies per run— a
    timestamp, a pipeline ID, a random nonce in the prompt— defeats the cache.
    Keep volatile values out of the prompt prefix (the same rule that governs
    native caching).

## Guardrails

A gateway enforces policy on the wire, in both directions:

- **Input screening**— detect prompt-injection / jailbreak attempts and redact
  secrets or PII *before* the request leaves your trust boundary. This is
  defense-in-depth with the OTel scrubbing, which only redacts the audit copy.
- **Output screening**— block disallowed content, enforce response schemas, or
  strip anything that should never reach a PR comment.
- **Budget & rate limits**— cap spend per pipeline / project / token, and throttle
  runaway agents. Pairs with the `claude_code.cost.usage` metric the agent already
  emits (see [Observability](observability.md)).
- **Model allow-listing**— restrict the agent to approved models (e.g. only
  `claude-sonnet-4-6` / `claude-opus-4-8`), rejecting anything else.

## Different models— or vendors— for creation vs review

The two [personalities](ci-versions.md#personalities-triggers) do opposite jobs, so
it makes sense to run them on **different models, or even different vendors**:

- **Agent (creation)**— the heavy lift. Give it the strongest coding model
  (e.g. `claude-opus-4-8`); it writes the implementation.
- **Advisor (review)**— an *independent* check. Route it to a **different** model
  or vendor, so the reviewer doesn't share the creator's blind spots. When the
  same model both writes and grades its own work, a misread requirement or a
  hallucinated API tends to pass review unnoticed— it made the same mistake twice.
  A model trained differently de-correlates those failures and catches more.

### Why this is safe to do— spec-driven engineering

This only works because the work is **anchored to a written spec**, not to one
model's interpretation. The spec— acceptance criteria, the
[`CLAUDE.MD`](https://github.com/bigg01/claude-ci-agent/blob/main/CLAUDE.MD)
contract, an issue's definition of done— is the shared source of truth:

- The Agent implements **to the spec**; the Advisor reviews the diff **against the
  same spec**. The question is objective— *does this meet the spec?*— not "would
  *I* have written it this way," so a different reviewer model stays grounded
  instead of bikeshedding style.
- The spec is the contract that lets you **swap the model behind either role**
  without changing the pipeline. Creation and review are interchangeable engines
  bolted to a fixed specification, which is the whole point of spec-driven work.
- Independent review is only meaningful when it's actually independent. Model/vendor
  diversity is what turns "the AI reviewed itself" into a real second opinion.

### Wiring it up

The pipelines already set `CLAUDE_PERSONALITY` (`agent` / `advisor`) on each job,
so you have two levers:

- **Different Claude models— no gateway needed.** Set a different `CLAUDE_MODEL`
  per personality job (Agent → `claude-opus-4-8`, Advisor → `claude-sonnet-4-6`,
  or vice-versa). Each personality already passes `--model "$CLAUDE_MODEL"`.
- **Different vendor— via the gateway.** Point both at the gateway and let it
  route on the `CLAUDE_PERSONALITY` (or a header you add), sending the Advisor's
  traffic to a non-Anthropic backend that speaks the `/v1/messages` shape. LiteLLM
  and Portkey both support per-route model/vendor mapping. Keep the
  **model allow-list** above scoped per route so each personality can only reach
  its intended backend.

!!! tip "Pin the reviewer for reproducibility"

    Pin the review model/vendor to a specific version, the same way you pin the
    creation model— a moving reviewer makes review outcomes non-reproducible across
    runs of an unchanged diff.

## Choosing a gateway

Any Anthropic-compatible proxy works— it must expose the `/v1/messages` API shape.
Common options:

| Gateway | Notes |
| --- | --- |
| [LiteLLM Proxy](https://docs.litellm.ai/) | Self-hosted; response caching (Redis), guardrails hooks, budgets. Good default for self-hosting in your cluster. |
| [Portkey](https://portkey.ai/) | Caching + guardrails + observability, hosted or self-hosted. |
| [Cloudflare AI Gateway](https://developers.cloudflare.com/ai-gateway/) | Managed caching, rate limiting, analytics. |
| [Kong AI Gateway](https://konghq.com/) | API-gateway-native plugins for AI traffic. |

Host the gateway **inside your trust boundary**— it sees full prompts and
completions. A central in-cluster service (one gateway, many pipelines) is the
usual shape; a per-job sidecar also works.

## Enabling it

Point the agent at the gateway and (if the gateway authenticates separately)
hand it the gateway key. Claude Code reads both from the environment:

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_BASE_URL` | The gateway endpoint, e.g. `https://llm-gateway.internal/v1` |
| `ANTHROPIC_AUTH_TOKEN` | Gateway credential, when the gateway fronts the real Anthropic key |

=== "GitLab CI"

    Define `ANTHROPIC_BASE_URL` as a CI/CD variable— GitLab exports it into the
    job environment automatically, and the agent picks it up. No pipeline edit
    needed.

=== "GitHub Actions"

    Add it to the personality jobs' `env:` (it is empty, and therefore inert,
    until you set the repository variable):

    ```yaml
    env:
      ANTHROPIC_BASE_URL: ${{ vars.ANTHROPIC_BASE_URL }}
    ```

=== "OpenBao"

    Store `ANTHROPIC_BASE_URL` (and `ANTHROPIC_AUTH_TOKEN`) at your
    [OpenBao](secrets-openbao.md) `BAO_SECRET_PATH`— they flow into the job with
    the rest of the secrets, keeping the gateway endpoint and key out of CI
    config entirely.

!!! note "Keep telemetry pointed at the collector"

    The gateway only handles **model** traffic. `OTEL_EXPORTER_OTLP_ENDPOINT`
    still points at the OTel Collector sidecar on `localhost:4318`— the two paths
    are independent.
