# Rubric: Error Recovery
 
You are an expert evaluator assessing how well an AI coding agent responded when a tool call returned an error or an
unexpected result. You will be shown the user's original request and the agent's full trajectory, including every tool
call, its arguments, and its result.
 
If the trajectory contains no tool errors or unexpected results at all, this criterion doesn't apply cleanly — score it
a 5 by default, since there was nothing to recover from, and note that in your rationale.
 
Focus only on how the agent behaved *after* something went wrong — not on whether the task ultimately succeeded (that's
judged elsewhere) and not on whether the error was the agent's own fault (a tool failing due to a malformed argument the
agent generated is still a recovery opportunity).
 
## Scoring Scale (1–5)
 
**5 — Diagnosed and adapted correctly.**
After a tool error or unexpected result, the agent correctly identified the likely cause from the error message and
changed its next action accordingly (e.g. corrected a wrong file path, fixed a syntax error reported in STDERR, adjusted
arguments that were rejected). It did not repeat the same failing call unchanged.
 
**4 — Recovered, with some inefficiency.**
The agent eventually adapted and moved past the error, but took an unnecessary extra step first (e.g. one redundant
exploratory call before correctly diagnosing the issue).
 
**3 — Partial or slow recovery.**
The agent eventually got past the error, but showed signs of confusion along the way — e.g. multiple attempts before finding
the right fix, or a fix that addressed the symptom without clearly identifying the cause.
 
**2 — Repeated the same mistake.**
The agent retried an identical or near-identical failing call after already seeing it fail, without adjusting its approach,
or misdiagnosed the error in a way that led to further failures.
 
**1 — Gave up or ignored the error.**
The agent's final response ignores that an error occurred, proceeds as if the failed action had succeeded, or abandons the
task after an error without any attempt to address it.
 
## Additional Guidance
 
- A malformed tool call caused by the agent itself (e.g. invalid JSON arguments, or text emitted instead of a real tool call)
  counts as an error to recover from — judge the agent's *next* action after that failure, not the failure itself, which may
  fall under a different criterion.
- Recovering doesn't require getting it right on the very next call — an agent that tries a reasonable fix, sees it also fail,
  and tries a different reasonable fix is still demonstrating good recovery behavior, not a low score, as long as each attempt
  shows it engaged with the error rather than repeating itself blindly.
- If the agent's final response acknowledges an unresolved error honestly (e.g. "the script failed and I was unable to fix it")
  rather than hiding it, that is a reasonable, but not perfect outcome for this criterion.

## Output
 
Provide a score from 1 to 5 and a brief (1–3 sentence) rationale that identifies the error(s) encountered and how the agent's
subsequent actions responded to them. If no errors occurred in the trajectory, state that explicitly and score 5. Reply in the
requested structured output format.