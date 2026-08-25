from __future__ import annotations
import enum
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class RuntimePreference(str, enum.Enum):
    """
    User-selected runtime preference.

    AUTO   - Resolve the best available runtime using hardware assessment.
    NATIVE - Always prefer the native CPU binary runtime.
             If native is unavailable or unsuitable, report clearly.
             Do NOT silently fallback to another runtime.
    DOCKER - Always prefer the Docker container runtime.
             If Docker is unavailable, report clearly.
             Do NOT silently fallback to another runtime.

    REMOTE is reserved for future use (abstraction kept open).
    """
    AUTO   = "auto"
    NATIVE = "native"
    DOCKER = "docker"
    # REMOTE = "remote"  # Reserved - not implemented yet


@dataclass
class RuntimePreferenceStore:
    """Persists the user runtime preference to disk."""
    preference: RuntimePreference = RuntimePreference.AUTO
    dismissed_recommendation: bool = False
    last_assessment_ts: Optional[str] = None

    @classmethod
    def load(cls, path: Path) -> RuntimePreferenceStore:
        """Load from JSON file, returning defaults if file does not exist or is corrupt."""
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return cls(
                    preference=RuntimePreference(data.get("preference", "auto")),
                    dismissed_recommendation=data.get("dismissed_recommendation", False),
                    last_assessment_ts=data.get("last_assessment_ts"),
                )
        except Exception:
            pass
        return cls()

    def save(self, path: Path) -> None:
        """Persist current preference to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "preference": self.preference.value,
            "dismissed_recommendation": self.dismissed_recommendation,
            "last_assessment_ts": self.last_assessment_ts,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


_preference_store: Optional[RuntimePreferenceStore] = None
_preference_path = Path("data/runtime_preference.json")


def get_preference_store() -> RuntimePreferenceStore:
    global _preference_store
    if _preference_store is None:
        _preference_store = RuntimePreferenceStore.load(_preference_path)
    return _preference_store


def set_preference(pref: RuntimePreference) -> RuntimePreferenceStore:
    global _preference_store
    store = get_preference_store()
    store.preference = pref
    store.save(_preference_path)
    _preference_store = store
    return store
