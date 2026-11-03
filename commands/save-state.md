---
description: Save the current FinPlan user state JSON to the local file system after any state modification
allowed-tools:
  - Glob
  - Edit(//tmp/finplan/**)
  - Bash(python3 *scripts/finplan.py *)
argument-hint: [file-path]
---

# Save Financial Plan State

Merge the latest `manage_state` response into the local state file with `finplan.py save`. You never write the state file yourself: the helper applies the response, checks the result against the server's `state_hash`, and replaces the file only if nobody changed it since you recorded its hash.

## State file location

Save to the same `*_finplan_state.json` file in the current working directory that was most recently read or created. If no state file exists yet, save to `finplan_state.json` in the working directory.

## How to save

1. Find the existing state file using Glob for `*finplan_state.json` in the working directory.
2. Take the file's hash **recorded before** the `manage_state` call: the output of `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/finplan.py hash <file>` that the calling command ran, or the `metadata.result_hash` that the previous save printed. If the file does not exist yet (an `action="create"`), there is no hash: leave `--expect-hash` off.
   - If the file exists and no hash was recorded, run `finplan.py hash <file>` now and pass that. The save is then guarded only against changes made after this moment, so say so in your report.
3. **If the response carries `urls.data`**, it served the full document as a download: a `manage_state` call made with `full_document: "download"` (a `create`, or an edit that returned the whole document), or `migrate_state`. Do not download it or read it. Pass the URL and the response's `content_hash` straight to `save`, then skip to step 6 and report the envelope this `save` prints:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/finplan.py save --state <file> --from-url <urls.data> --state-hash <content_hash> --expect-hash <hash>

   # create: no state file yet, so no --expect-hash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/finplan.py save --state <file> --from-url <urls.data> --state-hash <content_hash>
   ```

   `save` downloads it only from the FinPlan server (or, for a local server, its download directory), checks it against `content_hash`, and installs it the same guarded way. Any other URL is refused.
4. Otherwise, write the most recent `manage_state` response with the Write tool to `/tmp/finplan/response-<id>.json`, where `<id>` is the first 12 hex characters of the response's `state_hash`. Write it **exactly as the tool returned it**: every key, unedited, nothing added or removed. This works for every response shape: an `update_*` or `remove_*` delta, a person change, and a full document (`create`, `return_full_state=true`, or a migrated input).
   - Naming the file after the hash gives every response its own new file, so an earlier save's file is never read by mistake. If Write refuses because the file has not been read yet, the file already exists, so this same response was written before: use that file as it is.
   - Do not pass the JSON through a shell heredoc or `echo`. Claude Code's Bash check refuses commands that mix braces and quotes.
5. Run `save` on that file:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/finplan.py save --state <file> --response /tmp/finplan/response-<id>.json --expect-hash <hash>

   # create: no state file yet, so no --expect-hash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/finplan.py save --state <file> --response /tmp/finplan/response-<id>.json
   ```
6. Report the result from the JSON envelope `save` prints: the file path (`data.path`), what changed (`data.change`, `data.section`, `data.item_id`), and any `metadata.warnings`. Keep `metadata.result_hash`: it is the `--expect-hash` for the next save of this file.

## When save refuses

`save` writes nothing on any error. It prints one JSON object to standard error, with a `hint` saying what to do. **Never write the state file by hand to get around an error: not with Write or Edit, which the plugin's hook denies on `finplan_state.json` and `*_finplan_state.json`, and not through the shell (`>`, `jq … > file`, `cp`, `mv`, `tee`, an inline `python3` script).** A redirect onto the file being read empties it before `jq` runs. Write is for the response file under `/tmp/finplan/` only.

- **Exit 3, `error: stale_write`:** the file changed after its hash was recorded. The response is kept as `<file>.pending.json` for reference. Re-read the state file, record its hash, redo the `manage_state` call against it, and save that new response. Do not copy the pending response over the file.
- **Exit 3, `error: hash_mismatch`:** the rebuilt document does not match the server's `state_hash`. Most often the `state_json` passed to `manage_state` was not the file's content verbatim. Re-read the file and redo the edit against it unchanged.
- **Exit 2, `error: validation`:** a missing `--expect-hash` while the state file exists, a malformed response (an error response carries no `state_hash`), a removal whose target is not in the file, or a `--from-url` that is not the response's own `urls.data`. Fix the call, not the file.
- **Exit 4, `error: local_io`:** a file could not be read or written.
- **Exit 6, `error: network`, or exit 7, `error: server`** (`--from-url` only): the download could not be fetched, and nothing was written. A link lasts about an hour; if it expired, redo the tool call and save its new response. If the message says `Tunnel connection failed`, Claude Code's sandbox blocked `mcp.finplan.tools`: redo the same `manage_state` call with `full_document: "inline"`, save that response through step 4, and tell the user once that adding `mcp.finplan.tools` to `sandbox.network.allowedDomains` makes later saves cheaper (the plugin README shows the setting). For `migrate_state`, which has no inline form, stop and tell the user the same thing.

## Important

- If no state has been created or loaded in this session, inform the user that there is nothing to save and suggest using `/finplan:read-state` first or creating a new state via `manage_state`.
- If `$ARGUMENTS` is provided, treat it as an explicit file path to save to instead of the default location.
- A successful save keeps the previous file as `<file>.bak`.
