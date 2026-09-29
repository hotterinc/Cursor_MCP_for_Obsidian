import importlib.util
import sys
from pathlib import Path

ENTRY = Path(__file__).parents[1] / "src/obsidian_context_mcp/__main__.py"
spec = importlib.util.spec_from_file_location("sidecar_entry", ENTRY)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)

def test_frozen_help_is_cli(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "argv", ["sidecar.exe", "--help"])
    assert not entry._is_frozen_multiprocessing_reexec()

def test_frozen_worker_is_detected(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "argv", ["sidecar.exe", "--multiprocessing-fork", "parent_pid=1"])
    assert entry._is_frozen_multiprocessing_reexec()

def test_runtime_modules_are_not_excluded():
    text = (ENTRY.parents[2] / "obsidian-context-mcp.spec").read_text()
    excludes = text.split("excludes = [", 1)[1].split("]", 1)[0]
    assert '"unittest"' not in excludes
    assert '"torch.backends.cudnn"' not in excludes


def test_native_command_failure_is_not_ignored():
    import shutil
    import subprocess

    import pytest

    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        pytest.skip("PowerShell is unavailable")
    helper = ENTRY.parents[3] / "scripts/native.ps1"
    script = f". '{helper}'; Invoke-Native '{sys.executable}' @('-c', 'raise SystemExit(23)')"
    result = subprocess.run([shell, "-NoProfile", "-Command", script], capture_output=True)
    assert result.returncode != 0
    assert b"23" in result.stderr
