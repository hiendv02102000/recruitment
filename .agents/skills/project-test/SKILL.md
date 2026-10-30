---
name: project-test
description: Run automated or technical checks for a change; verify acceptance criteria and regressions using actual commands, data, and recorded evidence.
---

# Test

Apply section 5 of the [workflow](../../../docs/WORKFLOW.md). Read the
acceptance criteria, verification plan, available review results, and
actual project configuration. For an independent test request, state the
scope and any unknown review status; do not claim a review has passed.

1. Select the smallest meaningful checks for the change: static analysis,
   unit/integration tests, a build, a CLI smoke test, or documentation checks.
2. Cover main scenarios, edge cases, and existing behavior at risk. Use
   data with known expected results to verify correctness. Draw performance
   conclusions only from actual measurements on described data.
3. Record commands, working directories, data/environment, actual results,
   and evidence. Use `PASS`, `FAIL`, `NOT_RUN`, or `N/A`, explaining checks
   not run or not applicable. An environment failure is not a pass.
4. Classify failures as implementation, requirements, or environment issues.
   State the next action and checks to rerun. Update the Test section of an
   existing task record.

Output a verification report and any missing prerequisites. When invoked
independently, leave source code unchanged and report results without
starting fixes. In the full workflow, code failures return to
Implement → Code review → Test. Hand over to Human test only when required
checks pass. If blocked, record `BLOCKED` at Test and what is needed to resume.
