"""How fpt identifies itself on every HTTP request.

Every request is built by :func:`build_request`, which always sets
``User-Agent: fpt/<version>``, plus an ``ai-agent <name>`` token when a coding agent is
recognised from its environment variables (the convention DataDog's ``pup`` uses).
Detection changes nothing else: output, help and behaviour are the same for people and
agents. It labels requests the server already receives and sends nothing new.

Agents have no standard variable yet. The ones read here, most specific name first:

* ``AI_AGENT``: a proposed standard that carries the agent's name; Claude Code sets it
  (e.g. ``claude-code_2-1-316_agent``).
* ``CLAUDECODE=1``: Claude Code.
* ``CODEX_CI`` or ``CODEX_THREAD_ID``: Codex.
* ``AGENT``: Goose sets its name (``AGENT=goose``); Bun's convention is ``AGENT=1``,
  which names no agent. A false value (``0``, ``false``, ``no``) means no agent, so a
  shell that sets ``AGENT=0`` is not tagged ``ai-agent 0``.
"""

from __future__ import annotations

import os
import re
import urllib.request
from collections.abc import Mapping

from fpt import __version__

_UNNAMED_AGENT = "unknown"
# How a flag-style AGENT reads: a boolean, not a name.
_TRUE_VALUES = frozenset({"1", "true", "yes"})
_FALSE_VALUES = frozenset({"0", "false", "no"})
# RFC 9110 `tchar`, the characters a User-Agent product token may hold.
_NOT_TOKEN_CHAR = re.compile(r"[^!#$%&'*+.^_`|~0-9A-Za-z-]+")
_MAX_NAME_LENGTH = 64


def _token(value: str) -> str:
    """``value`` as a User-Agent token: disallowed characters become ``-``, length capped."""
    cleaned = _NOT_TOKEN_CHAR.sub("-", value.strip()).strip("-")
    return cleaned[:_MAX_NAME_LENGTH] or _UNNAMED_AGENT


def detect_agent(env: Mapping[str, str] | None = None) -> str | None:
    """The coding agent fpt is running under, or None when none is recognised."""
    source = os.environ if env is None else env
    named = source.get("AI_AGENT", "").strip()
    if named:
        return _token(named)
    if source.get("CLAUDECODE", "").strip():
        return "claude-code"
    if source.get("CODEX_CI", "").strip() or source.get("CODEX_THREAD_ID", "").strip():
        return "codex"
    generic = source.get("AGENT", "").strip()
    if not generic or generic.lower() in _FALSE_VALUES:
        return None
    return _UNNAMED_AGENT if generic.lower() in _TRUE_VALUES else _token(generic)


def user_agent(env: Mapping[str, str] | None = None) -> str:
    """``fpt/<version>``, plus ``ai-agent <name>`` when an agent is detected."""
    base = f"fpt/{__version__}"
    agent = detect_agent(env)
    return f"{base} ai-agent {agent}" if agent else base


def build_request(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: Mapping[str, str] | None = None,
    env: Mapping[str, str] | None = None,
) -> urllib.request.Request:
    """A request for ``url`` carrying fpt's User-Agent.

    The User-Agent is set last, so a caller's ``headers`` cannot replace it: every request
    fpt sends identifies the version, which is how the server can answer an old one with
    ``Deprecation`` and ``Sunset``.
    """
    request = urllib.request.Request(url, data=data, method=method)
    for name, value in (headers or {}).items():
        request.add_header(name, value)
    request.add_header("User-Agent", user_agent(env))
    return request
