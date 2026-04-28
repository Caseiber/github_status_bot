# Onboarding Prompt Generator

Use this prompt to create a project-specific onboarding prompt for Claude Code sessions.

# Onboarding Prompt Generator

Use this prompt to create a project-specific onboarding prompt for Claude Code sessions.

---

**PROMPT:**

I need you to create a project-specific onboarding prompt for Claude Code development sessions. This prompt will be used to quickly bring new Claude Code instances up to speed on an ongoing project.

I'll provide you with the completed PRD for the project, and you'll extract the relevant information and ask me targeted questions to create a comprehensive onboarding prompt.

## Input: Project PRD

**Completed PRD:**

```
[PASTE YOUR COMPLETED PRD HERE]
```

## Your Process

### Step 1: Extract from PRD

From the provided PRD, automatically extract:

- **Project name and description**
- **Technology stack recommendations**
- **Architecture decisions and patterns**
- **Target users and core functionality**
- **MVP scope and development phases**
- **Key project principles and constraints**
- **UI/UX specifications** (if UI design phase was completed)

### Step 2: Ask Targeted Questions

Ask me specific questions about:

- **Repository details**: GitHub URL, current branch structure
- **Development environment**: Any setup specifics not covered in PRD
- **Current development phase**: Which tasks/features are you working on now
- **Git workflow preferences**: Branch naming, commit conventions, PR process
- **Team context**: Solo development vs team, any specific collaboration needs

### Step 3: Generate Complete Onboarding Prompt

Create a comprehensive onboarding prompt that includes:

#### Project Context Section

- Clear project overview with vision and current status
- Technology stack and architecture decisions
- Target users and core functionality summary
- Current development phase and immediate priorities

#### Development Workflow Section

- **Critical git workflow rules** (feature branches, never commit to main)
- **Testing and quality standards** (>90% coverage, manual testing approach)
- **Reference to development guidelines** (not duplication of content)
- **Key project principles** (MVP focus, user-centered testing, simplicity)

#### Getting Started Instructions

- Step-by-step process for continuing development
- Key files to read first (PRD, UI prototypes if available, task breakdown, guidelines)
- How to identify next tasks and track progress
- Integration notes for APIs, services, deployment

#### UI/UX Validation with Playwright Section

- **Setup instructions** for Playwright testing environment
- **Task agent delegation commands** for comprehensive UI/UX testing
- **Mobile-first testing protocols** with specified viewport requirements
- **Performance validation thresholds** and measurement approaches
- **Quality gates** that must pass before PR creation
- **Core user workflows** to test based on project requirements

#### Project-Specific Context

- File structure and organization conventions
- Common commands and development workflows
- Important environment setup or dependencies
- Any project-specific gotchas or considerations

## Output Format

Structure the generated onboarding prompt as a complete markdown document that can be saved and used directly for Claude Code sessions. 

**File Location**: Save as `planning/onboarding-prompt.md` to keep it organized with other project planning documents.

Include:

1. **Clear project header** with name and context
2. **Getting started checklist** for immediate orientation
3. **Development standards summary** with references to full guidelines
4. **Project-specific details** extracted from PRD and your answers
5. **Quick reference section** with commands, links, and key information

## Guidelines for Creation

- **Extract maximum context** from the PRD to minimize questions needed
- **Focus on actionable information** that Claude needs to continue development
- **Reference rather than duplicate** the development guidelines content
- **Include enough context** for effective development without being overwhelming
- **Make it scannable** with clear sections and bullet points
- **Include critical workflow reminders** to prevent common mistakes

Start by analyzing the PRD I provided, then ask your targeted questions to fill in the project-specific details needed for the onboarding prompt.
