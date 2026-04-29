# PRD to Tasks Breakdown

Convert any PRD version into actionable development tasks with automatic version detection and systematic task tracking.

---

**PROMPT:**

Generate comprehensive task breakdown from my latest PRD version with appropriately versioned task file.

## Auto-Detection Process

### Step 1: Identify Latest PRD and Generate Matching Task File

- Scan planning/ directory: `prd.md`, `prd-v2.md`, `prd-v3.md`, etc.
- Use highest version number as source
- Generate matching task file:
  - `prd.md` (v1.0) → `planning/tasks.md`
  - `prd-v2.md` (v2.0) → `planning/tasks-v2.md`
  - `prd-v3.md` (v3.0) → `planning/tasks-v3.md`

### Step 2: Current Context

**Latest PRD File:**

```
[PASTE CONTENT OF HIGHEST VERSION PRD FILE]
```

**Existing Task Files:**

```
[LIST: tasks.md, tasks-v2.md, tasks-v3.md, etc. - note which exist]
```

**Recent Git Progress:**

```
[REVIEW RECENT COMMITS - identify completed features if relevant]
```

## Task File Generation

### Output Format: `planning/tasks-v[X].md`

```markdown
# [Project Name] - Development Tasks v[X]

**Generated from**: [PRD version] on [Date]
**Development Phase**: [MVP/Post-MVP/Enhancement]

## Quick Status Overview

| Epic        | Total Tasks | Completed | In Progress | Not Started |
| ----------- | ----------- | --------- | ----------- | ----------- |
| [Epic Name] | X           | 0         | 0           | X           |

**Last Updated**: [Date]

## Next Priority Tasks

1. **T001**: [Task name] - [Brief description]
2. **T002**: [Task name] - [Brief description]
3. **T003**: [Task name] - [Brief description]

## Epic Breakdown

### Epic E001: [Epic Name]

**Priority**: High/Medium/Low
**Dependencies**: [Prerequisites]

#### Feature F001: [Feature Name]

**User Story**: As [user], I want [capability] so that [benefit]

##### Task T001: [Implementation Task]

**Priority**: High/Medium/Low
**Effort**: [Hours/Complexity]
**Dependencies**: [Prerequisites]

**Acceptance Criteria**:

- [ ] [Specific requirement 1]
- [ ] [Specific requirement 2]
- [ ] [Specific requirement 3]

**Testing Requirements**:

- [ ] Unit tests written and passing
- [ ] Integration tests implemented
- [ ] Manual testing completed
- [ ] Playwright UI validation (if UI changes)

**Definition of Done**:

- [ ] All acceptance criteria met
- [ ] Code reviewed
- [ ] Tests passing >90% coverage
- [ ] Feature deployed and validated

**Git Workflow**:

- Branch: `feature/t001-[description]`
- Commits: `Task T001: [change description]`
- Completion: `Task T001: Mark as completed`

[Continue for all tasks...]
```

### Task Structure Requirements

#### Task Breakdown Rules

- Epic → Feature → Task → Acceptance Criteria
- Tasks completable in 1-4 hours
- Clear dependencies and priority order
- Specific, testable acceptance criteria
- Git workflow integration

#### Priority Order

1. Foundation/setup tasks first
2. Core features by user value
3. Enhancement features
4. Testing and deployment tasks

## Git Integration

### Development Workflow

```bash
# Generate new task file
git add planning/tasks-v[X].md
git commit -m "Generate tasks-v[X] from PRD v[X]"

# Task development
git checkout -b feature/t001-[description]
git commit -m "Task T001: [progress description]"
git commit -m "Task T001: Mark as completed"
```

### Task Completion Process

1. Complete all acceptance criteria
2. Update task checkboxes in task file
3. Commit completion: `Task T[ID]: Mark as completed`
4. Move to next priority task

## Output Requirements

**Generate**: `planning/tasks-v[X].md` (matching PRD version)
**Include**: Complete task breakdown with priorities and dependencies
**Format**: Ready for immediate development use
**Integration**: Git workflow and development guidelines compliant

---

**Next Step**: Use generated task file as development roadmap, starting with highest priority tasks.
