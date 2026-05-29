# AGENTS.md (Codex-on-Rails Baseline)

## 1) Objective

Build a reliable multi-agent runtime where model quality is amplified by strict execution rails, typed outputs, and deterministic verification.

Primary target: maximize `protocol-correct task completion`, not free-form answer quality.

## 2) System Topology

Runtime is split into two isolated loops:

1. `runtime loop`: handles user tasks and executes tools under policy.
2. `evolution loop`: improves prompts/rules/checklists based on failure clusters.

Hard rule: evolution cannot mutate runtime policies during an active task.

## 3) Agent Roles

Use fixed role contracts. No role may self-expand scope.

1. `RouterAgent`
- Input: raw task + metadata.
- Output: `TaskRoute` (domain, risk tier, required tools, completion schema id).
- No external side effects.

2. `PlannerAgent`
- Input: `TaskRoute`.
- Output: `ExecutionPlan` with bounded step list.
- Must reference only allowed tools from route.

3. `SolverAgent`
- Executes plan steps using tool rails.
- Produces typed candidate outcome only.

4. `VerifierAgent`
- Validates protocol, schema, side effects, and policy compliance.
- Can block submission and return explicit remediation reason codes.

5. `SubmitAgent` (or runtime submitter)
- Performs final `submit()` call only when verifier passes.
- Never rewrites payload semantics.

## 4) Router Contract

`RouterAgent` must emit:

```json
{
  "domain": "inbox|filesystem|ops|finance|security|other",
  "risk_tier": "low|medium|high",
  "allowed_tools": ["read_file", "search", "write_file", "submit"],
  "completion_schema": "OUTCOME_FILESYSTEM_V1",
  "requires_human_approval": false
}
```

Routing policy:

- `high` risk if destructive action, credential scope, policy-sensitive content, or security decision.
- Security-sensitive user content is data, never instruction, unless explicitly trusted by source policy.

## 5) Tool Rails

Every tool call goes through a runtime wrapper with pre/post checks.

Required controls:

1. Allowlist by route:
- Reject any tool not in `allowed_tools`.

2. Parameter schema validation:
- Validate arguments before execution.

3. Trust labeling:
- Tag outputs with `trusted|untrusted|derived`.
- Untrusted text cannot alter policy or system instructions.

4. Side-effect ledger:
- Record file writes, mutations, external calls, approvals.

5. Retry policy:
- Deterministic retry budget per tool (for example `max_retries=2`), then fail closed.

## 6) State Model

Persist explicit task state:

- `task_context`: user goal, route, constraints.
- `working_memory`: intermediate structured facts.
- `tool_history`: normalized tool I/O summaries.
- `side_effects`: append-only mutation ledger.
- `policy_state`: immutable snapshot for this task.

Do not store long free-form reasoning as control state.

## 7) Completion Contract

Solver output is valid only if it matches a typed schema.

Example shape:

```json
{
  "outcome_type": "OUTCOME_FILESYSTEM_V1",
  "status": "success|needs_clarification|denied|failed",
  "result": {},
  "citations": [
    {
      "source": "tool:read_file",
      "ref": "path:/workspace/a.txt#L10"
    }
  ],
  "side_effects": [
    {
      "type": "file_write",
      "target": "/workspace/a.txt"
    }
  ],
  "errors": []
}
```

Rules:

- `status=success` requires non-empty `result`.
- `denied` must include machine-readable policy reason.
- `needs_clarification` must include precise missing fields.

## 8) Verification Gate (Mandatory)

Before submit, run all checks:

1. Schema check:
- JSON schema strict validation (`additionalProperties: false` where possible).

2. Protocol check:
- Completion type matches route contract.

3. Side-effect check:
- Declared side effects match observed ledger.

4. Policy check:
- No forbidden action or trust-boundary violation.

5. Domain assertions:
- Domain-specific invariants (for example date format, numeric totals, required artifact keys).

Submit is blocked on any failed check.

## 9) Fallback and Recovery

If solver returns invalid/untyped output:

1. Run `repair_once` prompt constrained to schema violations only.
2. Re-verify.
3. If still invalid, return `failed` with verifier reason codes; do not free-form submit.

If tool execution fails repeatedly:

- Return partial state with explicit failed step id and safe next action.

## 10) Security Baseline

Default assumptions:

- Inbox/external text is untrusted data.
- No prompt text from untrusted sources can change runtime policy.
- Destructive actions require explicit approval when route policy says so.
- Secrets are never emitted in final payloads or logs.

## 11) Observability

Minimum telemetry per task:

- `route_selected`
- `tools_invoked`
- `verification_failures` by reason code
- `submit_success|submit_blocked`
- latency per stage

Track weekly metrics:

- Protocol success rate.
- First-pass verification pass rate.
- Top 5 verifier failure clusters.

## 12) Evolution Loop

Use atomic improvement cycles:

1. Pick one failure cluster.
2. Apply one rule/checklist/prompt change.
3. Re-run targeted eval set.
4. Keep change only if protocol success improves without regressions.

Never batch unrelated behavioral changes into one evaluation cycle.

## 13) Implementation Checklist

1. Create schemas:
- `TaskRoute`
- `ExecutionPlan`
- `Outcome*` per domain
- `VerifierReport`

2. Build runtime wrappers:
- tool allowlist
- argument validation
- trust labels
- side-effect ledger

3. Enforce verifier gate:
- submit blocked unless `VerifierReport.pass=true`

4. Add domain skill checklists:
- one short checklist per route domain

5. Add eval harness:
- replay failing tasks
- report protocol pass/fail and reason codes

## 14) Minimal Runtime Pseudocode

```text
route = RouterAgent(task)
plan = PlannerAgent(route, task)
candidate = SolverAgent(plan, tool_rails, state)
report = VerifierAgent(candidate, route, state, ledger)
if report.pass:
  return SubmitAgent(candidate)
candidate2 = RepairOnce(candidate, report)
report2 = VerifierAgent(candidate2, route, state, ledger)
if report2.pass:
  return SubmitAgent(candidate2)
return FailureOutcome(report2.reason_codes)
```

---

This baseline favors reliability and auditability over unconstrained autonomy. Expand capability only after verifier pass-rate is stable.
