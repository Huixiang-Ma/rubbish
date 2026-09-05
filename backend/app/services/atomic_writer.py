import json
import os
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.services.hash_utils import sha256_text


class AtomicWriter:
    def write_text(self, path: Path, content: str) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        try:
            with tmp_path.open("w", encoding="utf-8", newline="\n") as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            self._replace_with_retry(tmp_path, path)
            digest = sha256_text(content)
            hash_path = path.with_suffix(path.suffix + ".sha256")
            hash_tmp_path = hash_path.with_name(f"{hash_path.name}.{uuid4().hex}.tmp")
            with hash_tmp_path.open("w", encoding="utf-8", newline="\n") as file:
                file.write(digest)
                file.flush()
                os.fsync(file.fileno())
            self._replace_with_retry(hash_tmp_path, hash_path)
            return digest
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def write_json(self, path: Path, data: Any) -> str:
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return self.write_text(path, content)

    def verify_sha256(self, path: Path, expected_hash: str) -> bool:
        if not path.exists():
            return False
        return sha256_text(path.read_text(encoding="utf-8")) == expected_hash

    def _replace_with_retry(self, source: Path, target: Path) -> None:
        for attempt in range(5):
            try:
                os.replace(source, target)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
