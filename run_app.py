"""
QueryGuard Master Application Runner
Launches both the FastAPI backend and Streamlit executive dashboard in one command.
Automatically frees ports, initializes default baselines, and opens the dashboard.
"""

import os
import sys
import time
import subprocess
import signal

def print_banner():
    print("\n" + "═" * 74)
    print("  🛡️  QUERYGUARD: EXECUTIVE OBSERVABILITY & REGRESSION SOLVER")
    print("═" * 74)

def free_port(port: int):
    """Kills any process currently listening on the specified port."""
    try:
        cmd = f"lsof -ti:{port}"
        pids = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip().split()
        for pid in pids:
            if pid:
                os.kill(int(pid), signal.SIGKILL)
    except Exception:
        pass

def main():
    print_banner()

    # Step 1: Clean any existing stale processes on ports 8000 & 8501
    print("[1/3] Clearing ports 8000 and 8501...")
    free_port(8000)
    free_port(8501)
    time.sleep(0.5)

    python_bin = sys.executable
    project_dir = os.path.abspath(os.path.dirname(__file__))

    # Step 2: Launch FastAPI Backend
    print("[2/3] Launching FastAPI Backend on http://localhost:8000...")
    backend_proc = subprocess.Popen(
        [python_bin, "-m", "backend.main"],
        cwd=project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Allow backend to bind and seed baselines
    time.sleep(2)

    # Step 3: Launch Streamlit Dashboard
    print("[3/3] Launching Executive Streamlit Dashboard on http://localhost:8501...")
    streamlit_cmd = [
        python_bin, "-m", "streamlit", "run",
        "frontend/streamlit_app.py",
        "--server.port=8501",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]

    streamlit_proc = subprocess.Popen(
        streamlit_cmd,
        cwd=project_dir
    )

    print("\n" + "═" * 74)
    print("  ✅  ALL SERVICES ARE RUNNING!")
    print("  👉  Executive Dashboard (Frontend):  http://localhost:8501")
    print("  👉  FastAPI OpenAPI Docs (Backend):   http://localhost:8000/docs")
    print("═" * 74)
    print("  Press CTRL+C in this terminal at any time to stop all services.\n")

    def shutdown(sig, frame):
        print("\nStopping QueryGuard services...")
        backend_proc.terminate()
        streamlit_proc.terminate()
        free_port(8000)
        free_port(8501)
        print("Done. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep alive while child processes run
    try:
        streamlit_proc.wait()
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == "__main__":
    main()
