# Reusable development workflow

**Brainstorm → Plan → Implement → Code review → Test → Human test**

Use this workflow for features, bug fixes, and improvements in the
repository. Each step needs a clear output before the next step starts.
Match the level of detail to the task; keep small changes lightweight.

## How to use

Submit a request using this format:

```text
Apply docs/WORKFLOW.md to this request: <task description>.
Goal: <desired outcome>.
Constraints: <scope, technology, performance, or timing, if any>.
```

For tasks with multiple steps, copy `docs/templates/TASK.md` to
`docs/tasks/<task-name>.md`. Maintain that record throughout the task,
updating checklists and evidence as results become available. An unfilled
template is not evidence that a step is complete.

By default, the implementer proceeds from Brainstorm through Test without
waiting for approval. If the user asks to approve the approach or plan,
pause at that point for their response. Human test always requires the user
to perform the checks and report the outcome.

### Using skills

Skills are stored with the project in `.agents/skills/`. Invoke a step
independently or use `project-workflow` to coordinate the full process.

| Skill | Purpose |
| --- | --- |
| [project-workflow](../.agents/skills/project-workflow/SKILL.md) | Coordinate all six steps, resume tasks, and manage fix loops |
| [project-brainstorm](../.agents/skills/project-brainstorm/SKILL.md) | Clarify the problem, choose an approach, and define acceptance criteria |
| [project-plan](../.agents/skills/project-plan/SKILL.md) | Create an implementation checklist and verification plan |
| [project-implement](../.agents/skills/project-implement/SKILL.md) | Implement code, tests, and documentation according to the plan |
| [project-code-review](../.agents/skills/project-code-review/SKILL.md) | Review changes and report findings by impact |
| [project-test](../.agents/skills/project-test/SKILL.md) | Run technical checks and record results and evidence |
| [project-human-test](../.agents/skills/project-human-test/SKILL.md) | Prepare acceptance scenarios and record the user's confirmation |

Invocation examples for Codex CLI or the IDE extension:

```text
$project-workflow Build the CSV aggregation CLI required by the challenge.
$project-brainstorm Suggest a memory-efficient approach for processing a CSV of about 1GB.
$project-plan Create a plan from the agreed approach in docs/tasks/aggregator.md.
$project-implement Implement the plan in docs/tasks/aggregator.md.
$project-code-review Review the current changes against the acceptance criteria.
$project-test Run the relevant checks for the current changes.
$project-human-test Prepare instructions for me to acceptance-test the CLI.
```

The task path in these examples refers to a record created by the user or
the Plan step. An independently invoked skill ends at that step's output.
Standalone Code review and Test leave source code unchanged. In the full
workflow, findings return to Implement for fixes, followed by review and
testing again.

Codex reads repository skills from `.agents/skills/`. If a skill does not
appear, restart Codex. In ChatGPT, use `@` to select a skill where the
interface supports it. See [OpenAI Docs on skills](https://learn.chatgpt.com/docs/build-skills).

## 1. Brainstorm — Understand the problem and choose an approach

**Input:** The request and the project's current context.

- Read the README, relevant instructions, existing code, and Git status.
- Identify the problem, users, desired outcome, scope, and exclusions.
- Record assumptions, unanswered questions, and risks that could affect the result.
- Where there are meaningful alternatives, compare complexity, performance,
  maintainability, and risk. Choose an approach and explain why.
- Inspect the repository before asking questions. Ask only about uncertainties
  that could materially change the approach or acceptance criteria.

**Output / exit criteria:** A problem statement, scope, chosen approach, and
verifiable acceptance criteria, with no unanswered questions blocking the
plan. Criteria must describe specific behavior and results, rather than
simply saying that something "works well."

## 2. Plan — Break down the work and define verification

**Input:** The approach and acceptance criteria from Brainstorm.

- Create a checklist in dependency order.
- Identify files or components expected to change and effects on existing behavior.
- Map each acceptance criterion to code review, automated checks, or human test.
- Identify relevant main scenarios, edge cases, and invalid-input cases.
- Record verification commands, working directories, environment, and data.
  Use commands that actually exist in the project; if something is missing,
  identify the work needed to add it.
- Prepare human test scenarios with initial conditions, actions, and expected
  results. Add a recovery approach when changes pose data or compatibility risks.

**Output / exit criteria:** An implementation checklist and verification
plan specific enough to execute, with decisions requiring user input resolved.

## 3. Implement — Execute the plan

**Input:** The plan and defined scope.

- Complete the checklist using the project's existing structure and conventions.
- Keep changes focused on the request and preserve the user's existing work.
- Add meaningful behavior tests when needed to verify changed logic. Update
  documentation or configuration examples when usage changes.
- Run short checks during implementation as needed. The later Test step
  verifies the reviewed version.
- If an assumption proves incorrect or scope must expand, update Brainstorm
  and Plan before continuing the affected work.

**Output / exit criteria:** Implementation items are complete, the changes
are runnable, and the diff is ready for review.

## 4. Code review — Check the code against the requirements

**Input:** The implementation diff, plan, and acceptance criteria.

- Read all changes, including new files, together with related code.
- Check correctness, error paths, edge cases, clarity, and maintainability.
  Consider security, performance, and compatibility where relevant.
- Confirm that tests check expected behavior and can catch real failures.
- Record each finding with its location, impact, severity, and suggested
  resolution. Distinguish required fixes from optional improvements.
- Resolve required findings before advancing, then review the fixes.
  A separate self-review pass is acceptable; identify the reviewer or tool.
  For a standalone review request, report findings for handoff. Fixes belong
  to Implement when requested or when coordinating the full workflow.

**Output / exit criteria:** A review result and resolution status for each
finding. No required fixes remain. State explicitly if there were no findings.

## 5. Test — Verify the reviewed changes

**Input:** The reviewed version and verification plan.

- Run appropriate checks, such as formatting, static analysis, unit tests,
  integration tests, a build, or a CLI smoke test, depending on the change.
- Cover main scenarios, edge cases, and existing behavior at risk. Do not
  add automated tests by default for simple documentation changes.
- Record exact commands, working directories, data/environment, and actual
  results. Distinguish `PASS`, `FAIL`, `NOT_RUN`, and `N/A`, with reasons
  for checks not run or not applicable. An unavailable environment is not a pass.
- For code failures, return to Implement → Code review → Test for the affected
  scope. For incorrect requirements or plans, return to the corresponding step.

**Output / exit criteria:** Required checks pass with supporting evidence.
If required checks remain unrun, mark the task `BLOCKED` at Test and state
what is needed to continue. Human test scenarios may be shared for preparation,
but do not claim the Test step has passed.

## 6. Human test — User acceptance

**Input:** The tested version, run instructions, and acceptance scenarios.

- Hand over a description of the changes, environment setup, and planned scenarios.
- Give each scenario concrete actions and expected results for comparison.
- The user performs the checks, records actual results, and reports `PASS`
  or `FAIL`. For failures, collect reproduction steps, data, and relevant logs.
- Use `AWAITING_HUMAN_TEST` at handoff. AI must not infer that human test
  passed from automated test results.
- On failure, record the issue and return to the appropriate step. Review
  and retest affected changes, then ask the user to check them again.

**Output / completion criteria:** The user confirms the acceptance criteria
pass, no required fixes remain, and evidence is recorded. Then mark the task
`DONE`. Committing, pushing, or releasing are separate actions performed only
when the user requests them.

## States and fix loops

Main flow:

```text
BRAINSTORM → PLAN → IMPLEMENT → CODE_REVIEW → TEST → AWAITING_HUMAN_TEST → DONE
```

- Review finding: return to `IMPLEMENT`, then review again.
- Test failure: `IMPLEMENT → CODE_REVIEW → TEST`.
- Human test failure: return to the step responsible, then continue through
  the remaining steps.
- Changed requirements or assumptions: return to `BRAINSTORM` or `PLAN`,
  updating the relevant criteria and tests.
- Missing prerequisites: record `BLOCKED`, the current step, the reason,
  and the condition for resuming. Continue independent work if available.

## Applying the workflow to the CSV challenge

Check the specific requirements in the
[challenge README](../fv-sec-001-software-engineer-challenge/README.md).
When a task affects the data aggregator, consider these checks:

- Use a small dataset with manually calculated results to verify campaign
  totals, CTR, CPA, top 10 ordering, and exclusion of campaigns with zero
  conversions from the top CPA results.
- Cover empty or missing files, invalid schemas, malformed rows, zero
  denominators, and fewer than 10 campaigns. Define expected behavior first.
- For performance work, measure runtime and memory using suitable data.
  Claim full-dataset processing only after actually running it and recording
  the measurements.
- In human test, run the CLI using the instructions, open the output CSVs,
  and compare known values. Use commands for the implemented version;
  example commands in the challenge are not evidence that a command exists.
- When preparing an AI-assisted submission, record prompts verbatim in
  `PROMPTS.md` as directed by the challenge. Do not rewrite the original prompts.
