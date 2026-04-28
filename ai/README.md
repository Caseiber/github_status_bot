# Claude Code Project Development Toolkit

**Problem**: Claude Code is incredibly powerful but has critical limitations that derail projects:

- 🧠 **Context Loss**: Each new session starts from scratch, losing project history and decisions
- ⚙️ **Over-Engineering**: Claude naturally creates complex solutions when simple ones work better
- 📈 **Scope Creep**: Claude will happily build whatever you ask for without questioning necessity
- 🔀 **Inconsistent Patterns**: Without guidance, Claude uses different approaches across sessions
- 🧪 **Testing Gaps**: Claude focuses on making code work, not on real-world user validation

**Solution**: This toolkit provides systematic processes that work _with_ Claude Code's strengths while compensating for its limitations. Transform vague ideas into structured requirements, maintain context across sessions, and ensure every development session builds toward shipping working software that solves real user problems.

> **Note**: These prompts are optimized and tested specifically for Claude Code. The principles may apply to other AI development tools, but effectiveness is only verified with Claude Code.

## 📁 Toolkit Files

```
claude-code-project-toolkit/
├── README.md                           # This guide
├── development-guidelines.md           # Reference doc - copy into projects
├── prd-prompts/
│   ├── initial-prd-creation.md        # Conversation starter: idea → comprehensive PRD
│   └── prd-refinement.md              # Conversation starter: update PRDs based on feedback
├── task-generation/
│   └── prd-to-tasks.md                # Conversation starter: PRD → detailed task breakdown
└── claude-onboarding/
    └── onboarding-prompt-generator.md  # Conversation starter: PRD → project-specific onboarding prompt
```

## 🚀 Quick Start Guide

### **Setup: Choose Your Workflow**

**Option A: Claude Code Directory Access** (Recommended)

- Add the toolkit directory to your Claude Code session file access
- Reference files directly: "Analyze the `prd-prompts/initial-prd-creation.md` file and help me create a PRD"
- No copy-paste needed, always uses latest version

**Option B: Manual Copy-Paste**

- Copy prompt content from files and paste into any AI tool
- Works with any AI tool, not just Claude Code

### 1. **Create PRD** (30-60 minutes)

**Option A**: "Analyze `prd-prompts/initial-prd-creation.md` and help me create a PRD for my project"  
**Option B**: Copy `prd-prompts/initial-prd-creation.md` and paste into Claude Code

Answer questions about your project and get comprehensive PRD

### 2. **Generate Tasks** (20-40 minutes)

**Option A**: "Using `task-generation/prd-to-tasks.md`, break down my PRD into development tasks"  
**Option B**: Copy `task-generation/prd-to-tasks.md` and paste with your completed PRD

Get detailed task breakdown with priorities and timelines

### 4. **Setup Onboarding** (10-15 minutes)

**Option A**: "Using `claude-onboarding/onboarding-prompt-generator.md`, create an onboarding prompt for my project"  
**Option B**: Copy `claude-onboarding/onboarding-prompt-generator.md` and paste with your PRD

Answer follow-up questions and get customized onboarding prompt for your project

### 5. **Development Setup** (5 minutes)

- Copy `development-guidelines.md` into your project repository
- Save your generated onboarding prompt for daily use
- Start developing with systematic task completion!

## 📋 Best Practices

### **All files are conversation starters** - copy from file, paste into Claude Code, no editing needed

### **For PRD Creation**

- Be specific with concrete examples and measurable success criteria
- Focus on real user problems, not theoretical features
- Include Claude Code development considerations for rapid iteration

### **For Task Breakdown**

- Each task should be completable in 1-4 hours
- Include testing requirements alongside feature development
- Make dependencies clear and realistic
### **For Development**

- Follow `development-guidelines.md` to prevent over-engineering
- Test every feature by actually using it as intended
- Always use feature branches, never commit directly to main
- Maintain >90% test coverage with meaningful tests

### **For Onboarding**

- Regenerate onboarding prompts when project context changes
- Include enough context for effective development continuation
- Reference guidelines file rather than duplicating content

## 📚 Example Usage

### **New Dashboard Project**

1. PRD Creation (45 min) → Task Breakdown (30 min) → Onboarding Setup (15 min)
2. Copy development guidelines into project repo
3. Daily development using onboarding prompt for each Claude Code session

### **Existing Project Evolution**

1. PRD Refinement (20 min) with new requirements
2. Generate new tasks (15 min) for additional features
4. Regenerate onboarding prompt (10 min) with updated context

### **Team Handoff**

1. Ensure PRD and tasks are current
2. Verify onboarding prompt has complete project context
3. Share development guidelines with new team members

## 🔄 Maintenance

**Weekly**: Update task progress, refine estimates based on actual velocity  
**At Milestones**: Update PRD for scope changes, regenerate onboarding prompt  
**Continuously**: Document lessons learned, improve templates based on experience

## 📞 Support

**Using the Toolkit**: Start with Quick Start Guide, reference individual files for detailed usage  
**Improving the Toolkit**: Document successful adaptations, suggest improvements based on real project experience

---

**Goal**: Systematic, repeatable project success through structured planning and consistent Claude Code development practices.
