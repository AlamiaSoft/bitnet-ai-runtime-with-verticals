from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Callable, List, Optional
from bitnet_runtime.logging import logger

class DirectoryWatcher:
    """Watches local directories for new/modified documents to index."""

    def __init__(self, directories: List[str | Path], on_new_file: Callable[[Path], Any]):
        self.directories = [Path(d) for d in directories]
        self.on_new_file = on_new_file
        self._seen_files = set()

    async def scan_once(self) -> int:
        count = 0
        for d in self.directories:
            if not d.exists() or not d.is_dir():
                continue
            for f in d.glob("**/*"):
                if f.is_file() and str(f.resolve()) not in self._seen_files:
                    self._seen_files.add(str(f.resolve()))
                    try:
                        if asyncio.iscoroutinefunction(self.on_new_file):
                            await self.on_new_file(f)
                        else:
                            self.on_new_file(f)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error handling new file {f}: {e}")
        return count
