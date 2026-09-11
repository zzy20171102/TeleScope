import sys
import tempfile
import unittest
from pathlib import Path

from telescope import schedule


class TestSchedule(unittest.TestCase):
    def test_write_bat(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bat = schedule.write_bat(root, python_exe="C:/Python314/python.exe")
            self.assertEqual(bat, root / "scripts" / "daily_task.bat")
            self.assertTrue(bat.exists())
            text = bat.read_text(encoding="utf-8")
            self.assertIn("@echo off", text)
            self.assertIn("cd /d", text)
            self.assertIn("telescope run", text)
            self.assertIn("daily_run.log", text)
            self.assertIn("C:/Python314/python.exe", text)
            # extra args keep the redirect separated
            bat2 = schedule.write_bat(root, python_exe="py",
                                      extra_args="--hours 48")
            self.assertIn("run --hours 48 >>", bat2.read_text(encoding="utf-8"))

    def test_command_builders(self):
        cmd = schedule.build_create_command("TeleScopeDaily", "07:00",
                                            Path("D:/w/scripts/daily_task.bat"))
        self.assertEqual(cmd[0], "schtasks")
        self.assertIn("/Create", cmd)
        self.assertIn("/TN", cmd)
        self.assertIn("TeleScopeDaily", cmd)
        self.assertIn("/SC", cmd)
        self.assertIn("DAILY", cmd)
        self.assertIn("/ST", cmd)
        self.assertIn("07:00", cmd)
        self.assertIn("/F", cmd)
        self.assertIn("daily_task.bat", cmd[cmd.index("/TR") + 1])
        dele = schedule.build_delete_command("TeleScopeDaily")
        self.assertEqual(dele[:3], ["schtasks", "/Delete", "/TN"])
        query = schedule.build_query_command("TeleScopeDaily")
        self.assertEqual(query[:3], ["schtasks", "/Query", "/TN"])


if __name__ == "__main__":
    unittest.main()
