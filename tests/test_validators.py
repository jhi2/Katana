import os
import tempfile
import unittest

from validators import (
    ValidationError,
    validate_file_path,
    validate_gcode,
    validate_ip_address,
    validate_printer_profile,
    validate_selection_data,
    validate_temperature_range,
    validate_bed_dimensions,
    validate_nozzle_size,
    validate_filament_diameter,
)


class ValidatorTests(unittest.TestCase):
    def test_validate_ip_address_allows_empty(self):
        self.assertEqual(validate_ip_address(""), "")
        self.assertEqual(validate_ip_address("   "), "")

    def test_validate_ip_address_allows_host_forms(self):
        self.assertEqual(validate_ip_address("localhost"), "localhost")
        self.assertEqual(validate_ip_address("localhost:7125"), "localhost:7125")
        self.assertEqual(validate_ip_address("printer.local"), "printer.local")
        self.assertEqual(validate_ip_address("printer.local:80"), "printer.local:80")
        self.assertEqual(validate_ip_address("http://192.168.1.2:7125"), "http://192.168.1.2:7125")
        self.assertEqual(validate_ip_address("https://printer.local/"), "https://printer.local/")

    def test_validate_ip_address_rejects_bad_ports(self):
        with self.assertRaises(ValidationError):
            validate_ip_address("localhost:99999")
        with self.assertRaises((ValidationError, ValueError)):
            validate_ip_address("http://localhost:99999")

    def test_validate_ip_address_rejects_garbage(self):
        with self.assertRaises(ValidationError):
            validate_ip_address("not a host")
        with self.assertRaises(ValidationError):
            validate_ip_address("http://")

    def test_validate_file_path_blocks_traversal(self):
        with self.assertRaises(ValidationError):
            validate_file_path("../secret.txt")
        with self.assertRaises(ValidationError):
            validate_file_path("/etc/passwd")

    def test_validate_file_path_scopes_to_base_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            expected = os.path.join(tmp, "config.json")
            resolved = validate_file_path("config.json", base_dir=tmp)
            self.assertEqual(resolved, expected)

    def test_validate_gcode_sanitizes_and_limits(self):
        cleaned = validate_gcode("G1 X1 Y2 ; ok\nM104 S200\n")
        self.assertIn("G1 X1 Y2", cleaned)
        # Disallow obvious injection characters
        cleaned = validate_gcode("G1 X1 Y2 $()`")
        self.assertNotIn("$", cleaned)
        self.assertNotIn("`", cleaned)

        with self.assertRaises(ValidationError):
            validate_gcode("G1 X1\n" + ("G" * 10001))

    def test_validate_printer_profile_happy_path(self):
        profile = {
            "name": "Test Printer",
            "manufacturer": "Katana",
            "ip_address": "localhost:7125",
            "bed_size": [220, 220, 250],
            "nozzle_size": 0.4,
            "filament_diameter": 1.75,
            "hotend_temp": {"min": 180, "max": 260},
            "bed_temp": {"min": 0, "max": 80},
            "speed_settings": {
                "print_speed": 50,
                "travel_speed": 150,
                "infill_speed": 60,
                "outer_wall_speed": 40,
            },
            "retraction": {"enabled": True, "distance": 5, "speed": 45},
            "gcode_start": "G28",
            "gcode_end": "M104 S0",
        }
        validated = validate_printer_profile(profile)
        self.assertEqual(validated["name"], "Test Printer")
        self.assertEqual(validated["manufacturer"], "Katana")
        self.assertEqual(validated["ip_address"], "localhost:7125")
        self.assertEqual(validated["bed_size"], [220, 220, 250])

    def test_validate_printer_profile_rejects_bad_bed(self):
        profile = {
            "name": "Test Printer",
            "manufacturer": "Katana",
            "bed_size": [10, 10, 10],
            "nozzle_size": 0.4,
            "filament_diameter": 1.75,
            "hotend_temp": {"min": 180, "max": 260},
            "bed_temp": {"min": 0, "max": 80},
            "speed_settings": {
                "print_speed": 50,
                "travel_speed": 150,
                "infill_speed": 60,
                "outer_wall_speed": 40,
            },
            "retraction": {"enabled": True, "distance": 5, "speed": 45},
            "gcode_start": "G28",
            "gcode_end": "M104 S0",
        }
        with self.assertRaises(ValidationError):
            validate_printer_profile(profile)

    def test_validate_selection_data(self):
        index, profile_type = validate_selection_data({"index": 0, "type": "prebuilt"})
        self.assertEqual(index, 0)
        self.assertEqual(profile_type, "prebuilt")
        with self.assertRaises(ValidationError):
            validate_selection_data({"index": -1, "type": "prebuilt"})
        with self.assertRaises(ValidationError):
            validate_selection_data({"index": 0, "type": "unknown"})

    def test_validate_temperature_range(self):
        self.assertEqual(validate_temperature_range(180, 260), (180, 260))
        with self.assertRaises(ValidationError):
            validate_temperature_range(260, 180)

    def test_validate_bed_dimensions(self):
        self.assertEqual(validate_bed_dimensions(220, 220, 250), (220, 220, 250))
        with self.assertRaises(ValidationError):
            validate_bed_dimensions(10, 220, 250)

    def test_validate_nozzle_and_filament(self):
        self.assertEqual(validate_nozzle_size(0.4), 0.4)
        self.assertEqual(validate_filament_diameter(1.75), 1.75)
        with self.assertRaises(ValidationError):
            validate_nozzle_size(5)
        with self.assertRaises(ValidationError):
            validate_filament_diameter(3.0)


if __name__ == "__main__":
    unittest.main()
