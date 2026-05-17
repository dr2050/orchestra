#!/usr/bin/env python3

import importlib.util
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent


def _load_local_orchestrator():
    spec = importlib.util.spec_from_file_location(
        "feature_phase_test_orchestrator",
        SCRIPT_DIR / "orchestrator.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["feature_phase_test_orchestrator"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


orchestrator = _load_local_orchestrator()


class ResolveOrchestraDirTests(unittest.TestCase):
    def test_requires_orchestra_dir_env(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "ORCHESTRA_DIR is not set"):
                orchestrator.resolve_orchestra_dir()

    def test_accepts_valid_orchestra_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestra_dir = Path(tmpdir)
            (orchestra_dir / "feature-phase-orchestration" / "prompts").mkdir(parents=True)

            with patch.dict(os.environ, {"ORCHESTRA_DIR": str(orchestra_dir)}, clear=True):
                resolved = orchestrator.resolve_orchestra_dir()

            self.assertEqual(resolved, orchestra_dir.resolve())


class DrainAgentOutputTests(unittest.TestCase):
    def close_quietly(self, stream) -> None:
        try:
            stream.close()
        except OSError:
            pass
        except ValueError:
            pass

    def make_pipe(self):
        read_fd, write_fd = os.pipe()
        read_stream = os.fdopen(read_fd, "rb", buffering=0)
        write_stream = os.fdopen(write_fd, "wb", buffering=0)
        self.addCleanup(self.close_quietly, read_stream)
        self.addCleanup(self.close_quietly, write_stream)
        return read_stream, write_stream

    def test_captures_split_outcome_without_trailing_newline(self):
        read_stream, write_stream = self.make_pipe()
        captured: list[str] = []

        thread = threading.Thread(
            target=orchestrator.drain_agent_output,
            args=(read_stream, captured),
            daemon=True,
        )
        thread.start()

        write_stream.write(b"progress\rOUT")
        write_stream.write(b"COME: done")
        write_stream.close()

        thread.join(timeout=1)

        self.assertFalse(thread.is_alive(), "drain thread should exit after writer closes")
        self.assertEqual(captured, ["OUTCOME: done"])

    def test_closing_read_stream_unblocks_lingering_writer(self):
        read_stream, write_stream = self.make_pipe()
        captured: list[str] = []

        thread = threading.Thread(
            target=orchestrator.drain_agent_output,
            args=(read_stream, captured),
            daemon=True,
        )
        thread.start()

        write_stream.write(b"still running")
        time.sleep(0.05)
        read_stream.close()

        thread.join(timeout=1)

        self.assertFalse(thread.is_alive(), "drain thread should exit when the read side closes")
        self.assertEqual(captured, [])


if __name__ == "__main__":
    unittest.main()
