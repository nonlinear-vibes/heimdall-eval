# Heimdall - AI Agent Evaluation Framework
 
Systematically evaluates coding-agent behaviour: runs an agent against
a battery of prompts across multiple LLMs, captures full execution 
trajectories, then scores those trajectories against rubrics using multiple
LLM judges.
 
This is a work in progress. This README describes the current state.
 
## Why evaluation
 
Most "which LLM is best" comparisons are single-shot, single-judge, and
opaque about failure modes. This project tries to do better on three fronts:
 
- **Full trajectories, not just final answers.** Every tool call, every
  reasoning trace, every iteration is logged — so a model that reports
  success without actually doing the work is distinguishable from one that
  actually succeeded.
- **Multiple judges per criterion.** Each trajectory is scored by more than
  one LLM per criterion, so judge disagreement itself becomes a measurable
  signal, not something hidden behind a single averaged score.
- **Human-in-the-loop sanity check.** A human evaluator scores a subset of
  trajectories on the same rubric, so judge alignment with human judgement
  can be checked directly rather than assumed.
  
## Project structure
 
Two independent sub-projects, connected only through a shared data layer —
deliberately: the agent and the evaluator have no code dependency on each
other, only a shared file format.
 
```
repo/
├── agent/           # runs the coding agent against models × prompts
│   ├── config/       # models.yaml, prompts.yaml
│   ├── fixtures/      # starting files for prompts that need pre-existing state
│   └── ...
├── evaluator/         # scores trajectories using LLM judges (LangChain)
│   ├── config/          # criteria.yaml, judges.yaml
│   ├── rubrics/           # one .md rubric per criterion
│   └── ...
├── data/                    # shared interface — owned by neither sub-project
│   ├── logs/                  # <model_slug>/<prompt_id>.jsonl — raw trajectories
│   ├── evals/                   # <model_slug>/<prompt_id>/<criterion_id>_<judge_id>.json
│   │   └── human_evals/            # one .yaml per human evaluator
│   ├── eval.db                       # SQLite index, fully rebuildable from the above
│   └── build_db.py
└── README.md
```
 
Each sub-project has its own `pyproject.toml`/`uv.lock`/`.env` — different
dependencies (raw OpenAI SDK + Docker for the agent, LangChain + LangSmith
for the evaluator), different lifecycles, no shared imports.
 
## How it works
 
### 1. Agent harness (`agent/`)
 
The agent is a tool-using coding assistant (file read/write/list, Python
execution — optionally sandboxed in Docker) built directly on the OpenAI SDK
against OpenRouter. `harness.py` sweeps every `(model, prompt)` pair defined
in `config/models.yaml` and `config/prompts.yaml`:
 
- Each prompt gets a fresh, isolated workspace, optionally seeded from a
  `fixtures/` directory (for tasks like "find the bug in this existing
  script").
- Every LLM call and tool call is logged as structured JSON Lines to
  `data/logs/<model_slug>/<prompt_id>.jsonl` — durations, token usage,
  reasoning text, tool call arguments/results, and the exit condition
  (finished normally, hit the iteration cap, or errored).
- The sweep is resumable: a run already ending in a completed
  `"Run complete"` event is skipped; partial/corrupted logs from a crash are
  cleared and retried.
### 2. Evaluator (`evaluator/`)
 
For every trajectory, and for every `(criterion, judge)` pair defined in
`config/criteria.yaml` / `config/judges.yaml`, the evaluator:
 
- Builds a judge-facing view of the trajectory that deliberately excludes
  identifying details (model name, token counts, timing) to reduce
  judge self-preference bias, and includes only what a given criterion's
  rubric actually needs.
- Calls the judge model via LangChain (`with_structured_output`, backed by a
  Pydantic schema) to get a numeric score + rationale, traced to LangSmith
  for observability.
- Writes the result to `data/evals/<model_slug>/<prompt_id>/<criterion_id>_<judge_id>.json`,
  same resumability pattern as the agent side.
Rubrics live as standalone Markdown files (`evaluator/rubrics/`), used as
each judge's system prompt.
 
### 3. Human evaluation
 
A human evaluator can score any trajectory on the same criteria by hand,
recorded in `data/evals/human_evals/<evaluator_id>.yaml`. This is the
ground truth used to check how well the LLM judges track human judgment.
 
### 4. SQLite index (`data/build_db.py`)
 
Files (JSON/JSONL/YAML) are the source of truth throughout this project —
the database is a derived, disposable index, not a second copy of the data.
Running `build_db.py` wipes and rebuilds `data/eval.db` from scratch:
reference tables from the YAML configs, `runs`/`iterations`/`tool_calls`
from the logs, `evaluations` and `human_evals` from the eval outputs. Safe
to delete and regenerate at any time.
 
## Notable findings so far
 
- Free-tier models are already surfacing real, useful failure modes without
  any adversarial prompting — e.g. one model consistently emits its
  intended tool call as markdown text inside its response instead of using
  the actual tool-calling API field, which the harness correctly logs as a
  non-tool-use trajectory rather than crediting it as task completion.
- The same category of failure (plausible-looking natural-language output
  instead of a strictly-formatted response) shows up on the judge side too
  — a model that reliably makes tool calls as an agent has, in testing,
  failed to produce valid structured JSON output as a judge, and vice versa.
  This suggests structured-output reliability doesn't transfer cleanly
  between different invocation mechanisms (tool-calling vs. schema-forced
  JSON), even within the same model.
## Status / not yet done
 
- Only a small number of test prompts and free-tier models have been run
  end-to-end so far, mainly to validate the pipeline.
- The full ~40-50 prompt set and the final model/judge lineup (paid models
  for the real dataset) haven't been run yet.
- No analysis layer yet (inter-judge disagreement metrics, human-vs-judge
  alignment, reporting) — the database schema supports these queries, but
  the analysis scripts themselves haven't been written.
