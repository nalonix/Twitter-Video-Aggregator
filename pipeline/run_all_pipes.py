"""
Runs Pipe 1-7 in order. Pipe scripts live in this folder; they read and write
CSVs in the data folder (default: ../scrapped, or the first CLI argument).
"""
import os
import sys
import subprocess

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

# Force UTF-8 mode for all spawned Python subprocesses to prevent UnicodeEncodeError on Windows console
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

pipes = [
    "Pipe_1_Cut_New_Data.py",
    "Pipe_2_Remove_Empty.py",
    "Pipe_3_Type_Check_Default.py",
    "Pipe_4_Tag.py",
    "Pipe_5_Keywords.py",
    "Pipe_6_U_IDS.py",
    "Pipe_7_Timestamp.py",
]

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = (
    os.path.abspath(sys.argv[1])
    if len(sys.argv) > 1
    else os.path.join(os.path.dirname(script_dir), "scrapped")
)
python_executable = sys.executable
total = len(pipes)

for index, pipe in enumerate(pipes, start=1):
    print(f"\n{'=' * 60}", flush=True)
    print(f"[{index}/{total}] Running {pipe}...", flush=True)
    print(f"{'=' * 60}", flush=True)

    result = subprocess.run(
        [python_executable, "-u", os.path.join(script_dir, pipe)],
        cwd=data_dir,
    )
    if result.returncode != 0:
        print(f"\n❌ {pipe} failed with exit code {result.returncode}. Stopping.", flush=True)
        sys.exit(result.returncode)

    print(f"✅ {pipe} completed successfully.", flush=True)

print(f"\n✅ All {total} pipes executed successfully.", flush=True)
