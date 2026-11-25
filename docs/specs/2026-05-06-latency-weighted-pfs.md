# Latency-Weighted PFS — Design & Implementation Plan

**Status:** Draft, awaiting kickoff on Phase 0
**Author:** drafted 2026-05-06
**Scope:** Add a latency-aware "Quality" score on top of PAL-Bench PFS. Forward-only — no retrofit of the 2026-04-17 sweep.

---

## 1. Goals and non-goals

### Goals
- Capture per-call **TTFT** (time-to-first-token) and **total response time** for every API call made during a sweep.
- Produce a `PFS_weighted` metric that penalises slow test-model responses, with a smooth, tunable curve.
- Surface raw PFS, weighted PFS, and TTFT P90 side-by-side in the leaderboard so the penalty is auditable.
- Make the weight function tunable post-hoc — recomputing weighted PFS from already-captured latency must not require a re-run.

### Non-goals
- ELO weighting. PFS only.
- Adversarial pass-rate weighting.
- Retrofitting the 2026-04-17 sweep (no latency data was captured).

---

## 2. Design decisions (locked)

| Dimension | Choice | Rationale |
|---|---|---|
| What gets weighted | **PFS only** | Cleanly defined as a mean of rubric scores; multiplying it preserves semantics. ELO is a derived statistic where weighting muddies "head-to-head win rate" interpretation. |
| Latency signal | **Test-model TTFT**, per-turn, aggregated to per-conversation P90 | TTFT drives perceived responsiveness in CVI (TTS streams as soon as tokens land). Judge latency is irrelevant to product UX. |
| Latency target | **500 ms** | Tavus CVI / real-time voice usability threshold. |
| Weight curve | **Exponential decay above target, no floor**: `weight = exp(-max(0, ttft_p90 - 500) / τ)`, starting τ = 2000 ms | Single tuning knob. "Increasingly large penalties" — each extra ms costs proportionally more than the last. No floor matches "this would be unusable in CVI." |
| Aggregation level | **Per-conversation** weight × PFS, then mean | One slow conversation only docks its own contribution. Honest sample distribution. |
| Capture mechanism | **Streaming** (`stream=True`) on test and judge clients | Only way to physically measure TTFT. Also capture total time. |
| Rollout | **Forward only** | No latency in old data. |

---

## 3. Penalty curve

`weight(ttft_p90) = exp(-max(0, ttft_p90 - target_ms) / tau_ms)`

Starting parameters: `target_ms = 500`, `tau_ms = 2000`.

Sample weights at τ = 2000 (PFS 14 → weighted, for intuition):

| TTFT P90 | Weight | PFS 14 → weighted |
|---|---|---|
| 500 ms | 1.000 | 14.00 |
| 1000 ms | 0.779 | 10.91 |
| 1500 ms | 0.607 | 8.50 |
| 2000 ms | 0.472 | 6.61 |
| 3000 ms | 0.287 | 4.02 |
| 5000 ms | 0.105 | 1.47 |
| 8000 ms | 0.024 | 0.34 |

If this proves too aggressive in the first sweep, τ is the only knob to turn. τ = 3000 makes 1500 ms → 0.72 instead of 0.61.

---

## 4. Implementation phases

### Phase 0 — Latency capture in utils/api.py

**File:** [utils/api.py](../../utils/api.py)

- Switch `requests.post` to streaming (`stream=True`) for both test and judge clients.
- Wrap with `time.perf_counter()`:
  - `ttft_ms` = time from request send to first SSE chunk arrival.
  - `total_ms` = time from request send to last chunk.
- Reassemble streamed chunks back into the same `content` string the rest of the code expects — zero callsite changes for the synchronous return value.
- Append a per-call record to a per-run JSONL log: `{model, model_type, ttft_ms, total_ms, prompt_tokens, completion_tokens, status, timestamp}`.
- Expose latency on the call result (return tuple, thread-local, or attach to a context object — choose least invasive after closer read of callsites).
- Endpoint compatibility check: Helicone, OpenRouter, OpenAI, Anthropic-compat all support streaming.
- **Fallback path:** if streaming fails or the endpoint returns non-SSE, fall back to non-streaming and record `ttft_ms = total_ms` with a flag indicating the value is estimated (so it can be filtered out of strict analyses).

**Smoke test before any large sweep:** small 1-model, 1-persona, 4-scenario run to confirm streaming works on every endpoint we care about and that TTFT values are sane.

### Phase 1 — Conversation-level latency persistence

**File:** [core/conversation.py](../../core/conversation.py)

- For each scenario task, accumulate test-model TTFTs across turns (judge turns excluded from weighting; still logged).
- Compute and store on the task blob:
  - `ttft_ms_per_turn` (raw list)
  - `ttft_p50_ms`, `ttft_p90_ms`
  - `total_p90_ms`
- These become part of `scenario_tasks[iter][sid]` in the per-persona run files (`fullsweep_<persona>.json`).

### Phase 2 — Weighted PFS aggregation

**New file:** `utils/latency_weight.py`

```python
def latency_weight(ttft_p90_ms: float, target_ms: float = 500, tau_ms: float = 2000) -> float:
    if ttft_p90_ms is None:
        return None  # no latency data → caller decides
    return math.exp(-max(0.0, ttft_p90_ms - target_ms) / tau_ms)
```

**Aggregator changes:** wherever `_fullsweep_aggregated.json` is built (likely [scripts/run_fullsweep.py](../../scripts/run_fullsweep.py) and/or its aggregation pass), emit alongside existing fields:
- Per `(model, persona, scenario, iteration)`: `pfs_weighted = latency_weight(ttft_p90_ms) × pfs`.
- Per `(model, persona)`: mean `pfs_weighted` across conversations; mean `ttft_p90_ms`.
- Per model: persona mean of both.

**Edge case:** conversation with no TTFT samples (judge-only error path, all turns failed) → exclude from weighted mean, count under `weighted_n` so the sample-size table makes the gap obvious.

**Always keep raw `pfs` reported.** Weighted is additive, not a replacement.

### Phase 3 — Leaderboard surfaces

**File:** [scripts/build_presentation_dataset.py](../../scripts/build_presentation_dataset.py) and any leaderboard renderers.

- Top-line leaderboard gains columns: `PFS`, `PFS_weighted`, `TTFT P90 (ms)`.
- Per-persona table likewise.
- New short section: per-model latency distribution (P50 / P90 / P95 across all conversations), so the headline weighted number is traceable to an underlying latency story.

### Phase 4 — Tuning hooks

- Expose `target_ms` and `tau_ms` as CLI flags on the reporting / aggregation step (not on the sweep runner — re-weighting is post-hoc since raw latencies are persisted).
- New script: `scripts/recompute_weighted_pfs.py` (or extend [scripts/recompute_elo.py](../../scripts/recompute_elo.py)) — re-reads per-conversation TTFTs from the run files and re-emits the aggregated dataset with new weight params. No model re-run needed.

---

## 5. Risks and edge cases

- **Streaming refactor breaks endpoints.** Mitigate with the non-streaming fallback. Phase 0 ships behind a smoke run before any full sweep.
- **Cold-start latency outliers.** First call to a model after a cold endpoint can be artifactually slow. P90 across 96 conversations × multi-turn should absorb this; eyeball the distribution before publishing.
- **Helicone proxy adds fixed latency** (tens of ms). All test models share the proxy, so it's a constant offset and does not bias relative comparison.
- **Judge latency is captured but unused for weighting.** Keep it in the JSONL anyway — useful for cost / throughput retrospectives and the future-judge-swap evaluation (GLM 5.1 vs Opus 4.7).
- **Provider-reported usage tokens may be missing on streaming.** Some endpoints only emit usage in the final SSE event — confirm during the smoke run.
- **τ choice will look wrong on the first sweep.** That's expected. Plan to publish two τ values (e.g., 2000 and 3000) on the first run with weighted PFS so the leaderboard's sensitivity to the knob is visible.

---

## 6. Out of scope (explicit)

- ELO weighting.
- Adversarial pass-rate weighting.
- Retrofitting the 2026-04-17 sweep — no latency data exists.
- Per-criterion latency weighting — PFS is the headline; per-criterion analysis stays raw.

---

## 7. Open items

- Decide where the per-call JSONL log lives (`logs/latency/<run_id>.jsonl` is the obvious choice).
- Confirm whether streaming fallback flag should propagate up into per-conversation metadata (probably yes — exclude flagged conversations from strict weighted-PFS computation).
- Naming: `pfs_weighted` vs `pfs_quality` vs `qfs` — settle before Phase 2 emits the field, since downstream consumers will pin to it.
