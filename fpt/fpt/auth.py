"""``fpt auth login | status | logout``, and the one place fpt finds its credential.

Sign-in is the server's own OAuth flow: register a native client, then an
authorization-code grant with PKCE and a redirect to a listener on ``127.0.0.1``. The
server does not redirect to a loopback address by itself. It renders a hand-off page with
a Continue button and a copy box (``routes/_loopback_callback_html.py``), so the listener
hears back only after the user clicks Continue, and never when the browser is on another
machine. Login therefore also reads a pasted callback URL from standard input, whichever
arrives first.

The token the server returns is an API key (``fp_live_…``) that lasts
``DEFAULT_OAUTH_TOKEN_DAYS``. There is no refresh grant and no revocation endpoint, so an
expired or refused key ends in exit code 5 and the hint to log in again.

Where the key lives, in the order :func:`resolve_credential` reads them:

1. ``FPT_API_KEY`` in the environment, for CI and scripts. It wins over a stored login.
2. The OS keychain, through ``keyring`` (macOS Keychain, Windows Credential Manager,
   Linux Secret Service).
3. A file, ``credentials.json`` in fpt's config directory, mode ``0600``, used when the
   keychain cannot take the key: no keyring backend (headless Linux), or one that refuses
   the write (a locked macOS login keychain over SSH). Login says why when it falls back.

When the last login went to the file, the file is read before the keychain, so a key an
earlier login left in a keychain that now refuses writes cannot shadow the newer one. If
that file has since been deleted by hand, the keychain's key is still used.

Each is keyed by the server's origin, so a staging login and a production login coexist.
Facts about a login that are not secret (who, the key's public ``key_prefix``, when it
expires, where it is stored) go in ``auth.json`` beside it.

No command prints a credential. ``auth status`` reports the key by its ``key_prefix``,
the label the server already lists and logs it under, and nothing else of it.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import queue
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, TextIO, cast

from fpt.client import build_request
from fpt.exit_codes import EXIT_CODES_HELP, ExitCode
from fpt.output import FptError, emit, envelope

API_KEY_ENV = "FPT_API_KEY"
SERVER_ENV = "FPT_SERVER_URL"
CONFIG_DIR_ENV = "FPT_CONFIG_DIR"
DEFAULT_SERVER = "https://mcp.finplan.tools"
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

KEYRING_SERVICE = "finplantools-fpt"
CLIENT_NAME = "fpt"
CALLBACK_PATH = "/callback"
# How long login waits for the listener or a pasted URL before giving up.
LOGIN_TIMEOUT_SECONDS = 300
HTTP_TIMEOUT_SECONDS = 30
# The auth answers are a few hundred bytes; a cap keeps a misbehaving server from filling memory.
MAX_RESPONSE_BYTES = 64 * 1024

SOURCE_ENV = "environment"
SOURCE_KEYCHAIN = "keychain"
SOURCE_FILE = "file"

_RELOGIN_ERROR_HINT = (
    "Run `fpt auth login` to sign in. Keys from sign-in last 30 days and cannot be "
    "refreshed. Do not paste a key into the conversation."
)


# ---------------------------------------------------------------------------
# Where things live
# ---------------------------------------------------------------------------


def server_origin(env: Mapping[str, str] | None = None) -> str:
    """The FinPlan server fpt signs in to: ``FPT_SERVER_URL``, else production."""
    source = os.environ if env is None else env
    value = source.get(SERVER_ENV, "").strip() or DEFAULT_SERVER
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise FptError(
            ExitCode.VALIDATION,
            f"{SERVER_ENV} is not an http(s) URL: {value!r}",
            f"Set {SERVER_ENV} to the server's origin, e.g. {DEFAULT_SERVER}, or unset it.",
            source="environment",
        )
    # The key is a 30-day credential: never send it in cleartext beyond this machine.
    if parsed.scheme == "http" and parsed.hostname not in _LOOPBACK_HOSTS:
        raise FptError(
            ExitCode.VALIDATION,
            f"{SERVER_ENV} uses http for a host that is not this machine: {value!r}",
            "Use an https URL; plain http is allowed only for localhost, 127.0.0.1 or ::1.",
            source="environment",
        )
    return f"{parsed.scheme}://{parsed.netloc}"


def config_dir(env: Mapping[str, str] | None = None) -> Path:
    """fpt's own config directory: ``FPT_CONFIG_DIR``, else the platform's user config dir."""
    source = os.environ if env is None else env
    explicit = source.get(CONFIG_DIR_ENV, "").strip()
    if explicit:
        return Path(explicit).expanduser()
    if sys.platform == "win32":
        base = source.get("APPDATA", "").strip()
        return (Path(base) if base else Path.home() / "AppData" / "Roaming") / "fpt"
    xdg = source.get("XDG_CONFIG_HOME", "").strip()
    return (Path(xdg).expanduser() if xdg else Path.home() / ".config") / "fpt"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as handle:
            loaded: Any = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise FptError(
            ExitCode.LOCAL_IO,
            f"cannot read {str(path)!r}: {exc}",
            f"Delete {str(path)!r} and run `fpt auth login` again.",
            source="config",
        ) from exc
    return cast("dict[str, Any]", loaded) if isinstance(loaded, dict) else {}


def _write_private_json(path: Path, data: dict[str, Any]) -> None:
    """Write ``data`` to ``path`` with mode 0600, created that way rather than chmod'ed after."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        # A leftover .tmp would keep its own, possibly looser, mode: start from a new file.
        tmp.unlink(missing_ok=True)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except OSError as exc:
        raise FptError(
            ExitCode.LOCAL_IO,
            f"cannot write {str(path)!r}: {exc}",
            f"Check that {str(path.parent)!r} is writable.",
            source="config",
        ) from exc


# ---------------------------------------------------------------------------
# Credential stores
# ---------------------------------------------------------------------------


class Keychain:
    """The OS keychain through ``keyring``. ``available`` is False on a host with no backend."""

    def __init__(self) -> None:
        try:
            import keyring
            import keyring.errors
        except ImportError:  # pragma: no cover - keyring is a declared dependency
            self._keyring: Any = None
            return
        self._keyring = keyring
        self._errors: Any = keyring.errors

    @property
    def available(self) -> bool:
        """Whether a real keyring backend is configured (not the ``fail`` backend)."""
        if self._keyring is None:
            return False
        backend = self._keyring.get_keyring()
        return float(getattr(backend, "priority", 0)) > 0

    def get(self, origin: str) -> str | None:
        if not self.available:
            return None
        try:
            value: str | None = self._keyring.get_password(KEYRING_SERVICE, origin)
        except self._errors.KeyringError:
            return None
        return value

    def set(self, origin: str, token: str) -> str | None:
        """Store ``token``. Return None when stored, else why the keychain could not take it.

        The reason matters because the fixes differ: no backend at all (headless Linux)
        versus a keychain that exists but refused the write, as macOS does with -25308
        when the login keychain is locked in a session with no GUI (SSH, a remote shell).
        """
        if not self.available:
            return "no OS keychain is available"
        try:
            self._keyring.set_password(KEYRING_SERVICE, origin, token)
        except self._errors.KeyringError as exc:
            return f"the OS keychain refused it ({exc})"
        return None

    def delete(self, origin: str) -> bool:
        """Remove the stored token; True when there was one."""
        if not self.available:
            return False
        try:
            self._keyring.delete_password(KEYRING_SERVICE, origin)
        except self._errors.PasswordDeleteError:
            return False
        except self._errors.KeyringError:
            return False
        return True


class CredentialFile:
    """``credentials.json``, mode 0600, for when the keychain cannot take the key."""

    def __init__(self, directory: Path) -> None:
        self.path = directory / "credentials.json"

    def get(self, origin: str) -> str | None:
        value = _read_json(self.path).get(origin)
        return value if isinstance(value, str) and value else None

    def set(self, origin: str, token: str) -> None:
        data = _read_json(self.path)
        data[origin] = token
        _write_private_json(self.path, data)

    def delete(self, origin: str) -> bool:
        data = _read_json(self.path)
        if origin not in data:
            return False
        del data[origin]
        if data:
            _write_private_json(self.path, data)
        else:
            self.path.unlink(missing_ok=True)
        return True


class LoginRecord:
    """``auth.json``: what fpt knows about each server's login. Holds no secret."""

    def __init__(self, directory: Path) -> None:
        self.path = directory / "auth.json"

    def get(self, origin: str) -> dict[str, Any]:
        entry = _read_json(self.path).get(origin)
        return cast("dict[str, Any]", entry) if isinstance(entry, dict) else {}

    def set(self, origin: str, entry: dict[str, Any]) -> None:
        data = _read_json(self.path)
        data[origin] = entry
        _write_private_json(self.path, data)

    def delete(self, origin: str) -> None:
        data = _read_json(self.path)
        if data.pop(origin, None) is None:
            return
        if data:
            _write_private_json(self.path, data)
        else:
            self.path.unlink(missing_ok=True)


@dataclass
class Credential:
    """A key and where it came from. ``repr`` never shows the key."""

    token: str
    source: str
    origin: str

    def __repr__(self) -> str:
        return f"Credential(source={self.source!r}, origin={self.origin!r})"


@dataclass
class Stores:
    """Everything that reads or writes a credential, so tests can replace any of it."""

    keychain: Keychain
    file: CredentialFile
    record: LoginRecord

    @classmethod
    def default(cls, env: Mapping[str, str] | None = None) -> Stores:
        directory = config_dir(env)
        return cls(Keychain(), CredentialFile(directory), LoginRecord(directory))


def resolve_credential(
    origin: str, stores: Stores, env: Mapping[str, str] | None = None
) -> Credential | None:
    """The key fpt sends to ``origin``: the environment's, else the keychain's, else the file's."""
    source = os.environ if env is None else env
    from_env = source.get(API_KEY_ENV, "").strip()
    if from_env:
        return Credential(from_env, SOURCE_ENV, origin)
    readers: list[tuple[str, Callable[[str], str | None]]] = [
        (SOURCE_KEYCHAIN, stores.keychain.get),
        (SOURCE_FILE, stores.file.get),
    ]
    # A login the keychain refused went to the file, but a locked keychain still answers
    # reads, so the key it holds may be an older login's. Read the store the record names.
    if stores.record.get(origin).get("store") == SOURCE_FILE:
        readers.reverse()
    for name, read in readers:
        token = read(origin)
        if token:
            return Credential(token, name, origin)
    return None


def require_credential(
    origin: str, stores: Stores, env: Mapping[str, str] | None = None
) -> Credential:
    """:func:`resolve_credential`, or exit 5 when there is none."""
    credential = resolve_credential(origin, stores, env)
    if credential is None:
        raise FptError(
            ExitCode.AUTH,
            f"not signed in to {origin}",
            f"Run `fpt auth login`, or set {API_KEY_ENV} for a script. "
            "Do not paste a key into the conversation.",
            source="credentials",
        )
    return credential


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def _send(request: urllib.request.Request, *, what: str) -> dict[str, Any]:
    """Send ``request`` and return its JSON body, mapping failures to fpt's exit codes.

    A 401 or 403 is exit 5 with the hint to log in again: the server issues no refresh
    token, so a new login is the only recovery.
    """
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        detail = _error_detail(exc)
        if exc.code in (401, 403):
            raise FptError(
                ExitCode.AUTH,
                f"{what}: the server refused the credential ({exc.code}{detail})",
                _RELOGIN_ERROR_HINT,
                source="server",
            ) from exc
        code = ExitCode.SERVER if exc.code >= 500 else ExitCode.VALIDATION
        raise FptError(
            code,
            f"{what}: HTTP {exc.code}{detail}",
            "Try again; if it persists, run `fpt auth login` again from the start.",
            source="server",
        ) from exc
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise FptError(
            ExitCode.NETWORK,
            f"{what}: cannot reach {request.full_url.split('?')[0]} ({reason})",
            "Check the network, or that the server's host is allowed in the sandbox.",
            source="network",
        ) from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise FptError(
            ExitCode.SERVER,
            f"{what}: the server's answer is larger than {MAX_RESPONSE_BYTES} bytes",
            "Try again; if it persists, the server is misbehaving.",
            source="server",
        )
    try:
        parsed: Any = json.loads(body)
    except ValueError as exc:
        raise FptError(
            ExitCode.SERVER,
            f"{what}: the server's answer is not JSON",
            "Try again; if it persists, the server is misbehaving.",
            source="server",
        ) from exc
    if not isinstance(parsed, dict):
        raise FptError(
            ExitCode.SERVER,
            f"{what}: the server's answer is not a JSON object",
            "Try again; if it persists, the server is misbehaving.",
            source="server",
        )
    return cast("dict[str, Any]", parsed)


def _error_detail(exc: urllib.error.HTTPError) -> str:
    """The OAuth ``error`` code from an error body, never anything that could hold a secret."""
    try:
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return ""
        body: Any = json.loads(raw)
    except (ValueError, OSError):
        return ""
    if isinstance(body, dict):
        error = cast("dict[str, Any]", body).get("error")
        if isinstance(error, str):
            return f", {error}"
    return ""


def _post_json(url: str, payload: dict[str, Any], *, what: str) -> dict[str, Any]:
    request = build_request(
        url,
        method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    return _send(request, what=what)


def _post_form(url: str, payload: dict[str, str], *, what: str) -> dict[str, Any]:
    request = build_request(
        url,
        method="POST",
        data=urllib.parse.urlencode(payload).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    return _send(request, what=what)


def verify_key(origin: str, credential: Credential) -> dict[str, Any]:
    """Ask the server who ``credential`` belongs to: ``user_id`` and ``key_prefix``."""
    request = build_request(f"{origin}/auth/verify-key", headers={"Accept": "application/json"})
    # Unredirected: urllib copies ordinary headers onto a redirect, to any host or scheme.
    request.add_unredirected_header("Authorization", f"Bearer {credential.token}")
    return _send(request, what="checking the key")


# ---------------------------------------------------------------------------
# Login: PKCE, the listener, and the pasted URL
# ---------------------------------------------------------------------------


def pkce_pair() -> tuple[str, str]:
    """A PKCE ``code_verifier`` and its S256 ``code_challenge`` (RFC 7636)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


class _CallbackHandler(BaseHTTPRequestHandler):
    """Answers the browser's request to the loopback redirect and hands its URL over."""

    def do_GET(self) -> None:  # noqa: N802 - the http.server hook name
        parsed = urllib.parse.urlsplit(self.path)
        owner = cast("_CallbackServer", self.server)
        if parsed.path == "/" and owner.authorize_url:
            # The short link printed for this machine: the authorize URL is long enough to
            # wrap in a terminal, and clicking a wrapped link opens only its first line.
            self.send_response(302)
            self.send_header("Location", owner.authorize_url)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return
        owner.results.put(("listener", f"{owner.redirect_uri}?{parsed.query}"))
        body = (
            b"<!doctype html><meta charset=utf-8><title>fpt</title>"
            b"<p>fpt received the sign-in. You can close this tab.</p>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Silence http.server's request log: it would print the code to stderr."""


class _CallbackServer(HTTPServer):
    def __init__(self, results: queue.Queue[tuple[str, str]]) -> None:
        super().__init__(("127.0.0.1", 0), _CallbackHandler)
        self.results = results
        self.origin = f"http://127.0.0.1:{self.server_address[1]}"
        self.redirect_uri = f"{self.origin}{CALLBACK_PATH}"
        self.authorize_url = ""


@contextmanager
def _listener(results: queue.Queue[tuple[str, str]]) -> Generator[_CallbackServer, None, None]:
    server = _CallbackServer(results)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def _read_pasted(stream: TextIO, results: queue.Queue[tuple[str, str]]) -> None:
    """Put the first non-empty line of ``stream`` on ``results``."""
    try:
        for line in stream:
            if line.strip():
                results.put(("paste", line.strip()))
                return
    except (OSError, ValueError):
        return


def parse_callback(url: str, *, redirect_uri: str, expected_state: str) -> str:
    """The authorization code from a callback URL, after checking ``state``.

    A wrong ``state`` is exit 2: it means the URL belongs to a different sign-in, and using
    its code would sign in to whatever that one was for.
    """
    parsed = urllib.parse.urlsplit(url.strip())
    expected = urllib.parse.urlsplit(redirect_uri)
    if (parsed.scheme, parsed.netloc, parsed.path) != (
        expected.scheme,
        expected.netloc,
        expected.path,
    ):
        raise FptError(
            ExitCode.VALIDATION,
            "the pasted URL is not this sign-in's callback",
            f"Paste the whole URL from the hand-off page's copy box; it starts with {redirect_uri}.",
            source="callback",
        )
    params = urllib.parse.parse_qs(parsed.query)
    if params.get("state", [""])[0] != expected_state:
        raise FptError(
            ExitCode.VALIDATION,
            "the callback's state does not match this sign-in",
            "That URL is from a different sign-in. Run `fpt auth login` again and use the "
            "URL from the page it opens.",
            source="callback",
            pointer="/state",
        )
    if "error" in params:
        raise FptError(
            ExitCode.AUTH,
            f"sign-in was not completed ({params['error'][0]})",
            "Run `fpt auth login` again.",
            source="callback",
        )
    code = params.get("code", [""])[0]
    if not code:
        raise FptError(
            ExitCode.VALIDATION,
            "the callback URL carries no code",
            "Paste the whole URL from the hand-off page's copy box.",
            source="callback",
            pointer="/code",
        )
    return code


def _await_code(
    results: queue.Queue[tuple[str, str]], timeout: float, *, redirect_uri: str, state: str
) -> str:
    """The authorization code from the first callback that belongs to this sign-in.

    Anything on this machine can reach the listener, and a web page can make the browser
    request it, so a callback with the wrong ``state`` is ignored rather than allowed to end
    the sign-in. A pasted URL is the user's own, so a wrong one is reported at once.
    """
    timed_out = FptError(
        ExitCode.AUTH,
        f"no sign-in arrived within {int(timeout)} seconds",
        "Run `fpt auth login` again, and click Continue or paste the URL from the hand-off page.",
        source="callback",
    )
    deadline = time.monotonic() + timeout
    while True:
        # Checked before each read: a queue kept full by forged callbacks never raises Empty.
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise timed_out
        try:
            how, callback_url = results.get(timeout=remaining)
        except queue.Empty as exc:
            raise timed_out from exc
        try:
            return parse_callback(callback_url, redirect_uri=redirect_uri, expected_state=state)
        except FptError as error:
            if how == "listener" and error.pointer == "/state":
                continue
            raise


@dataclass
class LoginIO:
    """What login talks to besides the server, so tests can drive it."""

    open_browser: Callable[[str], bool]
    stdin: TextIO
    stderr: TextIO
    timeout: float = LOGIN_TIMEOUT_SECONDS

    @classmethod
    def default(cls) -> LoginIO:
        return cls(webbrowser.open, sys.stdin, sys.stderr)


def login(
    origin: str,
    stores: Stores,
    io: LoginIO,
    *,
    open_browser: bool = True,
) -> dict[str, Any]:
    """Sign in to ``origin`` and store the key; return what ``auth login`` reports."""
    results: queue.Queue[tuple[str, str]] = queue.Queue()
    with _listener(results) as server:
        redirect_uri = server.redirect_uri
        client = _post_json(
            f"{origin}/oauth/register",
            {
                "client_name": CLIENT_NAME,
                "redirect_uris": [redirect_uri],
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
            what="registering fpt with the server",
        )
        client_id = client.get("client_id")
        if not isinstance(client_id, str) or not client_id:
            raise FptError(
                ExitCode.SERVER,
                "registering fpt with the server: no client_id in the answer",
                "Try again; if it persists, the server is misbehaving.",
                source="server",
            )
        verifier, challenge = pkce_pair()
        state = secrets.token_urlsafe(32)
        authorize_url = f"{origin}/oauth/authorize?" + urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
            }
        )
        server.authorize_url = authorize_url
        short_url = f"{server.origin}/"

        opened = False
        if open_browser:
            try:
                opened = bool(io.open_browser(authorize_url))
            except Exception:  # noqa: BLE001 - any failure to open means "print the URL"
                opened = False
        if opened:
            lead = "Opened your browser to sign in."
        else:
            lead = (
                f"Open this link on this machine to sign in:\n{short_url}\n\n"
                "Or, from a browser on another device, open:"
            )
        io.stderr.write(
            f"{lead}\n{authorize_url}\n\n"
            "After signing in, click Continue on the page that follows.\n"
            "If this machine's browser cannot reach fpt (over SSH, or on another device), "
            "copy the URL from that page's box and paste it here, then press Enter.\n"
        )
        io.stderr.flush()

        reader = threading.Thread(target=_read_pasted, args=(io.stdin, results), daemon=True)
        reader.start()
        code = _await_code(results, io.timeout, redirect_uri=redirect_uri, state=state)

    token_response = _post_form(
        f"{origin}/oauth/token",
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
        },
        what="exchanging the sign-in code",
    )
    token = token_response.get("access_token")
    if not isinstance(token, str) or not token:
        raise FptError(
            ExitCode.SERVER,
            "exchanging the sign-in code: no access_token in the answer",
            "Run `fpt auth login` again.",
            source="server",
        )
    expires_at = None
    expires_in = token_response.get("expires_in")
    if isinstance(expires_in, int) and expires_in > 0:
        expires_at = _iso(time.time() + expires_in)

    identity = verify_key(origin, Credential(token, "login", origin))

    warnings: list[str] = []
    refused = stores.keychain.set(origin, token)
    if refused is None:
        store = SOURCE_KEYCHAIN
        stores.file.delete(origin)
    else:
        stores.file.set(origin, token)
        store = SOURCE_FILE
        warning = f"The key is stored in {stores.file.path} (mode 0600) because {refused}."
        if "-25308" in refused:
            warning += (
                " The macOS login keychain is locked in this session; run "
                "`security unlock-keychain` and `fpt auth login` again to move the key "
                "into it."
            )
        warnings.append(warning)
    stores.record.set(
        origin,
        {
            "user_id": identity.get("user_id"),
            "key_prefix": identity.get("key_prefix"),
            "expires_at": expires_at,
            "store": store,
        },
    )
    return {
        "data": {
            "server": origin,
            "signed_in": True,
            "source": store,
            "user_id": identity.get("user_id"),
            "key_prefix": identity.get("key_prefix"),
            "expires_at": expires_at,
        },
        "warnings": warnings,
    }


def _iso(timestamp: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))


# ---------------------------------------------------------------------------
# Status and logout
# ---------------------------------------------------------------------------


def status(origin: str, stores: Stores, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Who ``origin`` knows fpt as. Exit 5 when not signed in or the key is refused."""
    credential = require_credential(origin, stores, env)
    identity = verify_key(origin, credential)
    record = stores.record.get(origin) if credential.source != SOURCE_ENV else {}
    return {
        "server": origin,
        "signed_in": True,
        "source": credential.source,
        "user_id": identity.get("user_id"),
        "key_prefix": identity.get("key_prefix"),
        "expires_at": record.get("expires_at"),
    }


def logout(origin: str, stores: Stores, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Delete the stored key for ``origin``; return what ``auth logout`` reports."""
    removed: list[str] = []
    if stores.keychain.delete(origin):
        removed.append(SOURCE_KEYCHAIN)
    if stores.file.delete(origin):
        removed.append(SOURCE_FILE)
    stores.record.delete(origin)
    source = os.environ if env is None else env
    warnings: list[str] = [
        "The key itself stays valid until it expires. To revoke it now, sign in at "
        f"{origin}/auth/api-keys in a browser."
    ]
    if source.get(API_KEY_ENV, "").strip():
        warnings.append(f"{API_KEY_ENV} is still set, so fpt keeps using that key.")
    return {"data": {"server": origin, "removed": removed}, "warnings": warnings}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _cmd_login(args: argparse.Namespace) -> int:
    origin = server_origin()
    result = login(origin, Stores.default(), LoginIO.default(), open_browser=not args.no_browser)
    return emit(envelope(result["data"], warnings=result["warnings"]))


def _cmd_status(_args: argparse.Namespace) -> int:
    origin = server_origin()
    return emit(envelope(status(origin, Stores.default())))


def _cmd_logout(_args: argparse.Namespace) -> int:
    origin = server_origin()
    result = logout(origin, Stores.default())
    return emit(envelope(result["data"], warnings=result["warnings"]))


_AUTH_DESCRIPTION = f"""\
Sign fpt in to FinPlan, and see or remove that sign-in.

The server is {DEFAULT_SERVER} unless {SERVER_ENV} names another. {API_KEY_ENV} in the
environment wins over a stored sign-in, for CI and scripts. No command prints a key.
"""


def register_auth(subparsers: Any) -> None:
    """Add ``fpt auth login | status | logout``."""
    parser = subparsers.add_parser(
        "auth",
        help="sign in to FinPlan, show who is signed in, or sign out",
        description=_AUTH_DESCRIPTION,
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    actions = parser.add_subparsers(
        dest="auth_command", metavar="<login|status|logout>", parser_class=type(parser)
    )
    actions.required = True

    login_parser = actions.add_parser(
        "login",
        help="sign in through the browser and store the key",
        description="Sign in through the browser (OAuth with PKCE) and store the key in the "
        "OS keychain, or in a mode-0600 file when the keychain cannot take it (none exists, "
        "or it is locked). Click Continue on the page "
        "that follows sign-in; over SSH, paste the URL from that page instead. The key lasts "
        "30 days and cannot be refreshed: log in again when it expires.",
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    login_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="print the sign-in URL instead of opening a browser, and wait for the pasted "
        "callback URL",
    )
    login_parser.set_defaults(func=_cmd_login)

    status_parser = actions.add_parser(
        "status",
        help="show who is signed in, from which source, and when the key expires",
        description="Show the server, the signed-in user, where the key comes from "
        f"({SOURCE_ENV}, {SOURCE_KEYCHAIN} or {SOURCE_FILE}), the key's public "
        "key_prefix and its expiry. Exits 5 when not signed in or the key is refused.",
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    status_parser.set_defaults(func=_cmd_status)

    logout_parser = actions.add_parser(
        "logout",
        help="delete the stored key",
        description="Delete the stored key. The key stays valid until it expires; revoke "
        "it at /auth/api-keys in a browser to end it now.",
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    logout_parser.set_defaults(func=_cmd_logout)


__all__ = [
    "API_KEY_ENV",
    "Credential",
    "CredentialFile",
    "Keychain",
    "LoginIO",
    "LoginRecord",
    "Stores",
    "login",
    "logout",
    "parse_callback",
    "pkce_pair",
    "register_auth",
    "require_credential",
    "resolve_credential",
    "server_origin",
    "status",
    "verify_key",
]
