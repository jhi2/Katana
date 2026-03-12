import os
import tempfile
import unittest

from print3r_parser import (
    parse_ini_file,
    _safe_slug,
    _resolve_model_url_to_path,
    _infer_plate_index,
)


class Print3rParserTests(unittest.TestCase):
    def test_parse_ini_file_reads_simple_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            ini_path = os.path.join(tmp, "test.ini")
            with open(ini_path, "w") as f:
                f.write("alpha=1\n")
                f.write("beta = two\n")
                f.write("; comment\n")
                f.write("# comment\n")
                f.write("invalid_line\n")
            data = parse_ini_file(ini_path)
            self.assertEqual(data["alpha"], "1")
            self.assertEqual(data["beta"], "two")
            self.assertNotIn("invalid_line", data)

    def test_safe_slug_falls_back(self):
        self.assertEqual(_safe_slug("", "fallback"), "fallback")
        self.assertEqual(_safe_slug("  ", "fallback"), "fallback")
        self.assertEqual(_safe_slug("Hello World", "fallback"), "Hello_World")

    def test_resolve_model_url_to_path(self):
        base = "/tmp/katana"
        self.assertEqual(
            _resolve_model_url_to_path("/static/uploads/a.stl", base),
            os.path.join(base, "static", "uploads", "a.stl"),
        )
        self.assertEqual(
            _resolve_model_url_to_path("/demo/block.stl", base),
            os.path.join(base, "block.stl"),
        )
        self.assertEqual(
            _resolve_model_url_to_path("relative/file.stl", base),
            os.path.join(base, "relative/file.stl"),
        )

    def test_infer_plate_index(self):
        model = {"position": {"x": 0}}
        self.assertEqual(_infer_plate_index(model, 1, 220, 50), 0)

        model = {"position": {"x": 270}}
        self.assertEqual(_infer_plate_index(model, 2, 220, 50), 1)

        model = {"position": {"x": -999}}
        self.assertEqual(_infer_plate_index(model, 2, 220, 50), 0)

        model = {"position": {"x": 9999}}
        self.assertEqual(_infer_plate_index(model, 2, 220, 50), 1)


if __name__ == "__main__":
    unittest.main()
