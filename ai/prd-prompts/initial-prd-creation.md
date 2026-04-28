# Initial PRD Creation Prompt

Use this prompt to generate a comprehensive Product Requirements Document (PRD) from initial project ideas.

---

**PROMPT:**

You are an experienced product manager creating a comprehensive Product Requirements Document (PRD) for a new project.
Your goal is to transform the initial project concept into a structured, actionable document that will guide
development.

## Project Information to Analyze

**Raw Project Concept:**

```
We want to create a Slack bot that determines if GitHub is down. It should check this using Github's own status page
(https://www.githubstatus.com/) and by checking the Down Detector (https://downdetector.com/status/github/) to see if
Github's reported errors are above the baseline. We want to be able to reference this bot in a channel by tagging it
`@github_status_bot`, and get a text response indicating if it is down. It should also say which source it referenced 
(whether Github's own page or Down Detector). If it is down, it should tell us roughly how long it has been down for.
```

**Goals & Success Metrics:**

| Goal                       | Success Metric                                                                      | Target                          |
|----------------------------|-------------------------------------------------------------------------------------|---------------------------------|
| Slackbot is created        | We have a slackbot that meets the criteria laid out in the project concept          | All criteria met                |
| No false alarms            | When tagged, the bot only says Github is down if one of the sources said that it is | 0 false alarms                  |
| Speaks if spoken to        | The bot only sends a message when tagged, and only sends the one message.           | 0 unrequested or extra messages |
| References the listed URLs | The bot actually checks the URLs and provides up to date and accurate data          | 0 fake or assumed answers       |

**Component Responsibility Matrix:**

| Component | Responsibility |
|-----------|----------------|
| **Slack** | Hosts the bot  |

**Project Constraints:**

## PRD Structure to Follow

Create a comprehensive PRD with these sections:

### 1. Executive Summary

- **Project Name & Version**: Clear project identification
- **Date & Status**: Current date and development phase
- **Vision Statement**: One sentence describing the ultimate goal
- **Success Metrics**: 3-4 measurable outcomes that define success

### 2. Problem Statement

- **Current Pain Points**: Specific problems this project will solve
- **Target User Personas**: Detailed description of primary, secondary, and tertiary users
- **Market Opportunity**: Why this problem is worth solving now

### 3. Product Requirements

#### Core Functionality (MVP)

- Break down features into specific, testable requirements
- Focus on essential features that deliver core value
- Include acceptance criteria for each major feature

#### Advanced Features (Future Phases)

- Phase 2 and Phase 3 feature sets
- Clear dependency relationships between phases
- Rough effort estimates for future planning

### 4. Technical Architecture

- **Technology Stack Recommendations**: Specific technologies with rationale
- **Integration Strategy**: How components will work together
- **API Design**: Key endpoints and data flows
- **Security & Performance Requirements**: Non-functional requirements

### 5. Claude Code Development Considerations

#### Strengths to Leverage

- What Claude Code excels at for this type of project
- Development velocity advantages
- Quality assurance benefits

#### Development Strategy Adaptations

- **Requirements Precision**: How to provide detailed specifications
- **Test-Driven Development**: Testing approach and coverage goals
- **Continuous Feedback**: How to gather and incorporate feedback
- **Technology Stack Optimizations**: Best tools for Claude Code development

### 6. User Stories & Acceptance Criteria

- **Epic-level stories** organized by major functionality
- **Detailed user stories** with specific acceptance criteria
- **Edge cases and error scenarios** to consider

### 7. Implementation Roadmap

- **Phase 1 (MVP)**: Week-by-week breakdown with specific deliverables
- **Phase 2**: Enhanced features and timeline
- **Phase 3**: Production-ready improvements
- **Risk mitigation strategies** for each phase

### 8. Definition of Done

- **MVP Ready Criteria**: Specific, testable completion requirements
- **Technical Performance Standards**: Measurable performance targets
- **Integration & Deployment Standards**: Deployment and compatibility requirements
- **Code Quality Standards**: Testing, documentation, and maintainability requirements
- **User Validation**: How success will be measured with real users

### 9. Success Criteria & Metrics

- **Development Velocity Metrics**: How to measure development progress
- **Quality Assurance Standards**: Testing and reliability targets
- **User Experience Metrics**: How users will benefit from the solution

### 10. Risk Assessment

- **Technical Risks**: Development and integration challenges
- **Product Risks**: User adoption and market fit concerns
- **Mitigation Strategies**: Specific plans to address each risk

## Instructions for Creation

1. **Ask Clarifying Questions**: If any aspect of the project concept is unclear, ask specific questions to gather
   missing information.

2. **Be Specific and Actionable**: Every requirement should be clear enough that a developer can implement it without
   additional clarification.

3. **Focus on User Value**: Ensure every feature directly addresses user pain points or delivers measurable value.

4. **Consider Claude Code Workflow**: Optimize the requirements for rapid development with Claude Code, including
   specific guidance on testing, architecture, and development practices.

5. **Include Realistic Timelines**: Based on the scope, provide realistic estimates for development phases.

6. **Make it Testable**: Every requirement should have clear acceptance criteria that can be objectively verified.

## Questions to Address

Before writing the PRD, please ask any clarifying questions about:

- **User personas**: Who exactly will use this product?
- **Core value proposition**: What's the primary problem being solved?
- **Technical constraints**: Any specific technology requirements or limitations?
- **Success definition**: How will we know this project succeeded?
- **Scope boundaries**: What is explicitly NOT included in this project?

Please analyze the project concept provided and create a comprehensive PRD following this structure. Start by asking any
necessary clarifying questions, then proceed with the complete document.

## Output Requirements

**Save the completed PRD as**: `planning/prd.md`

- Create the planning/ directory if it doesn't exist
- Use git for version control instead of filename versioning
- This will be the single source of truth for project requirements
