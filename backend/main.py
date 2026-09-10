"""
QueryGuard Backend Service - FastAPI Application
Provides RESTful observability APIs, telemetry ingestion, plan comparison, and simulation endpoints.
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.api.endpoints import router as api_router
from detector.baseline import baseline_engine
from database.connection import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed default baselines
    print("\n" + "=" * 68)
    print("🚀 QueryGuard Backend Service Initialized")
    print("🔗 Localhost URL:      http://localhost:8000")
    print("📖 Interactive Docs:   http://localhost:8000/docs")
    print("=" * 68)
    try:
        baseline_engine.initialize_default_baselines()
        print("✅ Query baselines initialized successfully.\n")
    except Exception as e:
        print(f"Warning: could not pre-seed baselines on startup: {e}\n")
    yield
    print("QueryGuard backend shutting down.")

app = FastAPI(
    title="QueryGuard API",
    description="Query-Regression Detector Comparing Execution Plans for Multiplayer Applications Storing Rapidly Changing Session State.\n\n### 🛡️ [CLICK HERE TO OPEN EXECUTIVE OBSERVABILITY DASHBOARD](http://localhost:8501)",
    version="2.0.0",
    lifespan=lifespan
)

from fastapi.responses import RedirectResponse

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="http://localhost:8501")

app.include_router(api_router)

if __name__ == "__main__":
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("BACKEND_PORT", "8000"))

    # Automatically free port if a previous process is still bound
    import subprocess, signal
    try:
        curr_pid = os.getpid()
        pids = subprocess.check_output(f"lsof -ti:{port}", shell=True, stderr=subprocess.DEVNULL).decode().strip().split()
        for p in pids:
            pid = int(p)
            if pid != curr_pid:
                os.kill(pid, signal.SIGKILL)
    except Exception:
        pass

    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
