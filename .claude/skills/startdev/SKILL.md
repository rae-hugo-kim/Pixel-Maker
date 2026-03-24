---
name: startdev
allowed-tools: Read, Write, Edit, Bash(mkdir:*), Bash(git status:*), Bash(date:*), Bash(echo:*), Glob, Grep, Skill
argument-hint: <epic or task description>
description: Fresh start for implementation with mandatory TDD gates
---

# Startdev - Implementation with Mandatory Gates

## Goal

Start implementation with enforced TDD discipline. No shortcuts.

## Non-Negotiables

| Rule | Violation = STOP |
|------|------------------|
| **No code before test plan** | Gate 1 must pass |
| **No implementation before RED** | Failing test must exist first |
| **No "done" before checklist** | Gate 3 must pass |
| **No scope creep** | Only what's in the epic/task |
| **Discover, don't guess** | Find paths/commands from repo |

## Inputs

- `$ARGUMENTS`: What to implement
  - `"epic 4"` / `"epic4"` / `"에픽 4"` → find and read epic file
  - `"로그인 기능"` → use as task description
  - seed.yaml이 있으면 `$ARGUMENTS` 없이도 실행 가능

## Workflow with Mandatory Gates

### Phase 0: Context Setup
```
1. If long conversation exists, run /sum to save session context
2. Read CLAUDE.md
3. Read references/tdd_rules.md
```

### Phase 0.5: Seed Preflight

seed.yaml을 확인하고 유효성을 검증한다.

```
1. Read docs/harness/seed.yaml
2. 존재하면:
   - YAML 파싱 성공 확인
   - 필수 필드 9개 존재 확인 (version, status, goal, constraints,
     acceptance_criteria, out_of_scope, assumptions, risks, references)
   - acceptance_criteria >= 1개 확인
   - status가 draft 또는 approved 확인
   - 실패 시: "seed.yaml이 유효하지 않습니다. /kickoff를 먼저 실행하세요." 출력 후 중단
3. 없으면:
   - $ARGUMENTS에 epic 패턴이 있으면 → Phase 1 fallback으로 진행
   - 아무 입력도 없으면 → "/kickoff를 먼저 실행하세요." 출력 후 중단
```

### Phase 1: Understand

**seed.yaml이 있을 때 (우선):**
```
1. seed.yaml에서 추출:
   - [ ] Goal (goal 필드)
   - [ ] Acceptance criteria (acceptance_criteria)
   - [ ] Scope boundaries (out_of_scope)
   - [ ] Constraints (constraints)
   - [ ] Assumptions to verify (assumptions)
   - [ ] Risks to test (risks)
   - [ ] Reference files (references)
2. 보조 컨텍스트:
   - docs/harness/rubric-report.md → blocking issues 확인
   - docs/harness/kickoff-summary.md → 산문 맥락
3. Output: "## Task Understanding" summary
```

**seed.yaml이 없을 때 (fallback):**
```
1. Find epic file: Glob **/epic*<number>*.md
2. Extract:
   - [ ] User stories
   - [ ] Acceptance criteria
   - [ ] Scope boundaries (what's NOT included)
3. Output: "## Task Understanding" summary
```

**User confirmation required before proceeding.**

### audit.jsonl 기록

startdev 시작 시 `docs/harness/audit.jsonl`에 append:
```
{"ts":"<ISO>","event":"startdev_started","actor":"assistant","meta":{"seed_version":<N>,"seed_status":"<status>"}}
```

### ⛔ GATE 1: Test Plan (MANDATORY)

**Cannot proceed to implementation without this.**

```markdown
## Test Plan for: <task>

### Unit Tests
- [ ] Test case 1: <input> → <expected>
- [ ] Test case 2: <input> → <expected>

### Edge Cases
- [ ] Empty input
- [ ] Invalid input
- [ ] Boundary values

### Integration Tests (if applicable)
- [ ] <scenario>
```

Use `assets/test_plan_template.md` for full template.

**seed.yaml을 사용한 경우:**
- `acceptance_criteria`의 각 항목 → 최소 1개 테스트 케이스로 매핑
- `risks`의 각 항목 → 최소 1개 엣지 케이스 테스트로 매핑
- `assumptions` 중 코드로 확인 가능한 것 → 검증 테스트 후보

**Output test plan. Get user approval. Then proceed.**

### Phase 2: RED - Write Failing Test

```
1. Write FIRST test (smallest unit)
2. Run test → MUST FAIL
3. If test passes → STOP, test is wrong
4. Commit: "test: add failing test for <feature>"
```

**Show failing test output before proceeding.**

### Phase 3: GREEN - Minimal Implementation

```
1. Write MINIMUM code to pass the test
2. No extra features
3. No "while I'm here" improvements
4. Run test → MUST PASS
5. Commit: "feat: implement <feature>"
```

**Check against `references/anti_patterns.md` before proceeding.**

### Phase 4: TIDY - Clean Only What You Touched

```
1. Only files you modified
2. Only structural changes
3. Run tests → MUST PASS
4. Commit: "refactor: tidy <what>"
```

### ⛔ GATE 2: Cycle Check

Before next feature:
- [ ] Test exists and passes?
- [ ] Implementation is minimal?
- [ ] No scope creep?

**Repeat Phase 2-4 for each test case in the plan.**

### ⛔ GATE 3: Completion Checklist

**Cannot declare "done" without all checks passing.**

```markdown
## Completion Checklist

### Tests
- [ ] All planned tests implemented
- [ ] All tests passing
- [ ] Edge cases covered

### Code Quality
- [ ] No hardcoded values
- [ ] No TODO comments left
- [ ] No console.log / print debugging

### Scope
- [ ] Only requested features implemented
- [ ] No extra "improvements"
- [ ] Matches acceptance criteria

### Ready for Review
- [ ] Commits are atomic (one thing per commit)
- [ ] Commit messages are clear
- [ ] No merge conflicts
```

Use `references/implementation_checklist.md` for full checklist.

## Output Format

```markdown
## Implementation Complete

### Task
<what was implemented>

### Test Coverage
- Unit tests: N
- Edge cases: N
- All passing: ✓

### Commits
1. `abc1234` — test: ...
2. `def5678` — feat: ...
3. `ghi9012` — refactor: ...

### Checklist
- [x] All gates passed
- [x] No anti-patterns detected

### Next Steps
<if any follow-up needed>
```

## References (load as needed)

- `references/tdd_rules.md` — RED→GREEN→TIDY cycle details
- `references/implementation_checklist.md` — Full completion checklist
- `references/anti_patterns.md` — "대충 구현" detection
- `assets/test_plan_template.md` — Test plan template
- `docs/rules/seed_evolution_policy.md` — 구현 중 seed.yaml 수정 규칙
- `docs/glossary.yaml` — 프로젝트 용어집

## Patterns Applied

`constraints_first`, `explicit_output_schema`, `reason_act_loop`, `safety_guard`, `iteration_limit`
