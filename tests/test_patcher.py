import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from python_engine.patcher.patcher import WorkspacePatcher

class TestWorkspacePatcher(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "scratch_patcher"))
        os.makedirs(self.test_dir, exist_ok=True)
        self.patcher = WorkspacePatcher(workspace_root=self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            import shutil
            shutil.rmtree(self.test_dir)

    def test_patch_and_commit(self):
        rel = "test_file.py"
        self.patcher.apply_patch(rel, "content_v1")
        file_abs = os.path.join(self.test_dir, rel)
        self.assertTrue(os.path.exists(file_abs))
        with open(file_abs) as f:
            self.assertEqual(f.read(), "content_v1")

        self.patcher.commit()
        # Rollback should do nothing after commit
        self.patcher.rollback_all()
        self.assertTrue(os.path.exists(file_abs))

    def test_patch_and_rollback(self):
        rel = "original.py"
        file_abs = os.path.join(self.test_dir, rel)
        with open(file_abs, "w") as f:
            f.write("original_code")

        # Apply flawed patch
        self.patcher.apply_patch(rel, "broken_code")
        with open(file_abs) as f:
            self.assertEqual(f.read(), "broken_code")

        # Rollback
        self.patcher.rollback_all()
        with open(file_abs) as f:
            self.assertEqual(f.read(), "original_code")

    def test_new_file_rollback_deletes(self):
        rel = "newly_created.py"
        file_abs = os.path.join(self.test_dir, rel)
        self.assertFalse(os.path.exists(file_abs))

        self.patcher.apply_patch(rel, "new_code")
        self.assertTrue(os.path.exists(file_abs))

        # Rollback should delete newly created file
        self.patcher.rollback_all()
        self.assertFalse(os.path.exists(file_abs))

if __name__ == "__main__":
    unittest.main()
