import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/codex-pv-character-replacement/scripts/pv_manifest.py"
spec = importlib.util.spec_from_file_location("pv_manifest", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ManifestTests(unittest.TestCase):
    def test_maps_endpoints_monotonic_and_bounds(self):
        for source in (1, 2, 28, 53, 56, 137):
            for target in (1, 2, 28, 56):
                a = m.frame_map(source, target)
                self.assertEqual(len(a), target)
                self.assertEqual(a[0], 0)
                self.assertEqual(a, sorted(a))
                self.assertTrue(all(0 <= x < source for x in a))
                if target > 1:
                    self.assertEqual(a[-1], source - 1)
        self.assertEqual(m.frame_map(2, 3), [0, 1, 1])
        with self.assertRaises(ValueError):
            m.frame_map(0, 56)

    def setup_project(self, root):
        profile = dict(max_width=1024, max_height=576, dimension_step=32,
                       max_model_frames=56, frame_step=17, frame_offset=5,
                       max_source_frames=53, max_references=3)
        job = dict(id="s001a", start=100, end=128, mode="Ref2VA", width=1024,
                   height=576, model_frames=56, steps=20, seed=1, cast=["new"],
                   prompt="prompt.txt", source="source.bin",
                   references=[dict(path="ref.bin", role="identity")])
        for name in ("prompt.txt", "source.bin", "ref.bin"):
            (root / name).write_bytes(b"original")
        for name, obj in (("job.json", job), ("profile.json", profile)):
            (root / name).write_text(json.dumps(obj))
        return job, profile

    def test_packet_tamper_and_revocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.setup_project(root)
            packet = m.freeze(root, "job.json", "profile.json")
            m.emit(packet, root / "request.json")
            approval = dict(job_id="s001a", reviewer="User", approved=True,
                            request_sha256=m.digest(root / "request.json"))
            (root / "approval.json").write_text(json.dumps(approval))
            self.assertEqual(m.verify_packet(root, "request.json", "approval.json", "User")["technical_validation"], "PASS")
            approval["approved"] = False
            (root / "approval.json").write_text(json.dumps(approval))
            with self.assertRaises(ValueError):
                m.verify_packet(root, "request.json", "approval.json", "User")
            (root / "ref.bin").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                m.verify_packet(root, "request.json")

    def test_caps_and_fl_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            job, profile = self.setup_project(Path(tmp))
            for key, val in (("height", 468), ("model_frames", 73), ("end", 200)):
                bad = dict(job, **{key: val})
                with self.assertRaises(ValueError):
                    m.validate_job(bad, profile)
            with self.assertRaises(ValueError):
                m.validate_job(dict(job, cast=[]), profile)
            fl = dict(job, mode="FL2VA", references=[
                dict(path="first.png", role="first"), dict(path="last.png", role="last")])
            m.validate_job(fl, profile)
            fl["references"].reverse()
            with self.assertRaises(ValueError):
                m.validate_job(fl, profile)

    def test_ledger_coverage_routing_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frame.bin").write_bytes(b"native")
            row = dict(frame=100, path="frame.bin", asset_frame=0,
                       sha256=m.digest(root / "frame.bin"), kind="generated",
                       selected=True, sr=True)
            ledger = dict(start=100, end=102, fps=[24, 1],
                          frames=[row, dict(row, frame=101)])
            self.assertEqual(m.validate_ledger(root, ledger)["frames"], 2)
            ledger["frames"][1]["frame"] = 100
            with self.assertRaises(ValueError):
                m.validate_ledger(root, ledger)
            ledger["frames"][1] = dict(row, frame=101, kind="copy")
            with self.assertRaises(ValueError):
                m.validate_ledger(root, ledger)
            ledger["frames"][1] = dict(row, frame=101, sha256="bad")
            with self.assertRaises(ValueError):
                m.validate_ledger(root, ledger)

    def test_path_escape_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                m.local_file(root, "../secret")
            m.emit({"saved": True}, root / "once.json")
            with self.assertRaises(FileExistsError):
                m.emit({"saved": False}, root / "once.json")


if __name__ == "__main__":
    unittest.main()
