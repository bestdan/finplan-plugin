---
name: fpt
description: Save FinPlan state edits to the local state file with the fpt CLI. Use whenever a FinPlan manage_state call (or any FinPlan tool that returns a state download) changes the user's plan and the result must reach their *_finplan_state.json file, and before any FinPlan state edit, to record the file's hash. Never write the state file yourself.
---

# fpt: saving FinPlan state

`fpt` is a local command-line client for FinPlan. It keeps the user's state file correct: every change to that file goes through `fpt save`, which applies the server's response and checks the result against the server's hash before writing anything. fpt holds no financial logic; the FinPlan server does every calculation.

This skill was installed by `fpt skills install` and describes the fpt that installed it. Run `fpt --version` to see which that is, and `fpt <command> --help` for every flag.

## Rules

- **Save only through `fpt save`.** Never write, edit, copy over or move the state file (`finplan_state.json`, `*_finplan_state.json`) yourself: not with a file-writing tool, not with a shell (`>`, `jq … > file`, `cp`, `mv`, `tee`), and not with an inline script. Rebuilding the document by hand drops fields and saves transient metadata, which is the failure fpt exists to prevent.
- **Ask before writing.** Tell the user what will change in their plan and get their agreement before the `manage_state` call that changes it.
- **Never print or paste credentials.** Do not echo an API key or token, read one into the conversation, or put one in a command line.
- **Do not copy a `.pending.json` file over the state file.** It is a response that arrived too late; redo the edit instead (see exit code 3).

## The edit loop

1. **Record the file's hash before the call:** `fpt hash <state file>` prints it as `data.hash`. After a save, the envelope's `metadata.result_hash` is the new hash, so the next edit can reuse it. A new plan (`manage_state` with `action="create"`) has no file yet and no hash.
2. **Call `manage_state`** over the FinPlan MCP server, passing the state file's contents as `state_json` exactly as they are on disk.
3. **Write the response, unedited, to a file beside the state file** with your file-writing tool, for example `<state file>.response.json`. Never put it in `/tmp`, which every account on the machine shares: the response can hold the whole plan. Don't pass it through a shell heredoc or `echo`, which agent harnesses often refuse for JSON. When another program produces the response, pipe it straight in with `--response -` instead.
4. **Save it:**

   ```bash
   fpt save --state <state file> --response <state file>.response.json --expect-hash <hash from step 1>
   ```

   Leave `--expect-hash` off only when the file does not exist yet. Add `--dry-run` to check everything and write nothing. Then deal with the response file:
   - **The save succeeded:** delete it.
   - **It failed and the `manage_state` call must be redone** (a stale write, exit 3, keeps its own copy as `.pending.json`): delete it.
   - **A transient error** (exit 6 or 7): keep it, and retry the same save.

5. **When the response has `urls.data` instead of the document** (a full document served as a download, as `migrate_state` and the sync tools return), save it by reference, without reading the download into the conversation:

   ```bash
   fpt save --state <state file> --from-url <urls.data> --state-hash <content_hash> --expect-hash <hash>
   ```

`fpt save` handles every response shape: an `update_*` change, a `remove_*`, a person change, and a full document. It writes only when the result reproduces the response's `state_hash` and the file still has the hash you recorded. A successful write keeps the previous file as `<state file>.bak`.

## Output

Every command prints one JSON object on standard output:

```json
{
  "data": {},
  "metadata": {
    "input_hash": null,
    "result_hash": null,
    "schema_fingerprint": null,
    "out": null,
    "truncated": false,
    "next_cursor": null,
    "next_action": null,
    "warnings": []
  }
}
```

Read `data` for the result and pass `metadata.warnings` on to the user. A failure prints one JSON object on standard error instead, with `error`, `message`, `pointer` (the field at fault), `hint` (what to change) and `exit_code`. Follow the hint.

## Exit codes

Branch on the code and its `error`, not the message.

| Code | `error`                          | What to do                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ---- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0    | `ok`                             | Done. Report `data` to the user.                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 1    | `internal`                       | A bug in fpt. Show the user the traceback and the command you ran.                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2    | `validation`                     | Fix the arguments or the input as the hint says, then retry.                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2    | `dropped_keys`                   | The state file holds keys FinPlan does not keep, and saving would delete them. Nothing was written. Tell the user which keys `dropped_keys` names; pass `--allow-dropped-keys` only once they say those keys may go.                                                                                                                                                                                                                                                                                  |
| 3    | `hash_mismatch` or `stale_write` | Nothing was written. For `stale_write`, the file changed since you recorded its hash: re-read it, record its hash again and redo the edit. For `hash_mismatch`, the response does not reproduce its own hash: redo the `manage_state` call, unless the error carries `dropped_keys`, which no redo can fix: tell the user which keys they are. If the same edit has already failed this way, stop and tell the user rather than retrying: the file may hold keys of its own the server does not keep. |
| 4    | `local_io`                       | A local file could not be read or written. Check the path and permissions.                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 5    | `auth`                           | Not signed in, or the key was refused. Ask the user to run `fpt auth login` in their own terminal (it opens a browser), then retry. Never ask them to paste a key.                                                                                                                                                                                                                                                                                                                                    |
| 6    | `network`                        | The server could not be reached. Retry once; if it fails again, tell the user.                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 7    | `server`                         | The server answered with an error. Show the user its message.                                                                                                                                                                                                                                                                                                                                                                                                                                         |

## Commands in this version

- `fpt save`: merge a `manage_state` response, or install a `urls.data` download, into the state file.
- `fpt hash FILE`: print a file's content hash as `data.hash`, the value `--expect-hash` takes.
- `fpt skills list` and `fpt skills install <agent>`: show this skill, and install it for an agent.
- `fpt auth status`: show which server fpt is signed in to, as whom, where the key comes from (`environment`, `keychain` or `file`), the key's public `key_prefix` and when it expires. Run it when a command exits 5. `fpt auth login` and `fpt auth logout` are the user's to run: login opens a browser, and logout signs them out.
