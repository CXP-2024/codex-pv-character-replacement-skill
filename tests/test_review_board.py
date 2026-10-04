import importlib.util
from pathlib import Path
import tempfile
import unittest
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "skills/codex-pv-character-replacement/scripts/review_board.py"
spec = importlib.util.spec_from_file_location("review_board", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReviewBoardTests(unittest.TestCase):
    def test_real_overlay_and_header_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            Image.new("RGB", (100, 50), "red").save(p / "a.png")
            Image.new("RGB", (100, 50), "blue").save(p / "b.png")
            size = m.make_board(p / "a.png", p / "b.png", p / "out.png", 100)
            self.assertEqual(size, (300, 90))
            with Image.open(p / "out.png") as out:
                self.assertEqual(out.getpixel((250, 70)), (127, 0, 127))
            with self.assertRaises(FileExistsError):
                m.make_board(p / "a.png", p / "b.png", p / "out.png", 100)

    def test_resize_is_explicit_and_aspect_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            Image.new("RGB", (100, 50)).save(p / "a.png")
            Image.new("RGB", (200, 100)).save(p / "b.png")
            with self.assertRaises(ValueError):
                m.make_board(p / "a.png", p / "b.png", p / "out.png", 0)
            m.make_board(p / "a.png", p / "b.png", p / "ok.png", 0, True)
            Image.new("RGB", (100, 100)).save(p / "square.png")
            with self.assertRaises(ValueError):
                m.make_board(p / "a.png", p / "square.png", p / "bad.png", 0, True)
