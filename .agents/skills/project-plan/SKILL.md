---
name: project-plan
description: Plan implementation from a request or brainstorm results; order work by dependencies, identify affected files, and define how to verify each acceptance criterion.
---

# Plan

Apply section 2 of the [workflow](../../../docs/WORKFLOW.md). Use
brainstorm results, a clear request, or the supplied task record. Do not
require another brainstorm when the available context is sufficient.

1. Check the goal and acceptance criteria against the project's actual
   structure, code, and commands. Record assumptions or unanswered
   questions that block implementation.
2. Order work by dependencies. Give each item an outcome and the files or
   components expected to change. Identify effects on existing behavior.
3. Map each criterion to verification. Record main scenarios, edge cases,
   necessary regression checks, commands, working directories, and
   required data/environment.
4. Prepare human test scenarios with initial conditions, actions, and
   expected results. Include recovery steps when changes pose data risks.

Use the [task template](../../../docs/templates/TASK.md) for tasks with
multiple steps if no record exists. Update an existing record instead of
duplicating it. The output is an actionable checklist and a verification
plan tied to acceptance criteria.

When invoked independently, create or update only the plan and task
documentation. Within the full workflow, hand over to Implement when no
blockers or user-requested plan approval remain.
