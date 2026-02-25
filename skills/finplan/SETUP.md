# FinPlan Skills & Commands — Setup & Usage Guide

This directory contains a Claude **Agent Skill** that gives Claude the ability to do personal finance projections, tax calculations, retirement planning, Social Security analysis, and more — all powered by the FinPlan MCP server.

The companion [commands/](../../commands/) directory contains **slash commands** — client-side operations (local file I/O, dashboard generation) that work alongside the MCP skill.

## What's inside

```
client_docs/
├── skills/                 # MCP skill (remote tool catalog)
│   ├── SETUP.md              # This file
│   ├── SKILL.md              # Main skill (Claude reads this first)
│   └── packages/             # Detailed tool references (Claude reads on demand)
│       ├── projection.md     # Monte Carlo & closed-form projections
│       ├── tax.md            # Federal income tax & capital gains
│       ├── accounts.md       # Account types, allocations, ownership
│       ├── portfolio.md      # Return assumptions & glide paths
│       ├── goals.md          # Financial goal planning
│       ├── social-security.md # SSA benefits & claiming strategies
│       ├── mortgage.md       # Payments & amortization
│       ├── employer-match.md # 401(k) matching & vesting
│       ├── charts.md         # Chart.js visualizations
│       └── state.md          # User profiles & persistence
└── commands/               # Slash commands (client-side operations)
    ├── read-state.md         # /read-state — Read state from local JSON
    ├── save-state.md         # /save-state — Save state to local JSON
    └── projection-dashboard.md # /projection-dashboard — Generate HTML dashboard
```

### Skills vs Commands

|                      | Skills                                           | Commands                                                                      |
| -------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------- |
| **What they do**     | Teach Claude how to call remote MCP tools        | Define client-side operations Claude runs locally                             |
| **Where they run**   | Remote MCP server                                | Locally on the user's machine                                                 |
| **Install location** | Plugin (auto) or `~/.claude/skills/`             | Plugin (auto) or `~/.claude/commands/`                                        |
| **Invocation**       | Automatic (Claude triggers when relevant)        | User types `/finplan:<command-name>`                                          |
| **Examples**         | `run_projection`, `calculate_federal_income_tax` | `/finplan:read-state`, `/finplan:save-state`, `/finplan:projection-dashboard` |

## Prerequisites

You need the FinPlan MCP server connected to your Claude environment. The server endpoint is:

```
https://mcp.finplan.prethink.io/mcp
```

How you connect it depends on which Claude product you're using (see setup instructions below).

## Setup by platform

### Claude Code — Plugin (Recommended)

Install the FinPlan plugin from the marketplace:

```bash
claude plugin marketplace add bestdan/finplan-plugin
claude plugin install finplan@finplan-plugin
```

This installs:

- The FinPlan skill (auto-discovers tools when relevant)
- Slash commands: `/finplan:read-state`, `/finplan:save-state`, `/finplan:projection-dashboard`
- MCP server connection (auto-configured via `.mcp.json`)
- A hook that prompts you to allowlist curl for the FinPlan file server (one-time)

**Recommended**: Allowlist curl for the FinPlan file server to avoid repeated approval prompts when tools download result files:

```bash
claude settings add allowedTools 'Bash(curl*mcp.finplan.prethink.io*)'
```

To update later:

```bash
claude plugin update finplan
```

### Claude Code — Manual

If you prefer manual installation instead of the plugin:

**Step 1 — Install the skill**

```bash
mkdir -p ~/.claude/skills/finplan
cp -r skills/finplan/* ~/.claude/skills/finplan/
```

**Step 2 — Install the commands**

```bash
mkdir -p ~/.claude/commands
cp commands/*.md ~/.claude/commands/
```

This installs the commands globally (available in all projects). To install per-project instead, copy to `.claude/commands/` in your project directory.

**Step 3 — Add the MCP server** to your Claude Code settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "finplan": {
      "type": "url",
      "url": "https://mcp.finplan.prethink.io/mcp"
    }
  }
}
```

**Step 4 — Use it**

Start Claude Code. The skill auto-discovers and Claude will use FinPlan tools when relevant. You can also invoke it directly with `/finplan`.

Available slash commands:

- `/finplan:read-state` — Read your financial state from the local JSON file
- `/finplan:save-state` — Save the current state to the local JSON file
- `/finplan:projection-dashboard` — Generate an interactive HTML projection dashboard

### Claude Desktop — Cowork

[Cowork](https://support.claude.com/en/articles/13345190-getting-started-with-cowork) is Claude's background agent in the Desktop app. It can run multi-step financial planning tasks autonomously — describe what you need, approve the plan, and come back to finished work.

**Requirements**: Claude Max subscription, macOS Desktop app.

**Step 1 — Add the MCP connector**

1. Open Claude Desktop
2. Go to **Settings > Connectors**
3. Click **Add connector** and enter the remote MCP server URL:
   ```
   https://mcp.finplan.prethink.io/mcp
   ```
4. Save. You should see a tools icon confirming the connection.

> Note: Remote MCP servers must be added via Settings > Connectors. They cannot be added through the `claude_desktop_config.json` file.

**Step 2 — Install the skill**

1. Create a ZIP of the skill folder (the ZIP root should be the `finplan/` directory):
   ```bash
   cd skills
   zip -r finplan-skill.zip finplan/
   ```
2. Open **Settings > Capabilities**
3. Scroll to **Skills** and ensure skills are toggled on
4. Click **Upload skill** and select `finplan-skill.zip`
5. Confirm the FinPlan skill appears in your skills list

**Step 3 — Use it**

Start a new conversation or Cowork session. Claude will automatically use FinPlan tools when you ask about financial planning. For Cowork, describe a task like:

> "Build me a retirement projection: I'm 35, earn $120k, contribute $500/mo to my 401(k) with a 50% employer match up to 6%. Show me projected outcomes at ages 55, 60, and 65."

Claude will create a plan, execute the tools, and deliver results.

> The Desktop app must remain open while Cowork is running. Closing it ends the session.

### Claude.ai (Web)

**Step 1 — Add the MCP connector**

1. Go to [claude.ai](https://claude.ai) and open **Settings > Connectors**
2. Add a new connector with the URL `https://mcp.finplan.prethink.io/mcp`

**Step 2 — Install the skill**

1. Create a ZIP (same as above):
   ```bash
   cd skills
   zip -r finplan-skill.zip finplan/
   ```
2. Go to **Settings > Capabilities**, scroll to **Skills**
3. Upload `finplan-skill.zip`

**Step 3 — Use it**

Start a new conversation. Claude uses FinPlan tools automatically when relevant.

### Claude Agent SDK (Python / TypeScript)

1. Place the skill directory at `.claude/skills/finplan/` in your project.

2. Place command files at `.claude/commands/` in your project:
   ```bash
   mkdir -p .claude/commands
   cp commands/*.md .claude/commands/
   ```

3. Include `"Skill"` in your `allowed_tools` configuration.

4. Configure the MCP server connection in your agent setup to point to `https://mcp.finplan.prethink.io/mcp`.

## How it works

The skill uses **progressive disclosure** — Claude doesn't load everything at once:

1. **Always loaded** (~100 tokens): The skill name and description from the SKILL.md frontmatter. Claude knows the skill exists and when to reach for it.
2. **Loaded when triggered** (<5k tokens): The main SKILL.md body with tool categories, conventions, and workflows.
3. **Loaded on demand**: Individual package reference files. If you ask about Social Security, Claude reads `packages/social-security.md`. If you ask about projections, it reads `packages/projection.md`. The rest stay unloaded.

This keeps the context window lean while giving Claude access to 60+ specialized financial tools.

## Example prompts

Once set up, try asking Claude things like:

- "What would my 401(k) look like in 30 years if I contribute $500/month?"
- "Calculate my federal income tax on $150,000 as married filing jointly"
- "When should I claim Social Security if my salary is $95,000?"
- "Compare a conservative vs aggressive portfolio over 20 years"
- "What's my mortgage payment on a $400,000 loan at 6.5% for 30 years?"
- "Generate an amortization schedule for my mortgage"
- "How much does my employer 401(k) match contribute annually?"
- "Create a retirement projection with a fan chart showing percentile outcomes"

## Troubleshooting

**Skill not triggering**: Check that it appears in Settings > Capabilities under Skills. Try invoking directly with `/finplan` (Claude Code) or rephrasing your request to mention financial planning explicitly.

**MCP tools not available**: Verify the connector is active in Settings > Connectors. Look for the tools/hammer icon in Claude Desktop's bottom-right corner.

**Skills don't sync across platforms**: This is expected. Skills uploaded to Claude.ai are separate from Claude Desktop and Claude Code. You need to install on each platform independently.

## Updating

**Plugin users** (Claude Code):

```bash
claude plugin update finplan
```

**Manual install users** (Claude Code):

```bash
git pull
cp -r skills/finplan/* ~/.claude/skills/finplan/
cp commands/*.md ~/.claude/commands/
```

**Claude Desktop / Claude.ai** (skill ZIP upload):

```bash
git pull
cd skills && zip -r finplan-skill.zip finplan/
# Then re-upload via Settings > Capabilities
```
