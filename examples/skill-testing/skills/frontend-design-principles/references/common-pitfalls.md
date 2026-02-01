# Common Design Pitfalls

Gotchas practitioners commonly encounter, organized by domain.

## Meta-Pitfall: Designing for Yourself

The most common mistake across all domains: **designing for yourself or your technology rather than your users.** This manifests as:

- Jumping to screen design without defining the root problem
- Substituting stakeholder opinions for user research
- Treating edge cases as primary use cases
- Optimizing for the demo rather than daily use
- Assuming your expertise represents user expertise

## UX & Interaction Pitfalls

### Research & Discovery
- **No user research**: Relying on assumptions or stakeholder opinions
- **Wrong users**: Testing with colleagues instead of actual users
- **Leading questions**: Validating existing ideas rather than discovering needs
- **Feature focus**: Asking "what features do you want?" instead of understanding problems

### Mental Models
- **Implementation model exposed**: UI reflects database structure or API design
- **Expert blindness**: Assuming users understand domain jargon
- **Inconsistent patterns**: Same interaction working differently across screens
- **Breaking conventions**: Novel patterns where standards would work

### Cognitive Load
- **Too many choices**: Overwhelming users with options
- **Required recall**: Expecting users to remember across screens
- **Hidden state**: System status not visible
- **Mystery meat navigation**: Links/buttons that don't indicate destination

### Feedback
- **Silent failures**: Errors with no indication
- **Delayed feedback**: Actions without immediate response
- **Ambiguous states**: Is this loading, empty, or broken?
- **Unhelpful errors**: "An error occurred" with no actionable guidance

## Visual Design Pitfalls

### Typography
- **Too many fonts**: More than 2-3 font families creates noise
- **Arbitrary sizes**: No systematic scale; sizes chosen randomly
- **Poor line length**: Too wide (>75 chars) or too narrow (<45 chars)
- **Insufficient contrast**: Text hard to read against background
- **Center-aligned body**: Makes scanning difficult

### Spacing
- **Magic numbers**: 13px, 27px, 41px—no mathematical relationship
- **Inconsistent rhythm**: Same relationships with different spacing
- **Packed layouts**: No breathing room; everything competing
- **Unrelated systems**: Typography, spacing, layout using incompatible bases

### Color
- **Testing in isolation**: Colors appear different in context
- **Too many colors**: Palette sprawl without hierarchy
- **Color alone**: Relying only on color for meaning
- **Accessibility oversight**: Insufficient contrast ratios

### Hierarchy
- **Everything emphasized**: All bold, all colored = nothing stands out
- **Flat structure**: No clear reading order
- **Competing focal points**: Multiple elements fighting for attention
- **Inconsistent importance**: Same level styled differently across views

## Accessibility Pitfalls

### Mindset Pitfalls
- **Compliance-only**: Treating WCAG as checklist, missing user needs
- **Retrofit approach**: Addressing accessibility late
- **Design for, not with**: No disabled users in process
- **Single disability focus**: Only considering visual impairment
- **Disability simulations**: Non-disabled people using blindfolds instead of consulting disabled users

### Design Pitfalls
- **Low contrast**: Below 4.5:1 for normal text
- **Color dependence**: Using only color to convey state/meaning
- **Small targets**: Touch targets below 44x44px
- **No focus indicators**: Removing outlines without alternatives
- **Hover-only interactions**: Information only revealed on hover
- **Auto-playing media**: Sound or motion without user control
- **Time limits**: Auto-advancing without pause option

### Implementation Pitfalls
- **Missing alt text**: Images without descriptions
- **Decorative images with alt**: Non-functional images with verbose alt text
- **Poor heading structure**: Skipping levels or using for styling
- **Unlabeled forms**: Inputs without associated labels
- **ARIA overuse**: Using ARIA when semantic HTML would work
- **Keyboard traps**: Focus stuck in modals or components
- **Missing skip links**: No way to bypass repetitive navigation

## Design Systems Pitfalls

### Strategy
- **Project mindset**: One-time build instead of ongoing product
- **No defined purpose**: Building without clear problems to solve
- **Boiling the ocean**: Trying to systematize everything at once
- **Premature abstraction**: Generalizing before understanding patterns

### Governance
- **No ownership**: Unclear who makes decisions
- **No feedback loops**: Teams can't report issues
- **Contribution theater**: Accepting contributions but not reviewing them
- **Mandate without value**: Enforcing use rather than earning adoption

### Technical
- **Storybook = docs**: Playground isn't usage guidance
- **Over-engineering**: Components trying to do too much
- **Token chaos**: Inconsistent naming, no hierarchy
- **No versioning**: Breaking changes without migration support

### Adoption
- **Build it and they'll come**: No onboarding or support
- **Ignoring adoption metrics**: Not tracking actual usage
- **Documentation rot**: Docs don't match current implementation
- **Gap denial**: Pretending system covers cases it doesn't

## Warning Signs Checklist

When reviewing designs, watch for:

- [ ] Can you explain why each element exists?
- [ ] Does the visual hierarchy match content priority?
- [ ] Can you navigate everything by keyboard?
- [ ] Are interactive states (hover, focus, active, disabled) defined?
- [ ] Do error states exist and help users recover?
- [ ] Is spacing systematic or arbitrary?
- [ ] Does the design work at 200% zoom?
- [ ] Can you accomplish tasks without relying on color alone?
- [ ] Would a new user understand what to do first?
- [ ] Does the design match users' mental models or the system's?
