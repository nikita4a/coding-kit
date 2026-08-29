---
name: dashboard-ui-review
description: Use after changing a dashboard UI or before presenting it as finished. Verifies the running surface across viewport sizes, interaction states, responsive layout, accessibility, data legibility, and browser errors using available browser or Playwright tools.
---

# Dashboard UI Review

Review the rendered dashboard, not only its source code. A dashboard is not ready until its important states and interaction paths work in the browser.

## Workflow

1. **Launch the real app.** Follow the project run instructions. Use the available browser/Chrome DevTools integration or Playwright. Do not substitute a source inspection for a rendered check.
2. **Capture representative viewports.** Inspect at 1440px, 1024px, 768px, and 375px wide, or the closest supported sizes. Check for clipped text, broken grids, page-level horizontal overflow, unreadable tables, and controls that become unreachable.
3. **Exercise existing interactions.** Test the primary navigation, date/period controls, filters, tabs, sorting, pagination, row or card actions, and dialogs that exist in the product. Confirm visible feedback and preserved context after each action.
4. **Check the state matrix.** Inspect loading, empty, error, stale/partial data, disabled or permission-limited actions, long labels, large numbers, negative values, and slow responses. Do not add fake states to the product; verify the states that the code supports.
5. **Run the accessibility pass.** Check landmarks and heading order, accessible names for controls, form labels, table headers, keyboard tab order, visible focus, focus management in dialogs, contrast, text alternatives, zoom/reflow, and `prefers-reduced-motion`. Use WCAG 2.2 as the baseline. Automated audits do not replace keyboard testing.
6. **Run the visual pass.** Verify hierarchy, alignment, spacing, token consistency, chart units/legends, status meaning, table readability, sticky elements, and whether decoration competes with the primary decision. Check the browser console for errors and failed requests.
7. **Report evidence.** Record viewport, interaction/state, observed result, and exact defect location. Fix only confirmed issues, then rerun the affected check. Claim completion only after the rerun is clean.

## Required review questions

- Can a user identify the primary status and next action without hunting?
- Are active filters, date range, units, comparison period, and data freshness clear?
- Does every important chart have labels and a non-color-only interpretation?
- Does the screen remain usable with keyboard, zoom, reduced motion, and narrow widths?
- Are error and empty states actionable rather than vague?
- Is the page calmer and clearer after the redesign, or merely more decorated?

## Evidence format

```text
Surface: <route or screen>
Viewport: <width × height>
Path/state: <interaction or data state>
Observed: <what actually happened>
Result: pass | defect
Location: <component, selector, or screenshot reference>
```

## References

- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- Chrome accessibility tooling: https://developer.chrome.com/docs/devtools/accessibility/reference
