# Evaluation Frameworks

Reference material for systematic design evaluation.

## Nielsen's 10 Usability Heuristics

Use these for heuristic evaluation of interfaces:

1. **Visibility of System Status**: Keep users informed through timely feedback. Users should never wonder "did that work?"

2. **Match Between System and Real World**: Use familiar language and concepts. Follow real-world conventions; information appears in natural order.

3. **User Control and Freedom**: Provide clear exits. Support undo/redo. Users often choose functions by mistake.

4. **Consistency and Standards**: Follow platform conventions. Same words/actions should mean same things throughout.

5. **Error Prevention**: Design to prevent errors before they occur. Eliminate error-prone conditions; provide confirmation for risky actions.

6. **Recognition Rather Than Recall**: Minimize memory load. Make options visible; don't require users to remember across dialog steps.

7. **Flexibility and Efficiency of Use**: Accelerators for experts (invisible to novices). Allow users to tailor frequent actions.

8. **Aesthetic and Minimalist Design**: Every extra unit of information competes with relevant information. Remove unnecessary elements.

9. **Help Users Recognize, Diagnose, and Recover from Errors**: Error messages in plain language. Precisely indicate problem; constructively suggest solution.

10. **Help and Documentation**: Best if system needs no documentation, but provide help focused on user's task with concrete steps.

## Garrett's Five Planes of UX

Decisions cascade—each plane constrains those above:

1. **Strategy**: User needs + business objectives
2. **Scope**: Features and content requirements
3. **Structure**: Interaction design + information architecture
4. **Skeleton**: Interface design, navigation, information design
5. **Surface**: Visual design (sensory experience)

Evaluate whether problems stem from the right plane—surface fixes can't solve structure problems.

## Walter's Hierarchy of User Needs

Design must satisfy lower levels before higher ones provide value:

1. **Functional**: Does it work?
2. **Reliable**: Does it work consistently?
3. **Usable**: Can users accomplish goals without frustration?
4. **Pleasurable**: Does it create positive emotional response?

Delight without reliability creates worse experience than reliable without delight.

## Cooper's Goal-Directed Evaluation

Ask of any interface element:
- What user goal does this serve?
- Does this reflect the user's mental model or the implementation model?
- Would a perpetual intermediate understand this?

## Accessibility Quick Evaluation (POUR)

WCAG's four principles:

- **Perceivable**: Can all users perceive the content? (alt text, captions, contrast)
- **Operable**: Can all users operate the interface? (keyboard, timing, navigation)
- **Understandable**: Can all users understand content and operation? (readable, predictable, input assistance)
- **Robust**: Does content work with assistive technologies? (parsing, name/role/value)

## Design System Health Check

Evaluate systems against:
- **Adoption**: Are teams actually using it?
- **Contribution**: Can teams extend it effectively?
- **Documentation**: Does documentation match implementation?
- **Governance**: Is there clear ownership and decision-making?
- **Evolution**: Is the system actively maintained?
