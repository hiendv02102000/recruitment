# Task: <task name>

> Copy to `docs/tasks/<task-name>.md`, replace placeholders, and update using
> actual results. Check off a step only when its exit criteria in the
> [workflow](../WORKFLOW.md) are met.

- Status: `BRAINSTORM`
- Implementer: <name>
- Human tester: <name or not yet assigned>
- Scope / challenge: <directory or component>
- If blocked: <step, reason, condition for resuming, or none>

## 1. Brainstorm

- [ ] Brainstorm complete

**Original request:** <description or link>

**Problem and goal:** <who needs what and the desired outcome>

**In scope:** <work to be done>

**Out of scope:** <work not included>

**Assumptions / questions / risks:** <details and resolution status>

**Approach and rationale:** <compare alternatives when meaningful tradeoffs exist>

| ID | Acceptance criterion | Verification method |
| --- | --- | --- |
| AC-01 | <specific behavior and expected result> | <review / test case / human test> |

## 2. Plan

- [ ] Plan complete

| Order | Work item | File / component | Dependencies |
| --- | --- | --- | --- |
| 1 | <work item> | <path> | <none or preceding item> |

**Verification plan:** <main scenarios, edge cases, regression, commands, and working directories>

**Environment / data:** <setup instructions and prerequisites>

**Recovery if needed:** <procedure or N/A with a reason>

Fill in the Human test scenarios in section 6 before implementation.

## 3. Implement

- [ ] Implementation complete

**Changes made:** <files, behavior, and rationale>

**Deviations from the plan:** <details and reasons, or none>

## 4. Code review

- [ ] Code review complete; no required fixes remain

**Reviewer / tool:** <name; identify self-review if applicable>

**Reviewed scope:** <diff, new files, and related code>

| Location | Finding and impact | Severity / required fix? | Resolution / follow-up review |
| --- | --- | --- | --- |
| <file:line> | <description> | <severity / yes or no> | <result> |

If there are no findings, remove the example row and state the review conclusion.

## 5. Test

- [ ] Required checks passed

| Criterion / test case | Command or check | Directory / data / environment | Result | Evidence / reason |
| --- | --- | --- | --- | --- |
| <AC-01 / test case> | <actual command> | <execution context> | <PASS / FAIL / NOT_RUN / N/A> | <actual result or reason> |

**Remaining issues:** <issue, impact, and resolution approach, or none>

## 6. Human test

- [ ] Instructions delivered; status is `AWAITING_HUMAN_TEST`
- [ ] User confirmed that all acceptance criteria passed

**Version tested:** <commit if available, or version / diff description>

**Setup:** <environment, data, and run instructions>

| ID / criterion | Actions | Expected result | Actual result | PASS / FAIL / PENDING |
| --- | --- | --- | --- | --- |
| HT-01 / AC-01 | <concrete steps> | <observable result> | <filled in by the user> | PENDING |

**Feedback / reproduction steps:** <details or not yet received>

**User confirmation:** <who, when, and what they confirmed, or not yet confirmed>

## Completion

- [ ] The steps above meet their exit criteria; no required fixes remain
- [ ] User confirmation of human test is recorded
- [ ] Status is `DONE`

**Handoff result:** <changes, successful checks, and remaining limitations>
