# Dynamic Tool Search

## Overview

FinPlan exposes 30+ MCP tools across many financial domains (tax, projection, mortgage, social security, etc.). Loading all tool schemas into an LLM agent's context window upfront consumes significant tokens and degrades tool selection accuracy.

The `search_finplan_tools` meta-tool solves this by letting agents discover tools on-demand. Instead of reading all tool definitions, agents search with a natural-language query and receive only the relevant tools at the requested detail level.

This design follows the pattern described in [Anthropic's Advanced Tool Use guidance](https://www.anthropic.com/engineering/advanced-tool-use) and the [Tool Search Tool API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool).

## Architecture

```
Agent                              MCP Server
  │                                    │
  │ 1. search_finplan_tools(           │
  │      query="income tax",           │
  │      detail_level="names_and_descriptions")
  ├───────────────────────────────────▶│
  │                                    │ Score all catalog entries
  │                                    │ against query tokens
  │ 2. Returns top-N matching tools    │
  │◀───────────────────────────────────┤ (~200 tokens)
  │                                    │
  │ 3. Call discovered tool            │
  │    calculate_federal_income_tax()  │
  ├───────────────────────────────────▶│
  │◀───────────────────────────────────┤ (tool result)
```

## Key Components

### Tool Catalog (`finplan_mcp/tools/tool_catalog.py`)

A data-only module containing structured metadata for every tool:

- **name**: Exact MCP tool function name
- **description**: Concise human-readable summary
- **category**: Domain grouping (tax, projection, portfolio, ...)
- **keywords**: Extra search terms for discoverability
- **parameters_summary**: One-line hint of key parameters

The catalog imports no tool modules, so it loads cheaply with no side effects.

### Search Tool (`finplan_mcp/tools/tool_search.py`)

The `search_finplan_tools` MCP tool exposes three capabilities:

1. **Natural-language search**: Tokenizes the query and scores catalog entries using a weighted heuristic (name > description > category > keywords > parameters).
2. **Category browsing**: `category:tax` returns all tools in a domain.
3. **Category listing**: `list_categories` returns all categories with tool counts. Use `include_tools=True` to also get the list of tool names in each category (this increases token usage).

### Detail Levels

| Level                    | Returns                                           | Use Case                       |
| ------------------------ | ------------------------------------------------- | ------------------------------ |
| `names_only`             | Tool names only                                   | Quick existence check          |
| `names_and_descriptions` | Names, descriptions, category, parameters summary | Recommended default            |
| `full_schema`            | Everything including keywords                     | Disambiguation between similar |

## Scoring Algorithm

The search uses a simple weighted token-matching heuristic:

| Match Location    | Points per Token                                          |
| ----------------- | --------------------------------------------------------- |
| Exact tool name   | +20 (replaces name substring scoring to avoid duplicates) |
| Substring in name | +5 (only if not an exact match)                           |
| Category match    | +3                                                        |
| Description match | +3                                                        |
| Keyword match     | +2                                                        |
| Parameter match   | +1                                                        |

Results are sorted by score descending. Ties are broken alphabetically for stability.

## Adding a New Tool to the Catalog

> The paths below refer to the private [FinPlan server repository](https://github.com/bestdan/finplan), not this plugin repo. Plugin users don't need to modify the tool catalog — it's maintained server-side.

When you add a new MCP tool:

1. Add the `@mcp.tool()` function as usual in `finplan_mcp/tools/`.
2. Add a `ToolEntry` to `TOOL_CATALOG` in `finplan_mcp/tools/tool_catalog.py`.
3. Include descriptive keywords that users might search for.
4. Update the expected tool set in `tests/test_server.py::test_list_tools`.
5. Run `uv run pytest packages/mcp-server` to verify.

## Keeping the Catalog in Sync

The catalog is hand-written (descriptions, keywords, and parameter summaries require human judgment), but a CI script validates it stays in sync with the actual registered tools.

### CI Check

```bash
python3 scripts/sync_tool_catalog.py check
```

This runs as part of `scripts/check.py` and will **fail the build** if:

- A registered `@mcp.tool()` is missing from `TOOL_CATALOG`
- A `TOOL_CATALOG` entry refers to a tool that no longer exists
- The `search_finplan_tools` meta-tool is accidentally added to the catalog

### Scaffolding Missing Entries

When you add a new tool and the check fails, generate stubs:

```bash
python3 scripts/sync_tool_catalog.py scaffold
```

This prints `ToolEntry(...)` stubs with `TODO` placeholders that you copy into `tool_catalog.py` and fill in with real descriptions, keywords, and parameter summaries.

### Why Not Auto-Generate?

The catalog metadata (descriptions, keywords, parameter summaries) requires human judgment to write well. Auto-generated descriptions would be too verbose or too generic for effective search. The sync script catches drift; humans provide quality.

## Token Budget Impact

| Approach             | Approximate Token Cost        |
| -------------------- | ----------------------------- |
| All 30+ tool schemas | ~10,000-20,000 tokens upfront |
| search_finplan_tools | ~500 tokens (tool definition) |
| Typical search call  | ~200 tokens (result)          |

This represents an 85-95% reduction in tool-related token consumption per session.
