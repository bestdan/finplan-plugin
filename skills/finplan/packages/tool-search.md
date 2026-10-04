# Tool Search

Discover FinPlan MCP tools relevant to your current task without loading all tool schemas.

<!-- BEGIN GENERATED: tool-index search -->

## Tool index

| Tool                    | Description                                                           | Parameters                                      |
| ----------------------- | --------------------------------------------------------------------- | ----------------------------------------------- |
| `describe_finplan_tool` | Load the full schema for one tool on demand.                          | name                                            |
| `search_finplan_tools`  | Search FinPlan tools by natural-language query, or browse a category. | query, detail_level, max_results, include_tools |

<!-- END GENERATED: tool-index search -->

## Tools

### search_finplan_tools

Use it when the tool you need isn't named in the reference pages. Special `query` values: `"list_categories"`, `"category:<name>"` (e.g. `"category:tax"`), `"all"`. `detail_level` is `"names_only"`, `"names_and_descriptions"` (default), or `"full_schema"`. `max_results` is 1-10 (default 5). `include_tools` adds tool names per category for the `"list_categories"` query (default false).

### describe_finplan_tool

Use `search_finplan_tools` to find the name, then this to see exactly how to call it, instead of paying for every tool schema up front. Unknown names return `found: false` with suggestions.

## Usage notes

- Call `ping()` to warm up the server, then find the tool you need in the reference pages linked from `SKILL.md`. Search only when the tool isn't there.
- Use `"list_categories"` to see all tool categories with counts.
- Use `"category:tax"` to browse all tools in a specific category.
- Use `"all"` with `"names_only"` detail level for a compact overview.
- Default detail level (`"names_and_descriptions"`) includes name, description, category, and parameter summary.
- Follow a search with `describe_finplan_tool` to load one tool's full signature before calling it — the schema is read live from the server, so it always matches the real tool.
