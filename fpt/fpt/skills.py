"""``fpt skills``: install the skill that describes this fpt into a coding agent.

The skill is an Agent Skills folder (``SKILL.md``) shipped inside the package, in
``fpt/skill/``. Installing copies it into the agent's own skills directory, so the
skill an agent reads always describes the fpt installed beside it; run ``install``
again after upgrading fpt.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

from fpt import __version__
from fpt.exit_codes import EXIT_CODES_HELP, ExitCode
from fpt.output import FptError, emit, envelope

SKILL_NAME = "fpt"
_SKILL_FILE = "SKILL.md"


def _home() -> Path:
    return Path.home()


def _env_dir(variable: str, default: Path) -> Path:
    value = os.environ.get(variable, "")
    return Path(value).expanduser() if value else default


# Each agent's user-level skills directory. Claude Code and Codex move theirs with
# their config directory; OpenCode keeps its config under XDG_CONFIG_HOME.
AGENTS: dict[str, Callable[[], Path]] = {
    "claude": lambda: _env_dir("CLAUDE_CONFIG_DIR", _home() / ".claude") / "skills",
    "codex": lambda: _env_dir("CODEX_HOME", _home() / ".codex") / "skills",
    "cursor": lambda: _home() / ".cursor" / "skills",
    "gemini": lambda: _home() / ".gemini" / "skills",
    "opencode": lambda: _env_dir("XDG_CONFIG_HOME", _home() / ".config") / "opencode" / "skills",
}


def skills_dir(agent: str) -> Path:
    """The directory ``agent`` loads user skills from."""
    return AGENTS[agent]()


def skill_text() -> str:
    """The ``SKILL.md`` this version of fpt ships."""
    return resources.files("fpt").joinpath("skill", _SKILL_FILE).read_text(encoding="utf-8")


def _description(text: str) -> str:
    """The ``description`` from ``SKILL.md``'s front matter."""
    for line in text.split("\n")[1:]:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            return line[len("description:") :].strip()
    return ""


def _cmd_list(args: argparse.Namespace) -> int:
    """Print the skill this fpt ships and where each agent would load it from."""
    del args
    agents = {name: str(skills_dir(name) / SKILL_NAME) for name in AGENTS}
    installed = sorted(name for name, path in agents.items() if Path(path, _SKILL_FILE).is_file())
    skill = {
        "name": SKILL_NAME,
        "description": _description(skill_text()),
        "fpt_version": __version__,
    }
    return emit(envelope({"skills": [skill], "agents": agents, "installed": installed}))


def _cmd_install(args: argparse.Namespace) -> int:
    """Write the skill into ``args.agent``'s skills directory, replacing an older copy."""
    target = skills_dir(args.agent) / SKILL_NAME
    path = target / _SKILL_FILE
    text = skill_text()
    replaced = path.is_file()
    try:
        target.mkdir(parents=True, exist_ok=True)
        temporary = target / f".{_SKILL_FILE}.tmp-{os.getpid()}"
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    except OSError as exc:
        raise FptError(
            ExitCode.LOCAL_IO,
            f"cannot write {str(path)!r}: {exc}",
            f"Check that {str(target.parent)!r} is writable, or create it and retry.",
            source="arguments",
        ) from exc
    data = {
        "agent": args.agent,
        "skill": SKILL_NAME,
        "path": str(path),
        "replaced": replaced,
        "fpt_version": __version__,
    }
    return emit(envelope(data))


def register_skills(subparsers: Any) -> None:
    """Add ``fpt skills`` with its ``list`` and ``install`` subcommands."""
    parser = subparsers.add_parser(
        "skills",
        help="install the skill that describes this fpt into a coding agent",
        description="The skill tells an agent how to save FinPlan state with fpt. It "
        "ships with fpt, so reinstall it after upgrading fpt.",
        epilog=EXIT_CODES_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(
        dest="skills_command",
        metavar="<list|install>",
        parser_class=type(parser),
        required=True,
    )
    listing = commands.add_parser(
        "list", help="show the skill this fpt ships and each agent's skills directory"
    )
    listing.set_defaults(func=_cmd_list)
    install = commands.add_parser("install", help="copy the skill into an agent's skills directory")
    install.add_argument("agent", choices=sorted(AGENTS), help="the agent to install it for")
    install.set_defaults(func=_cmd_install)
