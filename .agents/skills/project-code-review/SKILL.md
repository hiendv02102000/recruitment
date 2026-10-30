---
name: project-code-review
description: Review a specified diff or code change; identify bugs, regressions, and acceptance-criteria gaps, then report findings by impact.
---

# Code review

Apply section 4 of the [workflow](../../../docs/WORKFLOW.md). Determine the
requested review scope: the working diff, a commit, or specified code.
Read the acceptance criteria, the complete diff including new files, and
related code.

1. Check behavior against requirements. Examine error paths, edge cases,
   and regressions. Consider security, performance, and compatibility
   where relevant to the changes.
2. Assess test quality and whether tests can catch real failures. Passing
   tests do not replace reading the code.
3. For each finding, record the file/line, triggering scenario, impact,
   severity, and suggested resolution. Separate required fixes from
   optional improvements.
4. State the reviewed scope, reviewer/tool, verification limitations, and
   conclusion. If there are no findings, say so instead of inventing
   speculative issues.

Output a review report and update the Code review section of an existing
task record. The review pass reads and verifies while leaving source code
unchanged. When invoked independently, end with the report; fixes must be
within the user's request. In the full workflow, return findings to
Implement and review the fixes before advancing to Test.
