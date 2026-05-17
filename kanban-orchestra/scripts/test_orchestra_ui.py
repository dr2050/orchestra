#!/usr/bin/env python3
"""Tests for the Textual orchestra-ui quit flow."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "kanban-orchestra" / "scripts"
UI_PATH = REPO_ROOT / "orchestra-ui" / "orchestra-ui.py"

os.environ.setdefault("ORCHESTRA_DIR", str(REPO_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))


def _load_ui_module():
    spec = importlib.util.spec_from_file_location("orchestra_ui_test_module", UI_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["orchestra_ui_test_module"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


orchestra_ui = _load_ui_module()


class TestLogColorizer(unittest.TestCase):
    def test_picked_up_lines_are_blue(self):
        colored = orchestra_ui._colorize("Picked up: 'Allowed task' (step=commit-make)")

        self.assertIn("[blue]Picked up: 'Allowed task' (step=commit-make)[/blue]", colored)

    def test_warning_error_and_done_colors_are_preserved(self):
        self.assertIn("[red]Picked up after error[/red]", orchestra_ui._colorize("Picked up after error"))
        self.assertIn("[yellow]Picked up warning[/yellow]", orchestra_ui._colorize("Picked up warning"))
        self.assertIn("[green]Task done[/green]", orchestra_ui._colorize("Task done"))


class FakeProcess:
    def __init__(self, status="stopped", cmd=None):
        self.status = status
        self.cmd = cmd
        self.killed = False

    def kill(self):
        self.killed = True


class AppHarness:
    def __init__(self, processes):
        self.processes = processes
        self.exited = False
        self.pushed_screen = None
        self.pushed_callback = None

    def exit(self):
        self.exited = True

    def push_screen(self, screen, callback):
        self.pushed_screen = screen
        self.pushed_callback = callback


class TestQuitModal(unittest.TestCase):
    def test_cancel_button_dismisses_without_choice(self):
        modal = orchestra_ui.QuitModal()
        event = SimpleNamespace(button=SimpleNamespace(id="cancel-quit"))

        with patch.object(modal, "dismiss") as dismiss:
            modal.on_button_pressed(event)

        dismiss.assert_called_once_with(None)

    def test_existing_quit_choices_are_preserved(self):
        modal = orchestra_ui.QuitModal()

        for button_id, expected_result in (
            ("kill-quit", "kill"),
            ("leave-quit", "leave"),
        ):
            event = SimpleNamespace(button=SimpleNamespace(id=button_id))
            with self.subTest(button_id=button_id), patch.object(modal, "dismiss") as dismiss:
                modal.on_button_pressed(event)
                dismiss.assert_called_once_with(expected_result)


class TestOrchestraAppQuitFlow(unittest.TestCase):
    def test_quit_exits_immediately_when_no_managed_processes_are_running(self):
        app = AppHarness(
            [
                FakeProcess("stopped", cmd=["orchestrator"]),
                FakeProcess("exited(0)", cmd=["dashboard"]),
                FakeProcess("running", cmd=None),
            ]
        )

        orchestra_ui.OrchestraApp._do_quit(app)

        self.assertTrue(app.exited)
        self.assertIsNone(app.pushed_screen)

    def test_quit_dialog_cancel_keeps_running_processes_alive(self):
        orchestrator = FakeProcess("running", cmd=["orchestrator"])
        dashboard = FakeProcess("stopped", cmd=["dashboard"])
        app = AppHarness([orchestrator, dashboard])

        orchestra_ui.OrchestraApp._do_quit(app)

        self.assertFalse(app.exited)
        self.assertIsInstance(app.pushed_screen, orchestra_ui.QuitModal)

        app.pushed_callback(None)

        self.assertFalse(app.exited)
        self.assertFalse(orchestrator.killed)
        self.assertFalse(dashboard.killed)

    def test_quit_dialog_kill_and_leave_choices_still_exit(self):
        for choice in ("kill", "leave"):
            with self.subTest(choice=choice):
                orchestrator = FakeProcess("running", cmd=["orchestrator"])
                app = AppHarness([orchestrator])

                orchestra_ui.OrchestraApp._do_quit(app)
                app.pushed_callback(choice)

                self.assertTrue(app.exited)
                self.assertEqual(orchestrator.killed, choice == "kill")


if __name__ == "__main__":
    unittest.main()
