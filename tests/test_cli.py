import subprocess
import sys


def test_version():
    r = subprocess.run([sys.executable, "-m", "sherpa.cli", "--version"], capture_output=True, text=True)
    assert r.returncode == 0
    assert r.stdout.startswith("sherpa ")


def test_help_lists_all_commands():
    r = subprocess.run([sys.executable, "-m", "sherpa.cli", "--help"], capture_output=True, text=True)
    assert r.returncode == 0
    for cmd in ("scan", "plan", "apply", "status"):
        assert cmd in r.stdout
