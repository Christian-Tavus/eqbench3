# PALs-Bench — Project Overview

## What Is PALs-Bench?

PALs-Bench is a specialized benchmark for evaluating the quality of PAL companion personas and their system prompting. It extends the open-source [EQ-Bench 3](https://eqbench.com/) framework with 32 custom scenarios designed specifically for conversational companions — not general-purpose assistants.

The primary question PALs-Bench answers is: **"How well does this persona configuration perform as a companion?"** — not "how smart is the underlying model?" While model capability is a factor, the benchmark is designed to measure the effectiveness of persona design, system prompt engineering, and behavioral tuning. The same base model can score very differently depending on how its companion persona is configured.

PALs-Bench is built specifically for [Tavus CVI](https://docs.tavus.io) personas. Tavus personas operate in real-time video conversations where all responses are spoken aloud via TTS — not read as text. This means the benchmark evaluates not just emotional intelligence but also spoken-delivery fitness: response brevity (1-3 sentences per turn), absence of text-only formatting (markdown, bullet points), and natural conversational pacing. These constraints are reflected in the scoring criteria.

PALs-Bench focuses on the skills that matter for PAL: empathy under pressure, boundary management, guardrail resilience, persona consistency, and the ability to say "no" without breaking the relationship.

## Why This Matters

There is no off-the-shelf benchmark for evaluating AI companion personas. General EQ benchmarks test raw model capability, but they don't test the specific failure modes we care about in persona design — romantic escalation handling, prompt extraction resistance, dependency awareness, or graceful scope management. PALs-Bench fills that gap with scenarios drawn from real conversational patterns.

The benchmark produces two scores per persona configuration:

- **EQ Score** — standard emotional intelligence (comparable to public EQ-Bench leaderboard scores)
- **PAL Fitness Score** — companion-specific skills: persona fidelity, guardrail adherence, objective progression, refusal quality, and Gricean cooperation (adherence to conversational maxims of quantity, quality, relation, and manner)

Together, these give a quantitative basis for comparing persona configurations, measuring the impact of prompt changes, and tracking companion quality over time. Typical use cases include:

- **A/B testing persona prompts** — does a revised system prompt improve boundary handling without hurting warmth?
- **Regression testing** — did a prompt update introduce new failure modes?
- **Model migration** — when moving a persona to a new base model, does it maintain the same companion quality?
- **Guardrail validation** — do adversarial scenarios still pass after prompt changes?

## Scope

### 32 Scenarios Across 9 Domains

| # | Domain | Scenarios | Type |
|---|--------|-----------|------|
| 1 | Emotional Support & Companionship | 4 | Non-adversarial |
| 2 | Boundaries & Relationship Management | 4 | Non-adversarial |
| 3 | Coaching & Goal-Oriented | 3 | Non-adversarial |
| 4 | Creative & Playful | 3 | Non-adversarial |
| 5 | Conflict & De-escalation | 3 | Non-adversarial |
| 6 | System Integrity | 5 | Adversarial |
| 7 | Safety Boundaries | 4 | Adversarial |
| 8 | Hate Speech & Misinformation | 3 | Adversarial |
| 9 | Focus & Scope | 3 | Adversarial |
| | **Total** | **32** | **16 non-adversarial / 16 adversarial** |

Each scenario uses fixed (canned) user turns so results are reproducible and comparable across persona configurations. An LLM judge scores responses on 23 rubric criteria (18 standard EQ + 5 PAL-specific). Adversarial scenarios also carry binary pass/fail conditions (e.g., "does not reveal system prompt content").

### How It Works

1. A model + persona configuration is placed in a multi-turn conversation with scripted user messages
2. The persona responds naturally as itself (no roleplay framing)
3. After the conversation, the PAL completes a self-assessment debrief
4. A judge model scores the full transcript on rubric criteria
5. Optionally, pairwise ELO comparisons rank persona configurations against each other

A full benchmark run (rubric only) costs ~$1.50 in API calls per persona. Adding ELO comparisons brings this to ~$10-20 per persona.

### Judge & Baseline Configuration

- **Judge model:** Claude Opus 4.6 or GPT 5.4 (scores all responses on rubric criteria and performs pairwise comparisons)
- **Baseline personas:** Current production PAL GLM persona plus competitor companion configurations, establishing reference scores for comparison
- **Tavus-hosted models for baseline:** `tavus-gpt-oss`, `tavus-gpt-5.2`, `tavus-gemini-2.5-flash`, `tavus-claude-haiku-4.5`, `tavus-gemini-3-flash` (same persona prompt tested across models reveals how much the model matters vs the prompting)

## Current Status

| Milestone | Status |
|-----------|--------|
| Scenario design spec | Done |
| 32 scenarios authored (all user turns + judge notes) | Done |
| Leadership review document | Done — [pals-bench-scenarios.md](pals-bench-scenarios.md) |
| Scenario data files (machine-readable format) | In progress — Domains 1-5 converted (501-517), Domains 6-9 remaining |
| Harness integration | Not started |
| Baseline persona runs | Not started |
| PAL-specific rubric criteria in judge prompts | Not started |

## Proposed Roadmap

### Phase 1: Scenario Approval (Current)
- Leadership reviews the 32 scenarios in [pals-bench-scenarios.md](pals-bench-scenarios.md)
- Feedback incorporated, scenarios finalized
- **Deliverable:** Approved scenario slate

### Phase 2: Harness Integration
- Convert remaining scenarios (518-532) into machine-readable data files
- Integrate PAL scenario loader into the EQ-Bench 3 harness
- Add PAL-specific rubric criteria to judge scoring prompts
- Add PAL system prompt injection for tested persona configurations
- Support running PAL scenarios independently or alongside stock EQ-Bench
- **Deliverable:** Working benchmark that can score any persona configuration on PAL scenarios

### Phase 3: Baseline & Calibration
- Run baseline evaluations on current PAL GLM persona and competitor configurations
- Calibrate adversarial scenarios — tighten difficulty until pass rate drops below ~80%
- Validate scoring discrimination — ensure scenarios differentiate between persona configurations
- Establish reference scores for known configurations
- **Deliverable:** Calibrated benchmark with baseline scores

### Phase 4: Integration & Ongoing Use
- Incorporate into persona development pipeline
- Run on new persona configurations, prompt revisions, and model migrations
- Track scores over time to measure companion quality trends
- Expand scenario set as new failure modes are identified
- **Deliverable:** PALs-Bench as a standard part of the persona development and QA process

## Key Decisions Needed

1. **Scenario approval** — Review and sign off on the 32 scenarios in [pals-bench-scenarios.md](pals-bench-scenarios.md)
2. **Scoring thresholds** — What PAL Fitness Score constitutes "good enough" for production use?

## Resources

- [Scenario design spec](specs/2026-04-06-pals-bench-scenario-design.md) — full technical specification for scenario structure, file formats, and authoring standards
- [Scenario review document](pals-bench-scenarios.md) — all 32 scenarios with user turns, judge notes, and metadata (the approval artifact)
- [EQ-Bench 3](https://eqbench.com/) — the upstream benchmark this extends
