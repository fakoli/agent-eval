# Visual Systems

Systematic approaches to typography, spacing, color, and hierarchy.

## Typography Systems

### Modular Scales

Use mathematical ratios to generate harmonious type sizes:

| Ratio | Name | Value | Use Case |
|-------|------|-------|----------|
| Minor Second | 1.067 | Subtle | Dense interfaces |
| Major Second | 1.125 | Moderate | Body-heavy content |
| Minor Third | 1.200 | Balanced | General purpose |
| Major Third | 1.250 | Noticeable | Marketing/editorial |
| Perfect Fourth | 1.333 | Strong | Headlines focus |
| Perfect Fifth | 1.500 | Dramatic | Display typography |
| Golden Ratio | 1.618 | Classical | Traditional design |

**Application**: Choose base size (typically 16px), multiply/divide by ratio for scale steps.

### Typography Gotchas

- **Arbitrary sizes**: Using 14px, 18px, 22px, 27px without systematic relationship
- **Too many sizes**: More than 6-8 distinct sizes creates visual noise
- **Center-aligned body text**: Harder to read than left-aligned
- **Poor line length**: Aim for 45-75 characters per line
- **Insufficient line height**: Body text typically needs 1.4-1.6 line height
- **Ignoring vertical rhythm**: Line heights and spacing should share mathematical relationships

## Spacing Systems

### The 8-Point Grid

All spacing uses multiples of 8px:
- 4px (half-unit for tight spacing)
- 8px (base)
- 16px, 24px, 32px, 48px, 64px, etc.

**Why 8**: Divisible by 2 and 4; works well with common screen densities; creates consistent rhythm.

### Space Concept Taxonomy (Curtis)

| Type | Description | Example |
|------|-------------|---------|
| **Inset** | Padding inside containers | Card padding |
| **Stack** | Vertical spacing between elements | Paragraph margins |
| **Inline** | Horizontal spacing between elements | Button icon + label |
| **Grid** | Gutters and margins in layouts | Column gaps |

### Spacing Gotchas

- **Magic numbers**: Using arbitrary values (13px, 27px) instead of systematic ones
- **Inconsistent relationships**: Same semantic relationships with different spacing
- **Packed designs**: Insufficient whitespace; everything competing for attention
- **Unrelated measurements**: Typography, spacing, and layout using incompatible systems

## Color Systems

### Color Token Architecture

**Tier 1 - Primitive/Base Tokens** (raw values):
```
blue-500: #3B82F6
gray-100: #F3F4F6
```

**Tier 2 - Semantic Tokens** (meaning):
```
color-primary: {blue-500}
color-background-subtle: {gray-100}
color-text-error: {red-600}
```

**Tier 3 - Component Tokens** (context):
```
button-primary-background: {color-primary}
alert-error-text: {color-text-error}
```

### Color Gotchas

- **Testing in isolation**: Colors appear different in context
- **Insufficient contrast**: WCAG AA requires 4.5:1 for normal text, 3:1 for large text
- **Color alone for meaning**: Always pair color with text/icons for colorblind users
- **Too many colors**: Limit palette; use tints/shades of core colors
- **No dark mode consideration**: Design color system for both modes from start

## Visual Hierarchy

### Hierarchy Mechanisms

In order of strength:
1. **Size**: Largest draws eye first
2. **Color/Contrast**: High contrast attracts attention
3. **Position**: Top-left (in LTR) has natural priority
4. **Weight**: Bold vs. regular creates emphasis
5. **Whitespace**: Isolation draws attention
6. **Density**: Dense areas read as "more"

### Hierarchy Gotchas

- **Everything emphasized**: When everything is bold/colored, nothing stands out
- **Competing focal points**: Multiple elements fighting for primary attention
- **Flat hierarchy**: No clear reading order; user doesn't know where to look
- **Inconsistent patterns**: Same importance levels styled differently across views

## Layout Principles

### Gestalt Principles

- **Proximity**: Elements close together perceived as related
- **Similarity**: Similar elements perceived as grouped
- **Continuity**: Eye follows lines and curves
- **Closure**: Mind completes incomplete shapes
- **Figure-Ground**: Distinguish foreground from background

### Layout Gotchas

- **Breaking proximity**: Related items spaced apart; unrelated items close
- **Arbitrary alignment**: Elements not sharing alignment points
- **Inconsistent grids**: Different pages using different underlying structures
- **Ignoring fold**: Placing critical content where users must scroll without indication
