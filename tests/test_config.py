from __future__ import annotations

import unittest
from pathlib import Path

from src.config import PROJECT_ROOT, resolve_upload_dir


class UploadDirectoryConfigTest(unittest.TestCase):
    def test_uses_project_upload_directory_locally(self) -> None:
        self.assertEqual(
            resolve_upload_dir({}),
            PROJECT_ROOT / "data" / "uploads",
        )

    def test_uses_tmp_directory_on_vercel(self) -> None:
        self.assertEqual(
            resolve_upload_dir({"VERCEL": "1"}),
            Path("/tmp/askly-uploads"),
        )

    def test_explicit_upload_directory_takes_priority(self) -> None:
        self.assertEqual(
            resolve_upload_dir(
                {"VERCEL": "1", "UPLOAD_DIR": "/tmp/custom-uploads"}
            ),
            Path("/tmp/custom-uploads"),
        )


if __name__ == "__main__":
    unittest.main()
