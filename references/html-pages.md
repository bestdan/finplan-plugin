# HTML page conventions

Styling and build rules shared by the commands that write an HTML page next to the user's state file: `/finplan:projection-dashboard`, `/finplan:what-if`, `/finplan:compare-scenarios` and `/finplan:scenario`. This is not a slash command. Those commands link here.

The data rules are not repeated here. Data files stay out of context ([SKILL.md](../skills/finplan/SKILL.md#data-files-stay-out-of-context)), and chart data reaches the page through the [inject script](../skills/finplan/packages/file-tools.md#embedding-data-in-self-contained-html-files).

## Fully offline pages (vendored Chart.js)

Most pages load Chart.js from the CDN (`<script src="https://cdn.jsdelivr.net/npm/chart.js@4">`), which is fine when the page will be opened online. Some commands require a page that renders with **no external requests at all** (`/finplan:compare-scenarios`, `/finplan:scenario`). A CDN `<script src>` breaks that, so those pages inline the vendored copy of Chart.js instead of linking it.

- The plugin ships a pinned Chart.js UMD bundle at `${CLAUDE_PLUGIN_ROOT}/assets/chart.umd.min.js` (Chart.js v4.4.6). Treat it as read-only.
- Inline it with the **same placeholder/inject mechanism as the data files**: it is one more token → file replacement. In the `<head>`, write an empty script the injector fills:

  ```html
  <script>__CHARTJS__</script>
  ```

  Then add the vendored path as one more pair on the [inject script](../skills/finplan/packages/file-tools.md#embedding-data-in-self-contained-html-files) call:

  ```bash
  python3 -c "..." output.html \
    "__CHARTJS__"  "$CLAUDE_PLUGIN_ROOT/assets/chart.umd.min.js" \
    "__DATA__"     "${TMPDIR:-/tmp}/finplan/compare_data.json"
  ```

  The vendored bundle contains no `</script>` sequence, so it is safe to inline between script tags. Keeping Chart.js on the same inject pass means it never enters your context either.
- **Vertical milestone lines** (e.g. a dashed line at the retirement age): draw them with a tiny inline `afterDraw` Chart.js plugin that strokes the canvas, rather than vendoring `chartjs-plugin-annotation`. One vendored asset keeps the offline story simple.

## Chart styling

Use these conventions for consistent styling across all charts.

### Chart.js options

```javascript
{
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { position: 'top', labels: { usePointStyle: true } },
    tooltip: {
      mode: 'index',
      intersect: false,
      // Sort tooltip items highest-to-lowest value
      itemSort: (a, b) => b.raw - a.raw
    }
  }
}
```

### Font stack

```
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
```

### Grid and axes

- Grid color: `#e5e7eb`
- Y-axis currency formatting: custom tick callback with `$` prefix and SI suffixes (`$100k`, `$1.2M`)
- X-axis: years (months / 12) for projections

### Fan chart bands

- Outer band (p10-p90): `rgba(59, 130, 246, 0.1)`. Fill between p90 (upper boundary) and p10 with `fill: '-1'`
- Inner band (p25-p75): `rgba(59, 130, 246, 0.2)`. Fill between p75 (upper boundary) and p25 with `fill: '-1'`
- Median (p50): `#3b82f6`, `borderWidth: 2.5`, solid line
- Net deposits: `#8b5cf6` (purple), `borderWidth: 2`, dashed (`borderDash: [5, 5]`)
- All band boundary lines: `pointRadius: 0`, `borderColor: 'transparent'`

### Percentile colors (when shown individually)

| Percentile | Color      | Hex       |
| ---------- | ---------- | --------- |
| p90        | Emerald    | `#10b981` |
| p75        | Lt Emerald | `#34d399` |
| p50        | Blue       | `#3b82f6` |
| p25        | Orange     | `#f97316` |
| p10        | Red        | `#ef4444` |

### Account type colors (for stacked/breakdown charts)

| Account type         | Color  | Hex       |
| -------------------- | ------ | --------- |
| Traditional 401k/IRA | Blue   | `#3b82f6` |
| Roth accounts        | Green  | `#10b981` |
| Taxable brokerage    | Amber  | `#f59e0b` |
| HSA                  | Pink   | `#ec4899` |
| 529 Education        | Purple | `#8b5cf6` |
| Real estate          | Indigo | `#6366f1` |
| Cash/savings         | Gray   | `#6b7280` |

### Goal-specific fan chart colors

| Goal type       | Base color                   |
| --------------- | ---------------------------- |
| Retirement      | Green — `rgba(16, 185, 129)` |
| Education       | Amber — `rgba(245, 158, 11)` |
| Total portfolio | Blue — `rgba(59, 130, 246)`  |

### Multi-account palette (for ad-hoc charts with multiple series)

`#0ea5e9` (sky), `#8b5cf6` (purple), `#ec4899` (pink), `#f59e0b` (amber), `#10b981` (emerald), `#ef4444` (red), `#6366f1` (indigo)

### Page design (for full-page HTML output)

- Background: `#f0f2f5`
- Cards: white, `border-radius: 12px`, `box-shadow: 0 2px 8px rgba(0,0,0,0.08)`
- Responsive grid layout using CSS grid
- Mobile-friendly with `@media` breakpoints

### Light theme only

Every value on this page is for a light background. There is no dark palette here. A command that requires a dark theme says where its dark values come from.
