import os
import shutil
from typing import Dict, Optional

class WorkspacePatcher:
    """Manages transactional file modifications, snapshots, and rollbacks in the workspace."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = os.path.abspath(workspace_root)
        self.backups: Dict[str, Optional[str]] = {}

    def apply_patch(self, rel_path: str, new_content: str) -> str:
        """Applies code changes transactionally, creating a backup if file existed."""
        target_abs = os.path.abspath(os.path.join(self.workspace_root, rel_path))

        # Snapshot original state before write
        if rel_path not in self.backups:
            if os.path.exists(target_abs):
                with open(target_abs, "r", encoding="utf-8") as f:
                    self.backups[rel_path] = f.read()
            else:
                self.backups[rel_path] = None # File did not exist originally

        os.makedirs(os.path.dirname(target_abs), exist_ok=True)
        with open(target_abs, "w", encoding="utf-8") as f:
            f.write(new_content)

        return target_abs

    def rollback_all(self):
        """Reverts all modified files to their original state prior to the loop."""
        for rel_path, original_content in self.backups.items():
            target_abs = os.path.abspath(os.path.join(self.workspace_root, rel_path))
            if original_content is None:
                # File was newly created, remove it
                if os.path.exists(target_abs):
                    os.remove(target_abs)
            else:
                # Restore original content
                with open(target_abs, "w", encoding="utf-8") as f:
                    f.write(original_content)
        self.backups.clear()

    def commit(self):
        """Commits the patch transaction, clearing stored backups."""
        self.backups.clear()
