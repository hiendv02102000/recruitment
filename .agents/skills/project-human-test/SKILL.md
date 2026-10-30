---
name: project-human-test
description: Prepare manual acceptance instructions or record human test results reported by the user; complete a task only after confirmation that acceptance criteria passed.
---

# Human test

Apply section 6 of the [workflow](../../../docs/WORKFLOW.md). Use the
acceptance criteria, reviewed/tested version, and planned scenarios. When
receiving feedback, check earlier confirmations in the conversation to
avoid asking the user to confirm the same result again.

1. Identify the version to test using a commit if available, or a diff
   description and run instructions. Record setup, data, and known limitations.
2. Map scenarios to criteria with initial conditions, actions, expected
   results, and space for actual results. Prefer actions the user can
   perform directly.
3. If required technical checks passed, hand over with
   `AWAITING_HUMAN_TEST`. If required review/test evidence is missing, state
   that and keep `BLOCKED` at the relevant step; share scenarios only for
   preparation.
4. When the user reports results, record who confirmed them, the version,
   their response, and the time if available. Use actual feedback; do not
   infer human acceptance from automated tests or fill in responses for
   the user.
5. On failure, record reproduction steps and unmet criteria for a fix
   handoff. Mark `DONE` only when all criteria pass, prior steps have
   sufficient evidence, and no required fixes remain. Later changes that
   affect results need the corresponding review, tests, and acceptance
   repeated.

Update the Human test section of an existing task record. When invoked
independently, end with acceptance instructions or recorded results. The
full workflow coordinates fix loops. Writing instructions does not complete
human test, and acceptance does not authorize committing, pushing, or releasing.
