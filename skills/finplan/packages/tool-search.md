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

Search for FinPlan tools by natural-language query. Use it when the tool you need isn't named in the reference pages.

| Parameter       | Type   | Description                                                                                                              |
| --------------- | ------ | ------------------------------------------------------------------------------------------------------------------------ |
| `query`         | string | Natural-language search query. Special values: `"list_categories"`, `"category:<name>"` (e.g. `"category:tax"`), `"all"` |
| `detail_level`  | string | `"names_only"`, `"names_and_descriptions"` (default), or `"full_schema"`                                                 |
| `max_results`   | int    | Maximum tools to return, 1-10 (default: 5)                                                                               |
| `include_tools` | bool   | When using `"list_categories"` query, include tool names per category (default: false)                                   |

Returns: `type`, `query`, `detail_level`, `total_results`, `tools` (list of matching tools at requested detail level).

### describe_finplan_tool

Load the full schema for a single tool on demand — parameter names, types, units, required/optional status, defaults, the return schema, and a ready-to-copy call example. Use `search_finplan_tools` to find the name, then `describe_finplan_tool` to see exactly how to call it, instead of paying for every tool schema up front.

| Parameter | Type   | Description                                                                                                 |
| --------- | ------ | ----------------------------------------------------------------------------------------------------------- |
| `name`    | string | Exact tool name to describe, e.g. `"run_projection"`. Unknown names return `found: false` with suggestions. |

Returns: `found`, `name`, `category`, `description`, `parameters` (list of `name`/`type`/`required`/`default`/`description`), `returns` (return schema), `call_example`, `keywords`.

## Usage notes

- Call `ping()` to warm up the server, then find the tool you need in the reference pages linked from `SKILL.md`. Search only when the tool isn't there.
- Use `"list_categories"` to see all tool categories with counts.
- Use `"category:tax"` to browse all tools in a specific category.
- Use `"all"` with `"names_only"` detail level for a compact overview.
- Default detail level (`"names_and_descriptions"`) includes name, description, category, and parameter summary.
- Follow a search with `describe_finplan_tool` to load one tool's full signature before calling it — the schema is read live from the server, so it always matches the real tool.
