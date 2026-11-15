# fpt

A thin local command-line client for FinPlan. It moves state files and bulk data between disk and the FinPlan server so a coding agent sees a short summary instead of the whole document.

fpt holds no financial logic: every calculation and validation rule lives on the server. It never imports `finplan_core` or `finplan_mcp`, and a test enforces that.

Changing fpt? Read `packages/fpt/dev_docs/security.md` in the FinPlan source repository first. fpt holds users' keys and writes their plans, and that page sets out the rules that keep both safe. It isn't published with fpt.

## Install

fpt is published in the public [`bestdan/finplan-plugin`](https://github.com/bestdan/finplan-plugin) repo, in its `fpt/` directory, with a `fpt-v<version>` tag for each release. Install a release with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install "git+https://github.com/bestdan/finplan-plugin@fpt-v0.3.0#subdirectory=fpt"
fpt --version
```

To move to a newer release, run the same command with the new tag and `--force`. `uv tool upgrade` keeps the source an install came from, so it won't move a pinned install to a new tag, or a checkout install to the public repo. From a FinPlan checkout, `uv tool install ./packages/fpt` installs the working copy.

The distribution is named `finplantools-fpt`; the command is `fpt`. It needs Python 3.10 or newer.

## Commands

- `fpt save --state FILE --response RESPONSE [--expect-hash HASH]`: merge a `manage_state` response into the state file. Nothing is written unless the result reproduces the response's `state_hash`, and, when the file exists, unless it still has the hash given as `--expect-hash`. With `--from-url URL --state-hash HASH` in place of `--response`, it installs a full document the server served as a `urls.data` download. `--dry-run` checks everything and writes nothing.
- `fpt hash FILE`: print the file's content hash as `data.hash`, the value `--expect-hash` takes.
- `fpt skills install <claude|codex|cursor|gemini|opencode>`: copy the skill that describes this fpt (`fpt/skill/SKILL.md`, in the open Agent Skills format) into the agent's user skills directory, replacing an older copy. Claude Code's follows `CLAUDE_CONFIG_DIR`, Codex's `CODEX_HOME`, and OpenCode's `XDG_CONFIG_HOME`. Run it again after upgrading fpt, so the skill matches the CLI.
- `fpt skills list`: show the skill this fpt ships, where each agent loads it from, and which agents have it.
- `fpt auth login [--no-browser]`: sign in through the browser with OAuth and PKCE. After signing in, click Continue on the page that follows. Over SSH, or when the browser is on another device, paste the URL from that page's copy box into the terminal instead. The key is stored in the OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service), or, when the keychain cannot take it (there is none, or it is locked, as a macOS login keychain is over SSH), in `credentials.json` in fpt's config directory with mode `0600`, and login says which and why. It lasts 30 days and cannot be refreshed: log in again when it expires.
- `fpt auth status`: the server, the signed-in user, where the key comes from (`environment`, `keychain` or `file`), the key's public `key_prefix`, and its expiry. Exits 5 when not signed in or the key is refused.
- `fpt auth logout`: delete the stored key. The key stays valid until it expires; revoke it at `/auth/api-keys` in a browser to end it now.

`FPT_API_KEY` in the environment wins over a stored sign-in, for CI and scripts. `FPT_SERVER_URL` points fpt at another server (default `https://mcp.finplan.tools`); sign-ins are kept per server. It must be https, except for `localhost`, `127.0.0.1` or `::1`, so a key never travels in cleartext off the machine. `FPT_CONFIG_DIR` moves the config directory from its default (`$XDG_CONFIG_HOME/fpt` or `~/.config/fpt`; `%APPDATA%\fpt` on Windows). No command prints a key.

`fpt save` is the plugin's `finplan.py save`, from the same source (`fpt/save.py`): it takes the same arguments, prints the same envelope on success and writes the same file. Usage errors differ: both exit 2, but `fpt` prints a JSON error on standard error where `finplan.py` prints argparse's usage text. `fpt save --help` has the details.

When fpt is installed, the plugin's `finplan.py save` runs `fpt save` in its place, provided `fpt --version` is in the range the plugin supports (`_FPT_MIN` and `_FPT_BELOW` in `finplan.py`). Raising fpt's minor version therefore needs a plugin release that widens that range, or plugin users keep saving with their own copy and see a warning.

## Output

Every command prints one JSON object on standard output and nothing else:

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

A failure with codes 2–7 prints one JSON object on standard error, naming the field at fault (`pointer`, a JSON Pointer), what to change (`hint`), and the exit code below. Code 1 is a bug in fpt: it exits with Python's own traceback, so report it with the command you ran.

| Code | Name            | Meaning                                             |
| ---- | --------------- | --------------------------------------------------- |
| 0    | `ok`            | success                                             |
| 1    | `internal`      | an uncaught error; a bug                            |
| 2    | `validation`    | bad arguments or input                              |
| 3    | `hash_mismatch` | a hash mismatch or stale write; nothing was written |
| 4    | `local_io`      | a local file could not be read or written           |
| 5    | `auth`          | not signed in, or the key was refused               |
| 6    | `network`       | the server could not be reached                     |
| 7    | `server`        | the server answered with an error                   |

The codes are the same as the plugin's `finplan.py`, so a caller branches on either the same way.

## Requests

Every request to the FinPlan API sends `User-Agent: fpt/<version>`; `save --from-url` downloads don't yet. When fpt runs under a coding agent it can recognise from the environment (Claude Code, Codex, or any agent that sets `AI_AGENT` or `AGENT`), it adds an `ai-agent <name>` token. Nothing else changes: output is the same for people and agents.
