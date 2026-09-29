"""Verify the freshly packaged executable without downloading a model."""
import json
import subprocess
import sys
from pathlib import Path

binary = Path(sys.argv[1]).resolve()
for args, expected in [(["--help"], "Usage"), (["vault-server", "--help"], "vault"), (["--runtime-smoke"], "runtime_imports")]:
    result = subprocess.run([str(binary), *args], capture_output=True, text=True, timeout=300)
    if result.returncode or expected not in result.stdout:
        raise SystemExit(f"Frozen smoke failed: {args}\n{result.stdout}\n{result.stderr}")
    if args == ["--runtime-smoke"]:
        assert len(json.loads(result.stdout)["runtime_imports"]) == 6
print("Frozen CLI and native runtime imports passed")
