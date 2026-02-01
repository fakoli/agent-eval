---
name: frontend-design-principles
description: Design reasoning and UX principles for frontend interfaces and design documentation. Use automatically for UI or frontend design work, and when explaining or critiquing design decisions, accessibility, or design system choices, or when the user mentions @frontend-design-principles.
---

# Frontend Design Principles

Use this skill to reason about the "why" behind design decisions. It complements implementation guidance by grounding choices in UX, visual, accessibility, and systems thinking.

## Quick Start

When asked to design, critique, or document a frontend UI:
1. Identify the primary domain (UX, visual, accessibility, systems)
2. Surface the most relevant principles
3. Explain why a principle applies and how it informs the decision
4. Acknowledge tradeoffs

## Core Meta-Principles

These principles transcend individual domains:

**Design is invisible when it works.** The goal is removing friction between users and their goals, not being noticed. Evaluate: "Does this call attention to itself or to the user's task?"

**Constraints enable creativity.** Limitations (mobile-first, accessibility requirements, brand guidelines) focus rather than restrict. Treat constraints as creative prompts.

**Systems thinking precedes component thinking.** The whole shapes the parts. Understand the ecosystem before designing individual elements.

**Process matters as much as outcome.** How work happens (inclusive design, iteration, testing) shapes what gets delivered.

## UX & Interaction Principles

**The Gulf of Execution & Evaluation** (Norman): Users bridge two gaps—from intention to action (execution) and from system state to understanding (evaluation). Good design minimizes both gulfs through clear affordances and feedback.

**Don't Make Me Think** (Krug): Every question mark adds cognitive load. Users satisfice (choose first reasonable option) rather than optimize. Reduce decisions, not clicks.

**Recognition Over Recall** (Nielsen): Make elements visible rather than requiring users to remember them. Menus beat command lines for novices.

**Jakob's Law**: Users spend most time on *other* sites. Leverage conventions; break them only with clear benefit.

**Mental Models Over Implementation Models** (Cooper): Interfaces should mirror how users think about tasks, not how systems work internally.

**Perpetual Intermediates**: Most users are neither beginners nor experts. Design must grow with users rather than optimizing for extremes.

For Nielsen's 10 Heuristics and detailed frameworks, see `references/evaluation-frameworks.md`.

## Visual Design Principles

**Data-Ink Ratio** (Tufte): Maximize ink representing actual information; minimize decoration. Applies beyond charts—every pixel should earn its place.

**Color is Relational** (Albers): The same hue appears different in different contexts. Test colors in context, not isolation.

**Typography Exists to Honor Content** (Bringhurst): Design subordinates to message. When in doubt, increase readability.

**Grids Enable, Not Constrain** (Muller-Brockmann): Grids create proportional relationships that guide attention. The grid is "an aid, not a guarantee."

**Modular Scales**: Use mathematical ratios (golden section 1.618, perfect fifth 1.5) for harmonious type sizes and spacing rather than arbitrary values.

**Visual Hierarchy Through Contrast**: Size, color, weight, and position create hierarchy. When everything screams for attention, nothing does.

For spacing systems, typography details, and hierarchy patterns, see `references/visual-systems.md`.

## Accessibility Principles

**Disability is a Mismatch** (Holmes): Disability exists at the intersection of person and environment—design creates mismatches, design can remedy them.

**The Persona Spectrum**: Permanent, temporary, and situational disabilities face the same design challenges. A permanently deaf person, someone with an ear infection, and someone in a loud bar all need captions.

**Solve for One, Extend to Many**: Design for permanent disabilities often benefits everyone (the curb cut effect).

**Accessibility is Outcome; Inclusive Design is Process** (Featherstone): You can achieve technical compliance without consulting disabled users, but process matters—it demonstrates values.

**Born Accessible** (Horton): Technology should be accessible from inception, not retrofitted. Retrofits are costly and produce inferior experiences.

**Design With, Not For**: Cast disabled users as co-designers, not test subjects. Disability simulations substitute poorly for consultation.

For WCAG principles, common errors, and testing approaches, see `references/accessibility-guide.md`.

## Design Systems Principles

**Build Systems, Not Pages** (Frost): Interface design creates interconnected components, not individual layouts. Atomic design (atoms → molecules → organisms → templates → pages) provides compositional thinking.

**A System is a Product Serving Products** (Curtis): Systems require ongoing investment, not one-time builds. They solve easy problems so products can solve hard ones.

**Functional vs. Perceptual Patterns** (Kholmatova): Distinguish what a component does from how it looks/feels. Both need systematic treatment.

**Design Tokens**: Separate raw values from semantic meaning. Base tokens (colors, sizes) feed semantic tokens (primary-action, error-state) enabling theming and systematic updates.

**Be Consistent, Not Uniform** (Hupe): Use same patterns for familiarity while acknowledging context. Consistency is outcome, not goal.

**Systems Can Scale Harm**: If systems industrialize decisions, they can also industrialize discrimination. Evaluate what you're scaling.

For governance models, token architecture, and pitfall patterns, see `references/design-systems-guide.md`.

## Applying Principles

When evaluating or creating designs:

1. **Identify the domain**: Is this primarily a UX problem, visual problem, accessibility problem, or systems problem? Often multiple.
2. **Surface the relevant principles**: Which concepts apply? Principles often tension against each other—that's where interesting design decisions live.
3. **Reason from principles**: Don't apply mechanically. Explain *why* a principle applies and *how* it informs the decision.
4. **Acknowledge tradeoffs**: Good design principles help articulate what you're trading off, not eliminate tradeoffs.

When critiquing designs, see `references/common-pitfalls.md` for domain-specific gotchas practitioners commonly encounter.

## Additional Resources

- Design evaluation frameworks: `references/evaluation-frameworks.md`
- Accessibility checklist and testing: `references/accessibility-guide.md`
- Visual system patterns: `references/visual-systems.md`
- Design systems details: `references/design-systems-guide.md`
- Common pitfalls checklist: `references/common-pitfalls.md`
- Thought leaders and citations: `references/thought-leaders.md`
