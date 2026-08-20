from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from building_code_ast.evidence.artifact_hydration import verify_local_artifact
from building_code_ast.evidence.source_packages import Artifact


class ArtifactHydrationTests(unittest.TestCase):
    def test_verify_local_artifact_uses_exact_artifact_identity_without_source_id(self) -> None:
        payload = b"exact retained derivative bytes"
        artifact = Artifact(
            object_key="engineering-sources/example/derivatives/component.bin",
            sha256=hashlib.sha256(payload).hexdigest(),
            size=len(payload),
            media_type="application/octet-stream",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "component.bin"
            path.write_bytes(payload)
            receipt = verify_local_artifact(artifact, path)
        self.assertEqual(receipt.artifact_id, artifact.artifact_id)
        self.assertEqual(receipt.object_key, artifact.object_key)
        self.assertEqual(receipt.sha256, artifact.sha256)

    def test_verify_local_artifact_fails_closed_on_wrong_bytes(self) -> None:
        payload = b"expected"
        artifact = Artifact(
            object_key="engineering-sources/example/source.bin",
            sha256=hashlib.sha256(payload).hexdigest(),
            size=len(payload),
            media_type="application/octet-stream",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.bin"
            path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "size mismatch|sha256 mismatch"):
                verify_local_artifact(artifact, path)


if __name__ == "__main__":
    unittest.main()
