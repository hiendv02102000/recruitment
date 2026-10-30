---
name: project-workflow
description: Coordinate the full development process through Brainstorm, Plan, Implement, Code review, Test, and Human test; use to execute or resume the complete project workflow.
---

# Project workflow

Read the [shared workflow](../../../docs/WORKFLOW.md) and current request.
For tasks with multiple steps, use the
[task template](../../../docs/templates/TASK.md) to create
`docs/tasks/<task-name>.md`, or continue the existing record.

## Selecting and resuming a step

Read the `SKILL.md` for the step when it is needed:

| Step | Skill | Task record status |
| --- | --- | --- |
| Brainstorm | [project-brainstorm](../project-brainstorm/SKILL.md) | `BRAINSTORM` |
| Plan | [project-plan](../project-plan/SKILL.md) | `PLAN` |
| Implement | [project-implement](../project-implement/SKILL.md) | `IMPLEMENT` |
| Code review | [project-code-review](../project-code-review/SKILL.md) | `CODE_REVIEW` |
| Test | [project-test](../project-test/SKILL.md) | `TEST` |
| Human test | [project-human-test](../project-human-test/SKILL.md) | `AWAITING_HUMAN_TEST` |

Each step receives the previous step's output. When resuming, choose the
step from evidence in the task record and conversation. Check that earlier
results still apply to the current version before reusing them. A recorded
status or checklist without results does not prove a step has passed.

## Coordination

1. Follow all six steps in order. Proceed from Brainstorm through Test
   when requirements are clear. Wait for approach/plan approval only when
   the user asks or a decision requires their input.
2. For required review findings, return to Implement and then review again.
   For code test failures, follow Implement → Code review → Test. If
   requirements or assumptions are incorrect, return to Brainstorm/Plan
   and update the relevant criteria and scenarios.
3. If prerequisites are missing, record `BLOCKED`, the current step, the
   reason, and the condition for resuming. Continue independent work if
   available; do not repeat blocked commands without a change in conditions.
4. Once required checks pass, hand over to Human test with
   `AWAITING_HUMAN_TEST` and wait for the user's results. On failure,
   coordinate fixes and repeat affected checks. Mark `DONE` only after
   confirmation and satisfaction of the workflow's completion criteria.

If the user requests only one step, read that step's skill and stay within
the requested scope instead of running the entire sequence. Coordinate
steps sequentially in the working session; separate agents are not required.
