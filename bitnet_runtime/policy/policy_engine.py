from __future__ import annotations
import enum
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from ..logging import logger

class PolicyDecision(enum.Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"

@dataclass
class PolicyEvaluationResult:
    decision: PolicyDecision
    reason: str
    sanitized_input: Optional[Dict[str, Any]] = None

class SecurityPolicyEngine:
    """
    First-class capability and policy evaluation engine enforcing
    deterministic security constraints on agent tool executions.
    """

    # High-risk commands and shell injection patterns
    CRITICAL_PATTERNS = [
        r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+[/\\*]",     # rm -rf / or rm -rf *
        r"del\s+/[sS]\s+/[qQ]\s+[a-zA-Z]:\\",        # del /s /q C:\
        r"format\s+[a-zA-Z]:",                       # format drive
        r"mkfs",                                     # make filesystem
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",     # fork bomb
        r"curl\s+.*\|\s*(sh|bash|powershell|cmd|zsh)",# curl pipe to shell
        r"wget\s+.*\|\s*(sh|bash|powershell|cmd|zsh)",# wget pipe to shell
        r">\s*/dev/sd[a-z]",                         # overwrite disk
        r"dd\s+if=.*of=/dev/",                       # dd raw write
        r"shutdown",                                 # system shutdown
        r"reboot",                                   # system reboot
        r"base64\s+-[a-zA-Z]*d.*\|\s*(sh|bash)",     # base64 decode pipe to shell
        r"(iex|Invoke-Expression)\s+",               # powershell iex
        r"powershell\s+.*-(e|enc|encodedcommand)",   # encoded powershell
    ]

    def __init__(
        self,
        strict_mode: bool = False,
        allowed_commands: Optional[Set[str]] = None,
        blocked_commands: Optional[Set[str]] = None,
        ask_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        self.strict_mode = strict_mode
        self.allowed_commands = allowed_commands
        self.blocked_commands = blocked_commands or set()
        self.ask_callback = ask_callback
        self._compiled_critical_patterns = [re.compile(p, re.IGNORECASE) for p in self.CRITICAL_PATTERNS]

    def _split_subcommands(self, command: str) -> List[str]:
        """Splits chained commands across shell delimiters (; , && , || , | , newlines, subshells)."""
        # Extract subshell contents: $(...) or `...`
        subshells = re.findall(r"\$\((.*?)\)|`([^`]+)`", command)
        extracted = []
        for s1, s2 in subshells:
            sub = s1 or s2
            if sub.strip():
                extracted.append(sub.strip())

        # Split on standard command separators
        parts = re.split(r"(?:;|\&\&|\|\||\||\n)", command)
        all_cmds = [p.strip() for p in parts if p.strip()] + extracted
        return all_cmds

    def evaluate_shell_command(self, command: str, working_dir: Path) -> PolicyEvaluationResult:
        cmd_clean = command.strip()
        if not cmd_clean:
            return PolicyEvaluationResult(PolicyDecision.DENY, "Empty command string.")

        # 1. Critical pattern check across entire command string
        for pattern in self._compiled_critical_patterns:
            if pattern.search(cmd_clean):
                return PolicyEvaluationResult(
                    PolicyDecision.DENY,
                    f"Command matched critical dangerous execution pattern: '{pattern.pattern}'",
                )

        # 2. Inspect all chained sub-commands
        sub_commands = self._split_subcommands(cmd_clean)
        for sub in sub_commands:
            # Check critical patterns in sub-commands
            for pattern in self._compiled_critical_patterns:
                if pattern.search(sub):
                    return PolicyEvaluationResult(
                        PolicyDecision.DENY,
                        f"Sub-command '{sub}' matched dangerous pattern: '{pattern.pattern}'",
                    )

            first_token = sub.split()[0].lower() if sub.split() else ""
            # Strip common path prefixes (e.g. /usr/bin/rm -> rm)
            first_token_name = Path(first_token).name.lower()

            if first_token in self.blocked_commands or first_token_name in self.blocked_commands:
                return PolicyEvaluationResult(
                    PolicyDecision.DENY,
                    f"Command '{first_token}' is explicitly blocked.",
                )

            # 3. Allowlist check if strict_mode is on
            if self.strict_mode and self.allowed_commands is not None:
                if first_token not in self.allowed_commands and first_token_name not in self.allowed_commands:
                    if self.ask_callback:
                        approved = self.ask_callback(cmd_clean, {"working_dir": str(working_dir), "sub_command": sub})
                        if approved:
                            return PolicyEvaluationResult(PolicyDecision.ALLOW, "Approved by user confirmation.")
                        return PolicyEvaluationResult(PolicyDecision.DENY, "Denied by user confirmation.")
                    return PolicyEvaluationResult(
                        PolicyDecision.ASK,
                        f"Command '{first_token}' requires explicit user confirmation (ASK).",
                    )

        return PolicyEvaluationResult(PolicyDecision.ALLOW, "Command passed security policy verification.")

    def evaluate_filesystem_access(self, target_path: Path, base_dir: Path, is_write: bool = False) -> PolicyEvaluationResult:
        try:
            resolved_target = target_path.resolve()
            resolved_base = base_dir.resolve()
            resolved_target.relative_to(resolved_base)
            return PolicyEvaluationResult(PolicyDecision.ALLOW, "Path is within allowed workspace boundary.")
        except ValueError:
            return PolicyEvaluationResult(
                PolicyDecision.DENY,
                f"Path traversal denied: '{target_path}' is outside base directory '{base_dir}'",
            )
