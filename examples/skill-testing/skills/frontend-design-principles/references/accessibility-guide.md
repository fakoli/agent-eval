# Accessibility Guide

Principles and patterns for inclusive design.

## The Mismatch Framework (Holmes)

Disability is a **mismatched interaction** between person and environment. Three categories:

| Type | Duration | Examples |
|------|----------|----------|
| **Permanent** | Lifelong | Blind, deaf, one arm |
| **Temporary** | Recoverable | Cataract, ear infection, broken arm |
| **Situational** | Contextual | Distracted, loud environment, carrying baby |

**Design implication**: Solving for permanent disabilities creates solutions that benefit temporary and situational cases. Design for the edges; the middle benefits.

## Inclusive Design Principles

### Seven Principles (W3C/Watson)

1. **Provide comparable experience**: Equivalent, not identical
2. **Consider situation**: Design for varying contexts (bright sunlight, one-handed, distracted)
3. **Be consistent**: Patterns should be predictable
4. **Give control**: Let users choose how to interact
5. **Offer choice**: Multiple ways to accomplish tasks
6. **Prioritize content**: Core content and functionality should be most accessible
7. **Add value**: Accessibility features should enhance experience for all

### Process Principles

**"Nothing about us without us"**: Include disabled users as co-designers, not test subjects.

**Accessibility is outcome; inclusive design is process**: Technical compliance without consultation misses the point.

**Born accessible**: Design for accessibility from start; retrofits are expensive and inferior.

## WCAG Principles (POUR)

### Perceivable

| Guideline | Key Points |
|-----------|------------|
| Text alternatives | Alt text for images; decorative images get empty alt |
| Time-based media | Captions, transcripts, audio descriptions |
| Adaptable | Content works in different presentations (linearized, zoomed) |
| Distinguishable | 4.5:1 contrast for text; don't use color alone |

### Operable

| Guideline | Key Points |
|-----------|------------|
| Keyboard accessible | All functionality via keyboard; no keyboard traps |
| Enough time | Adjustable timing; pause/stop moving content |
| Seizures | No content flashing >3 times/second |
| Navigable | Skip links, descriptive headings, focus visible |

### Understandable

| Guideline | Key Points |
|-----------|------------|
| Readable | Language identified; abbreviations explained |
| Predictable | Navigation consistent; no unexpected context changes |
| Input assistance | Error identification, labels, error prevention |

### Robust

| Guideline | Key Points |
|-----------|------------|
| Compatible | Valid markup; name/role/value for custom controls |

## Common Accessibility Errors

### Design-Phase Errors

1. **Low contrast**: Text below 4.5:1 ratio (3:1 for large text)
2. **Color alone**: Using only color to convey information (errors, states)
3. **Small touch targets**: Below 44x44px minimum
4. **No focus indicators**: Removing outlines without replacement
5. **Complex interactions**: Requiring hover, drag, or multi-touch without alternatives
6. **Time limits**: Auto-advancing content without pause controls

### Implementation Errors

1. **Missing alt text**: Images without alternatives
2. **Poor heading structure**: Skipping levels; using for styling not structure
3. **Unlabeled form fields**: Inputs without associated labels
4. **Missing landmarks**: No nav, main, aside regions
5. **Improper ARIA**: Using ARIA when semantic HTML would work
6. **Keyboard traps**: Modal dialogs that can't be closed via keyboard
7. **Auto-playing media**: Sound without user initiation

### The Compliance Trap

**50% of WCAG-compliant sites still fail usability tests with disabled users.**

Compliance != Usability. Technical conformance can miss:
- Cognitive accessibility
- Actual user workflows
- Context-dependent needs
- Interaction quality

## Testing Approaches

### Automated Testing
- Catches ~30% of issues
- Good for: contrast, alt text presence, heading structure
- Misses: alt text quality, keyboard usability, cognitive issues

### Manual Testing
- Keyboard-only navigation
- Screen reader testing (VoiceOver, NVDA, JAWS)
- Zoom to 200%
- High contrast mode
- Reduced motion preference

### User Testing
- Include users with various disabilities
- Test with actual assistive technologies they use
- Observe real workflows, not just task completion

## Key Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| Color contrast | 4.5:1 (AA), 7:1 (AAA) | Readability for low vision |
| Touch target | 44x44px minimum | Motor impairment accessibility |
| Focus visible | Always | Keyboard navigation |
| Animation duration | <5s or user-controlled | Vestibular/cognitive |
| Reading level | Grade 9 or lower | Cognitive accessibility |
