"""
retry_failed.py — retry failed uploads. Separate from run_full_workflow.py. See WORKFLOW.md.

    python retry_failed.py                                   # every failed_uploads/failed_uploads_*.csv
    python retry_failed.py failed_uploads/failed_uploads_X.csv

Runs maintenance/retry_failed_uploads.py with the project's venv. Videos already
delivered are skipped; anything that fails again goes to
failed_uploads/second_fail_<time>.csv.
"""
import subprocess
import sys
from pathlib import Path

from run_full_workflow import PYTHON, ROOT

if __name__ == "__main__":
    command = [PYTHON, "-u", "-m", "maintenance.retry_failed_uploads", *(str(Path(a).resolve()) for a in sys.argv[1:])]
    raise SystemExit(subprocess.call(command, cwd=ROOT))
