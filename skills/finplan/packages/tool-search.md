# Tool Search

Discover FinPlan MCP tools relevant to your current task without loading all tool schemas.

## Tools

### search_finplan_tools

Search for FinPlan tools by natural-language query. Call this FIRST to discover available tools before calling specific ones.

| Parameter       | Type   | Description                                                                                                              |
| --------------- | ------ | ------------------------------------------------------------------------------------------------------------------------ |
| `query`         | string | Natural-language search query. Special values: `"list_categories"`, `"category:<name>"` (e.g. `"category:tax"`), `"all"` |
| `detail_level`  | string | `"names_only"`, `"names_and_descriptions"` (default), or `"full_schema"`                                                 |
| `max_results`   | int    | Maximum tools to return, 1-10 (default: 5)                                                                               |
| `include_tools` | bool   | When using `"list_categories"` query, include tool names per category (default: false)                                   |

Returns: `type`, `query`, `detail_level`, `total_results`, `tools` (list of matching tools at requested detail level).

## Usage notes

- Call this tool **first** before calling any other FinPlan tool.
- Use `"list_categories"` to see all tool categories with counts.
- Use `"category:tax"` to browse all tools in a specific category.
- Use `"all"` with `"names_only"` detail level for a compact overview.
- Default detail level (`"names_and_descriptions"`) includes name, description, category, and parameter summary.
