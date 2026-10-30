---
name: project-implement
description: Implement a feature or bug fix from an existing plan; update code, tests, and necessary documentation to produce a diff ready for code review.
---

# Implement

Apply section 3 of the [workflow](../../../docs/WORKFLOW.md). Read the plan
and acceptance criteria from the task record or conversation, along with
instructions for the affected component. Clarify only missing decisions
that affect the implementation.

1. Check Git status, identify the user's existing changes, and preserve
   them throughout implementation.
2. Follow the checklist in dependency order and use existing conventions.
   Keep the diff focused on the requested scope.
3. Add behavior tests when needed to verify changed logic. Update usage
   instructions and configuration examples when the interface or run
   commands change. For simple documentation edits, use appropriate
   content and link checks.
4. Run necessary short checks while implementing and record actual
   results. If assumptions prove incorrect or scope must change, update
   the plan and criteria before continuing the affected work.

Output the implemented diff, completed plan items, checks actually run,
and remaining issues. Update the Implement section of the task record
if one exists.

When invoked independently, hand over the diff for Code review. Do not
mark review, testing after review, or human test as passed without evidence.
