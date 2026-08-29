---
name: dashboard-design
description: Use when redesigning or building marketplace, seller, operations, finance, logistics, or analytics dashboards. Defines information hierarchy, KPI summaries, filters, charts, tables, design tokens, responsive behavior, and loading/empty/error states without decorative dashboard clutter.
---

# Dashboard Design

Design dashboards as decision tools, not collections of cards. Improve the existing product with the smallest coherent visual system and preserve domain terminology that users already recognize.

## Use when

- Redesigning a marketplace or back-office dashboard
- Reworking KPI cards, charts, filters, tables, navigation, or detail panels
- Improving visual hierarchy, density, responsive behavior, or empty states

## Do not use when

- The task is only backend, data modeling, or query optimization
- The user asks for a poster, presentation, logo, or static illustration

## Workflow

1. **Inspect before proposing.** Read the existing routes, components, tokens, data shape, and current UI. Reuse existing primitives and terminology; do not invent metrics or controls that the product cannot support.
2. **Name the primary decision.** State who uses the dashboard, what they need to decide, and the three to five questions the screen must answer. Remove elements that do not support those questions.
3. **Set information hierarchy.** Put the primary status and action first, then KPI context, trend or comparison, details, and secondary actions. Keep filters and the active period visible. Use a table when exact values or row-level actions matter.
4. **Define a compact visual system.** Prefer the existing design tokens. If none exist, define semantic tokens for surface, text, muted text, border, success, warning, danger, accent, spacing, type scale, radius, and elevation. Components must consume tokens instead of scattered raw colors.
5. **Design every meaningful state.** Cover loading, no data, error, stale or partial data, disabled/permission-limited actions, and long labels or numbers. Keep the layout stable and explain the next useful action.
6. **Make charts answer one question.** Show units, time range, comparison context, labels or a legend, and an accessible text/table alternative when the chart carries meaning. Never communicate important differences through color alone.
7. **Handle responsive behavior intentionally.** Check desktop, tablet, and mobile layouts. Stack or reprioritize content before shrinking it. Allow horizontal scrolling only for genuinely wide data tables; never let the whole page overflow. Keep keyboard focus visible and respect reduced-motion preferences.
8. **Critique before implementation.** Remove one decorative element, one redundant label, and any card, chart, or animation that does not improve comprehension or actionability.

## Dashboard defaults

- Start with three to six primary KPIs only when each supports a real decision.
- Keep number formats, units, decimal precision, and positive/negative conventions consistent.
- Make status meaning explicit with text, iconography, and color where appropriate.
- Prefer sentence-case labels and action verbs such as `Export`, `Filter`, `View details`, and `Resolve`.
- Do not use gradients, glass effects, excessive pills, emoji icons, or uniform rounded cards as decoration.
- Do not turn every metric into a chart; a clear number, comparison, or table may be better.
- Preserve existing product patterns unless there is a documented reason to change them.

## Output before coding

Write a short design decision list:

- primary user and decision;
- retained, moved, and removed content;
- layout hierarchy;
- token or component changes;
- state and responsive behavior;
- one risk to verify in the running UI.

Then implement only that plan. For a new or ambiguous flow, use a separate discovery/brainstorming skill before changing code.
