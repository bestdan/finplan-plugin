# System Tools

Server status and connectivity checks.

## Tools

### ping

Check that the FinPlan MCP server is reachable and ready. Takes no parameters. Use as a lightweight warm-up call — the server may sleep after inactivity and this wakes it without doing real work.

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| _(none)_  |      |             |

Returns: `status` ("ok"), `server_version`, `authenticated` (bool — whether the request carried a valid API key).

### get_usage_guide

Return the complete FinPlan usage guide (the full `SKILL.md`) as markdown. Takes no parameters. It ships server-side for **plugin-less** MCP clients that never loaded this skill — if you already have the finplan plugin/skill, you have this content and need not call it.

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| _(none)_  |      |             |

Returns: `success` (bool) and `guide` (the markdown document).

## Usage notes

- Call `ping()` before any real tool calls if the server may be cold (first use in a session, or after long inactivity).
- If `authenticated` is `false` and the user expects to be authenticated, troubleshoot the API key configuration before proceeding.
- The `/finplan:setup` flow calls `ping()` automatically in step 0c.
