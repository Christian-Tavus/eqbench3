# PALs-Bench Cheat Sheet

Quick reference for running PALs-Bench companion persona evaluations.

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys in .env
TEST_API_KEY=sk-or-v1-...       # Model being tested
TEST_API_URL=https://openrouter.ai/api/v1/chat/completions
JUDGE_API_KEY=sk-or-v1-...      # Judge model (can be same key)
JUDGE_API_URL=https://openrouter.ai/api/v1/chat/completions
```

---

## Common Commands

### Score a persona (rubric only, fastest)
```bash
python eqbench3.py \
  --pals \
  --pal-persona persona.json \
  --test-model google/gemini-2.5-flash \
  --judge-model anthropic/claude-opus-4-6 \
  --no-elo
```

### Score a persona with ELO ranking
```bash
python eqbench3.py \
  --pals \
  --pal-persona persona.json \
  --test-model google/gemini-2.5-flash \
  --judge-model anthropic/claude-opus-4-6 \
  --ignore-canonical
```

### A/B test two persona prompts
```bash
# Run variant A
python eqbench3.py --pals --pal-persona persona_v1.json \
  --test-model google/gemini-2.5-flash \
  --judge-model anthropic/claude-opus-4-6 --ignore-canonical

# Run variant B (same model, different prompt)
python eqbench3.py --pals --pal-persona persona_v2.json \
  --test-model google/gemini-2.5-flash \
  --judge-model anthropic/claude-opus-4-6 --ignore-canonical
```

### Test a persona across models
```bash
python eqbench3.py --pals --pal-persona persona.json \
  --test-model google/gemini-2.5-flash \
  --judge-model anthropic/claude-opus-4-6 --no-elo

python eqbench3.py --pals --pal-persona persona.json \
  --test-model anthropic/claude-haiku-4-5 \
  --judge-model anthropic/claude-opus-4-6 --no-elo
```

### Run PAL + stock EQ-Bench together
```bash
python eqbench3.py --include-pals --pal-persona persona.json \
  --test-model google/gemini-2.5-flash \
  --judge-model anthropic/claude-opus-4-6
```

### Resume a failed/interrupted run
```bash
python eqbench3.py --pals --pal-persona persona.json \
  --test-model google/gemini-2.5-flash \
  --judge-model anthropic/claude-opus-4-6 \
  --run-id <run-id-prefix> --no-elo
```

### Re-score with a different judge
```bash
python eqbench3.py --pals --pal-persona persona.json \
  --test-model google/gemini-2.5-flash \
  --judge-model anthropic/claude-opus-4-6 \
  --run-id <run-id-prefix> --redo-rubric-judging --no-elo
```

---

## Persona Input Formats

### Tavus persona JSON (recommended)
```json
{
  "persona_name": "Sage",
  "persona_id": "p_abc123",
  "system_prompt": "You are Sage, a warm companion...",
  "greeting": "Hey there! How's your day going?",
  "layers": { "llm": { "model": "tavus-gemini-2.5-flash" } },
  "context": "User prefers morning check-ins."
}
```
- `persona_name` used in run identity and leaderboard
- `greeting` injected as first assistant message
- `context` appended to system prompt

### Plain text (also works)
```
You are Sage, a warm and supportive companion...
```
- Persona name derived from filename (e.g. `sage_v2.txt` -> `sage_v2`)
- No greeting injection

### Per-session context (optional)
```bash
--pal-context context.txt
```
Appends contents to the system prompt, simulating Tavus `conversational_context`.

---

## Output

### Scores (0-100 scale)

| Score | Band | Meaning |
|-------|------|---------|
| 80-100 | Excellent | Strong persona, natural conversation, solid guardrails |
| 60-79 | Good | Mostly on-character, minor lapses |
| 40-59 | Fair | Noticeable issues, breaks character or weak redirects |
| 20-39 | Poor | Frequent failures, generic assistant-speak |
| 0-19 | Failing | Fundamentally broken persona |

### What gets scored

| Criterion | Applies To | What It Measures |
|-----------|-----------|-----------------|
| persona_fidelity | All | Consistent character, no assistant-speak |
| objective_progression | All | Advances companion purpose naturally |
| gricean_cooperation | All | Conversational efficiency and relevance |
| guardrail_adherence | Scenarios with guardrails | Respects boundaries when tested |
| refusal_quality | Adversarial only | Warm, clear, relationship-preserving "no" |

### Adversarial pass/fail
16 adversarial scenarios (IDs 518-532 + some in 514-517) carry binary pass conditions.
Reported as e.g. `13/16 passed`.

---

## CLI Reference

| Flag | Description |
|------|-------------|
| `--pals` | PAL scenarios only (501-532) |
| `--include-pals` | PAL + stock EQ-Bench scenarios |
| `--pal-persona PATH` | Persona file (required with --pals/--include-pals) |
| `--pal-context PATH` | Per-session context file (optional) |
| `--test-model MODEL` | API model ID for the tested model |
| `--model-name NAME` | Custom label (default: "PersonaName (model)") |
| `--judge-model MODEL` | Judge model for scoring |
| `--no-elo` | Skip ELO pairwise analysis |
| `--no-rubric` | Skip rubric scoring |
| `--iterations N` | Run each scenario N times (default: 1) |
| `--threads N` | Parallel threads (default: 4) |
| `--run-id ID` | Custom run ID prefix (for resume) |
| `--redo-rubric-judging` | Re-score all tasks (resets errors too) |
| `--reset-model` | Wipe all local data for this persona/model |
| `--ignore-canonical` | Don't load canonical leaderboard |
| `--pals-elo-results-file` | Custom PAL ELO file (default: pals_elo_results.json) |

---

## Typical Costs (OpenRouter)

| Step | ~Cost per run |
|------|--------------|
| Conversations (32 scenarios) | $0.50-2.00 (depends on test model) |
| Rubric scoring (32 scenarios) | $1.50-3.00 (depends on judge model) |
| ELO pairwise (optional) | $10-20 |

---

## Tips

- Use `--no-elo` for fast iteration during prompt development
- Use `--ignore-canonical` when comparing your own personas (skip leaderboard models)
- Adversarial failures (527-529 pattern) usually mean the persona prompt needs stronger guardrails for subtle social harm
- Low `objective_progression` on adversarial scenarios is normal — the persona is correctly prioritizing safety over task advancement
- Run 2-3 iterations for production confidence; single iteration is fine for development
