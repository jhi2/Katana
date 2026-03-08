import os
import unittest

from configmanager import ConfigManager


class ConfigManagerTests(unittest.TestCase):
    def setUp(self):
        self.cm = ConfigManager()
        self.test_config_path = os.path.join(self.cm.base_dir, "config.test.json")
        self.test_config_backup = self.test_config_path + ".bak"

    def tearDown(self):
        for path in [self.test_config_path, self.test_config_backup]:
            if os.path.exists(path):
                os.remove(path)

        test_project = os.path.join(self.cm.projects_dir, "UnitTestProject.json")
        if os.path.exists(test_project):
            os.remove(test_project)

    def test_save_and_load_config_round_trip(self):
        self.cm.config = {"printers": [{"data": {"name": "X"}}]}
        self.cm.save_config("config.test.json")

        reloaded = ConfigManager()
        reloaded.load_config("config.test.json")
        self.assertEqual(reloaded.config["printers"][0]["data"]["name"], "X")

    def test_save_project_rejects_invalid_sanitized_name(self):
        success, error = self.cm.save_project("////", {"demo": True})
        self.assertFalse(success)
        self.assertIn("no valid filename characters", error)

    def test_save_list_load_delete_project(self):
        success, filename = self.cm.save_project("UnitTestProject", {"hello": "world"})
        self.assertTrue(success)
        self.assertEqual(filename, "UnitTestProject.json")

        projects = self.cm.list_projects()
        self.assertTrue(any(p["filename"] == filename for p in projects))

        project_data = self.cm.load_project(filename)
        self.assertEqual(project_data["hello"], "world")

        self.assertTrue(self.cm.delete_project(filename))


if __name__ == "__main__":
    unittest.main()
