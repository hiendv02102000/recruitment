# AI prompt log

This log records user prompts available in this session. It does not reconstruct
earlier conversations. Automatic environment, open-page, and loaded-skill
metadata are excluded.

## Prompt 1

````text
# AGENTS.md instructions for C:\Users\dovan\recruitment

<INSTRUCTIONS>
# Repository working instructions

## Default workflow

When implementing features, fixing bugs, or changing behavior through the
full process, use [project-workflow](.agents/skills/project-workflow/SKILL.md)
to coordinate [docs/WORKFLOW.md](docs/WORKFLOW.md) in this order:

**Brainstorm → Plan → Implement → Code review → Test → Human test.**

Individual step skills are in `.agents/skills/`: `project-brainstorm`,
`project-plan`, `project-implement`, `project-code-review`, `project-test`,
and `project-human-test`. See the [workflow](docs/WORKFLOW.md) for invocation
examples and file paths.

- Use English for project documentation, skill instructions, task records,
  and explanations. Preserve the original language of verbatim prompt logs.
- If the user requests only one step or invokes a specific skill, perform
  only that step. Standalone Brainstorm/Plan stays within analysis and
  planning; standalone Code review/Test reports results and leaves source
  code unchanged.
- Read the request and the relevant challenge README, then run
  `git status --short` before editing. Preserve the user's existing changes.
- For tasks with multiple steps, copy the [task template](docs/templates/TASK.md)
  to `docs/tasks/<task-name>.md` to record decisions, progress, and verification
  evidence. For small changes, a brief record in the conversation is enough.
- Continue through automated verification when the request is clear. Ask
  only when missing information affects scope or correctness. Pause for
  brainstorm/plan approval only when the user requests it or a decision
  requires their input.
- Code review must read the diff and check acceptance criteria, rather than
  relying solely on passing tests.
- Report only tests actually run. If a check could not run, explain why and
  describe the impact; do not mark it as passed.
- Hand over human test scenarios with actions and expected results. Keep
  the status `AWAITING_HUMAN_TEST` until the user reports the outcome.
  Mark `DONE` only when acceptance criteria pass and no required fixes remain.
- Match verification to the change. For documentation changes, check
  content and links; mark application runtime checks `N/A` with a reason
  when they do not apply.
- Commit or push only when the user requests it.

## Recording AI prompts

- Record user prompts verbatim in [PROMPTS.md](PROMPTS.md) at the repository
  root, for both the full workflow and individual skills.
- Before ending each work turn, append new prompts visible in context that
  have not yet been recorded. Keep submission order and record each turn once.
- Preserve the original language, wording, Markdown, line breaks, spaces,
  and escape characters. Do not summarize, correct spelling, or rewrite prompts.
- Put numbering and notes outside code blocks. Use a code fence longer than
  any backtick sequence in the prompt so the content displays unchanged.
- Record only content the user actually sent. Exclude system/developer
  instructions, automatic metadata, reasoning, and assistant responses.
- Preserve existing entries. Do not reconstruct history outside the available
  context or claim the log covers conversations that cannot be accessed.

</INSTRUCTIONS>
````

## Prompt 2

````text
[$project-workflow](C:\Users\dovan\recruitment\\.agents\skills\project-workflow\SKILL.md) 
````

## Prompt 3

The user answered the task-selection question with:

````text
Implement the CSV aggregator challenge
````

## Prompt 4

````text
 applying a Hash Partitioning + Streaming Aggregation solution. You must ensure thread safety.
````

## Prompt 5

````text
current 'The full dataset completed in 171.95 seconds, using 30.13 MiB peak memory' and previous 'Processed 26,843,544 records in **104.58 seconds**, using **24.30 MiB peak memor** ', back code to previous
````

## Prompt 6

````text
commit
````

## Prompt 7

````text
Find solutions to reduce latency
````

## Prompt 8

````text
implement
````

## Prompt 9

````text
commit
````
## Prompt 10

````text
write script read csv streaming for record latency read file and recommend optimize
````

## Prompt 11

````text
use split(",") instead of csv.reader
````

## Prompt 12

````text
it faster or slower
````


## Prompt 14

````text
Try using `split` for parallel processing; if it doesn't result in better speed, skip it.
````

## Prompt 15

````text
Ensure thread safe for the data, and verify the results.
````



## Prompt 16

````text
commit
````

## Prompts 17

````text
Configure the CSV aggregator to use 4 workers by default and allow the worker count to be specified as a command-line argument.
````

## Prompt 18

````text
can be optimized ?
````

