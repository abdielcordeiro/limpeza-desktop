# -*- coding: utf-8 -*-
"""Repositório local de Snapshots para reversão (Undo) idempotente."""
import os
import re
import json
from typing import List, Optional
from src.domain.entities import StateSnapshot
from src.domain.ports import ISnapshotRepositoryPort


class SnapshotRepository(ISnapshotRepositoryPort):
    """Persiste e recupera snapshots de estado do sistema em arquivos JSON locais."""

    def __init__(self, snapshots_dir: Optional[str] = None) -> None:
        if snapshots_dir is None:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            snapshots_dir = os.path.join(project_root, "outputs", "snapshots")
        self.snapshots_dir = snapshots_dir
        os.makedirs(self.snapshots_dir, exist_ok=True)

    @staticmethod
    def _sanitize_id(snapshot_id: str) -> str:
        if not isinstance(snapshot_id, str):
            return ""
        raw_base = os.path.basename(snapshot_id.strip())
        if raw_base.endswith(".json"):
            raw_base = raw_base[:-5]
        return re.sub(r"[^a-zA-Z0-9_-]", "", raw_base)

    def _filepath(self, snapshot_id: str) -> str:
        clean_id = self._sanitize_id(snapshot_id)
        if not clean_id:
            clean_id = "invalid"
        if not clean_id.startswith("snapshot_"):
            clean_id = f"snapshot_{clean_id}"
        return os.path.join(self.snapshots_dir, f"{clean_id}.json")

    def save_snapshot(self, snapshot: StateSnapshot) -> str:
        os.makedirs(self.snapshots_dir, exist_ok=True)
        path = self._filepath(snapshot.snapshot_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            return None
        if snapshot_id.strip() == "latest":
            return self.get_latest_snapshot()
        clean_id = self._sanitize_id(snapshot_id)
        if not clean_id or ".." in snapshot_id or "/" in snapshot_id or "\\" in snapshot_id:
            return None
        path = self._filepath(clean_id)
        if not os.path.exists(path):
            alt_path = os.path.join(self.snapshots_dir, f"{clean_id}.json")
            if os.path.exists(alt_path):
                path = alt_path
            else:
                return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return StateSnapshot(
                snapshot_id=data.get("snapshot_id", ""),
                created_at=data.get("created_at", ""),
                os_platform=data.get("os_platform", ""),
                mode=data.get("mode", "real"),
                entries=data.get("entries", {}),
                tweaks_applied=data.get("tweaks_applied", []),
                description=data.get("description", ""),
            )
        except (OSError, json.JSONDecodeError):
            return None

    def get_latest_snapshot(self) -> Optional[StateSnapshot]:
        snapshots = self.list_snapshots()
        return snapshots[0] if snapshots else None

    def list_snapshots(self) -> List[StateSnapshot]:
        if not os.path.exists(self.snapshots_dir):
            return []
        result: List[StateSnapshot] = []
        try:
            files = [
                f for f in os.listdir(self.snapshots_dir)
                if f.endswith(".json") and f.startswith("snapshot_")
            ]
            files.sort(reverse=True)
            for fname in files:
                fpath = os.path.join(self.snapshots_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    result.append(
                        StateSnapshot(
                            snapshot_id=data.get("snapshot_id", fname.replace(".json", "")),
                            created_at=data.get("created_at", ""),
                            os_platform=data.get("os_platform", ""),
                            mode=data.get("mode", "real"),
                            entries=data.get("entries", {}),
                            tweaks_applied=data.get("tweaks_applied", []),
                            description=data.get("description", ""),
                        )
                    )
                except (OSError, json.JSONDecodeError):
                    continue
        except OSError:
            return []
        return result
