# Design Systems Guide

Principles and patterns for creating and maintaining design systems.

## Atomic Design (Frost)

Compositional hierarchy for thinking about interfaces:

| Level | Description | Examples |
|-------|-------------|----------|
| **Atoms** | Basic building blocks | Buttons, inputs, labels, icons |
| **Molecules** | Simple groups of atoms | Search field (input + button), form field (label + input + error) |
| **Organisms** | Complex, distinct sections | Header, card, comment thread |
| **Templates** | Page-level layouts | Content placement without real content |
| **Pages** | Templates with real content | Actual instances users see |

**Key insight**: This is a mental model, not a linear process. Design moves fluidly between levels.

## Token Architecture

### Three-Tier Token System

**Tier 1: Primitive Tokens** (raw values)
```
color-blue-500: #3B82F6
space-4: 16px
font-size-md: 16px
```

**Tier 2: Semantic Tokens** (meaning/purpose)
```
color-primary: {color-blue-500}
color-background-surface: {color-gray-50}
space-component-padding: {space-4}
```

**Tier 3: Component Tokens** (specific contexts)
```
button-primary-background: {color-primary}
card-padding: {space-component-padding}
```

### Token Naming Principles

- **Describe purpose, not appearance**: `color-error` not `color-red`
- **Consistent taxonomy**: `{category}-{property}-{variant}-{state}`
- **Predictable patterns**: Once you know one, you can guess others

## Governance Models (Curtis)

| Model | Description | Best For |
|-------|-------------|----------|
| **Centralized** | One team owns system | Small orgs, early stages |
| **Federated** | Shared ownership across teams | Medium orgs, mature systems |
| **Distributed** | Community-driven | Large orgs, platform ecosystems |

### Contribution Patterns

**Warning**: "Contributions as a solution to speed? Such a false promise." (Curtis)

Contributions work when:
- Clear submission criteria exist
- Review process is defined
- Feedback loops are fast
- Documentation shows how

Contributions fail when:
- System team is bottleneck
- Quality standards are unclear
- No one knows how to contribute
- Submissions sit in review indefinitely

## Pattern Types (Kholmatova)

### Functional Patterns
What component **does**:
- A button submits forms
- A modal focuses attention
- A toast provides feedback

### Perceptual Patterns
How component **feels**:
- Brand alignment
- Emotional tone
- Visual language

Both need systematic treatment. Functional patterns without perceptual patterns feel generic. Perceptual patterns without functional patterns become inconsistent.

## Effective Design Principles

Principles must be **actionable**. Test: Does this help a designer make a decision?

**Weak principles** (too vague):
- "Be simple"
- "User-friendly"
- "Modern and clean"

**Strong principles** (decision-enabling):
- "When in doubt, prioritize clarity over cleverness"
- "Progressive disclosure: show essentials first, details on demand"
- "Error prevention over error recovery"

Strong principles specify tradeoffs and help resolve competing concerns.

## Common Design System Pitfalls

### Strategic Pitfalls

1. **Project vs. Product mindset**: Systems need ongoing investment, not one-time builds
2. **No defined purpose**: Building components without clear problems to solve
3. **Too much too fast**: Trying to systematize everything immediately
4. **Consistency as goal**: Consistency is outcome, not objective; it can scale harm

### Technical Pitfalls

1. **Storybook != Documentation**: Component playground isn't usage guidance
2. **Over-engineering**: Premature abstraction; components that do too much
3. **Token chaos**: Inconsistent naming, no clear hierarchy
4. **No versioning**: Breaking changes without migration paths

### Organizational Pitfalls

1. **Siloed handoffs**: Design -> Dev waterfall instead of collaboration
2. **No feedback loops**: Teams can't report issues or suggest improvements
3. **Missing leadership support**: No organizational investment
4. **Documentation rot**: Docs don't match implementation

### Cultural Pitfalls

1. **Treating as finished**: Systems evolve; "done" is a myth
2. **Ignoring adoption**: Building without ensuring teams actually use it
3. **Enforcing compliance**: Mandating use rather than providing value
4. **Scaling harm** (Hupe): "If design systems can become vectors for harm... we industrialize discrimination"

## System Health Metrics

| Metric | Healthy | Unhealthy |
|--------|---------|-----------|
| Adoption rate | Growing or stable | Declining |
| Time to first use | Days | Weeks/months |
| Contribution rate | Active | No contributions |
| Documentation currency | Updated with releases | Stale, inaccurate |
| Bug report response | Fast resolution | Growing backlog |
| Component coverage | Fits team needs | Major gaps |

## Hot Potato Process (Mall/Frost)

Eliminate designer -> developer handoff:

1. Ideas pass **quickly** between designer and developer
2. Prototypes emerge from collaboration, not specification
3. Both roles shape the output
4. Reduces bottlenecks and miscommunication

**Principle**: "Rather than aiming for massive impact that takes awhile, focus on the incremental wins. The smaller success stories cultivate adoption faster."
