---
name: data-visualization
description: Use when designing or reviewing dashboard KPIs, charts, tables, trends, rankings, funnels, or marketplace analytics. Chooses honest visual forms, preserves metric context and units, handles dense data responsively, and keeps charts accessible and actionable.
---

# Dashboard Data Visualization

Make data easier to decide from, not merely more decorative. A visualization must preserve the meaning of the metric and answer a specific user question.

## Workflow

1. **Confirm the metric.** Find the source definition, unit, aggregation, scope, time zone, freshness, and comparison period. Never infer business meaning from a label or fabricate sample values in production code.
2. **Name the question.** Write the decision the visual supports. If there is no decision or comparison, prefer a clear value, status, or table over a chart.
3. **Choose the least complex form.** Use a KPI for a current value, a delta for comparison, a line for time series, bars for category comparison/ranking, a table for exact values or row actions, and a funnel only when stages and denominators are defined. Use maps, pies, gauges, and dual axes only when the data genuinely requires them.
4. **Keep context attached.** Show title, units, time range, scope, comparison basis, data freshness, and meaningful annotations near the visual. Do not make users hover to discover essential values.
5. **Use honest scales.** Use a zero baseline for bars unless a documented exception is clearer. Avoid distorted axes, unexplained smoothing, false precision, and truncated labels. Format numbers consistently and make negative/positive meaning explicit.
6. **Encode accessibly.** Do not rely on color alone. Add labels, patterns, symbols, or direct annotations where needed. Provide accessible names and a text/table alternative for meaningful charts. Preserve contrast and keyboard access for interactive legends and tooltips.
7. **Design states.** Cover loading, no data, insufficient data, error, stale/partial data, filtered results, and values outside the expected range. Explain what the user can do next.
8. **Check density and responsive behavior.** Keep small multiples and legends readable. On narrow screens, simplify or stack before shrinking text; use horizontal scrolling only for genuinely wide tables. Recheck long category names and large numbers.
9. **Verify against real values.** Compare the rendered visual with source values and inspect tooltips, labels, sorting, filters, and date changes. A chart that looks good but misstates data is a failed design.

## Review checklist

- What question does this visual answer?
- Are numerator, denominator, unit, period, and scope clear?
- Can a user compare values without guessing the scale?
- Is freshness or partial availability visible?
- Does the table or text fallback preserve the important meaning?
- Does the visual still work in grayscale, zoom, keyboard navigation, and mobile width?

## Defaults

- Prefer one clear comparison over many competing series.
- Keep a stable color meaning across the whole product.
- Use direct labels when the number of series is small.
- Keep raw values available when decisions depend on exact amounts.
- Reuse the existing chart library and theme; do not add a new visualization dependency for one chart.
