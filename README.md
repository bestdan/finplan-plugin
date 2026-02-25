# FinPlan — Claude Code Plugin

Personal finance projection engine powered by 60+ MCP tools. Monte Carlo projections, tax calculations, retirement planning, Social Security analysis, and interactive dashboards.

## Install

From the marketplace:

```bash
claude plugin marketplace add bestdan/finplan-plugin
claude plugin install finplan@finplan-plugin
```

Or from a local clone:

```bash
git clone https://github.com/bestdan/finplan-plugin.git
claude plugin install finplan --plugin-dir ./finplan-plugin
```

This installs the skill, commands, MCP server connection, and a hook that prompts you to allowlist curl for file downloads.

**Recommended**: Allowlist curl for the FinPlan file server to avoid repeated approval prompts:

```bash
claude settings add allowedTools 'Bash(curl*mcp.finplan.prethink.io*)'
```

## What you get

### Skill

Claude automatically discovers and uses FinPlan tools when you ask about financial planning. 14 tool categories covering projections, tax, accounts, goals, Social Security, mortgage, employer match, charts, and more.

### Commands

| Command                         | Description                                    |
| ------------------------------- | ---------------------------------------------- |
| `/finplan:read-state`           | Read financial state from local JSON file      |
| `/finplan:save-state`           | Save current state to local JSON file          |
| `/finplan:projection-dashboard` | Generate interactive HTML projection dashboard |

### MCP Server

Auto-connects to the FinPlan MCP server at `https://mcp.finplan.prethink.io/mcp` — no manual configuration needed.

### Hook

On first FinPlan tool use, prompts you to allowlist `curl` for the file server if you haven't already. This avoids repeated approval dialogs when tools download result files.

## Example prompts

- "What would my 401(k) look like in 30 years if I contribute $500/month?"
- "Calculate my federal income tax on $150,000 as married filing jointly"
- "When should I claim Social Security if my salary is $95,000?"
- "Compare a conservative vs aggressive portfolio over 20 years"
- "Create a retirement projection with a fan chart showing percentile outcomes"

## Update

```bash
claude plugin update finplan
```

## Testing locally

After cloning this repo, test the plugin before making changes.

### 1. Load the plugin from the local directory

```bash
claude --plugin-dir .
```

This starts Claude Code with the plugin loaded from your working copy instead of an installed version.

### 2. Verify the plugin loaded

In the Claude Code session, run `/help` and confirm:

- The FinPlan skill appears in the skills list
- The namespaced commands appear: `/finplan:read-state`, `/finplan:save-state`, `/finplan:projection-dashboard`

### 3. Verify MCP server auto-connects

Ask Claude to list available tools or run a simple tool call:

```
Search for FinPlan tools related to "income tax"
```

If the MCP server connected via `.mcp.json`, Claude should find and call `search_finplan_tools` without any manual server configuration.

### 4. Test commands

```
/finplan:read-state
```

If no state file exists, the command should report that and suggest creating one — this confirms the command loaded and executed correctly.

```
/finplan:save-state
```

Should report nothing to save (expected if no state was created).

### 5. Test skill trigger

Ask a financial planning question without explicitly mentioning FinPlan:

```
What would a $500/month 401(k) contribution look like after 30 years?
```

Claude should automatically engage the FinPlan skill and call MCP tools.

### 6. Test dashboard generation (optional, requires state)

If you have a `finplan_state.json` file in the working directory:

```
/finplan:projection-dashboard
```

This should generate a self-contained HTML file and open it in the browser.

### Checklist

- [ ] `claude --plugin-dir .` starts without errors
- [ ] `/help` shows finplan skill and `/finplan:*` commands
- [ ] MCP tools are available (no manual `settings.json` needed)
- [ ] `/finplan:read-state` executes (reports no file or reads existing state)
- [ ] `/finplan:save-state` executes (reports nothing to save or saves state)
- [ ] Skill triggers automatically on financial planning questions
- [ ] `/finplan:projection-dashboard` generates HTML (if state file exists)

## Other platforms

Claude Desktop and Claude.ai users: see [SETUP.md](skills/finplan/SETUP.md) for ZIP-upload instructions. Those platforms don't support plugins — use the skill upload flow instead.

## License

Proprietary. See [repository](https://github.com/bestdan/finplan-plugin) for details.
