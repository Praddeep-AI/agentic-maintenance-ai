"""
Streamlit Community Cloud entry point.
Main file path (in Streamlit Cloud settings): streamlit_app.py

On Streamlit Cloud the repo is mounted at:
  /mount/src/agentic-maintenance-ai/

So this file lives at:
  /mount/src/agentic-maintenance-ai/streamlit_app.py

And the package code lives at:
  /mount/src/agentic-maintenance-ai/agents/
  /mount/src/agentic-maintenance-ai/workflow/
  etc.

The dashboard imports everything as `agentic_maintenance.*`, so we create
a virtual `agentic_maintenance` package that points back to this directory.
"""
import sys
import types
import pathlib

HERE = pathlib.Path(__file__).parent          # repo root on Cloud
sys.path.insert(0, str(HERE))                  # lets `from workflow.x import y` work

# ── Create `agentic_maintenance` as a namespace alias for THIS directory ──────
# This makes `from agentic_maintenance.workflow.x import y` resolve to
# `from workflow.x import y` relative to HERE.
pkg = types.ModuleType("agentic_maintenance")
pkg.__path__ = [str(HERE)]
pkg.__package__ = "agentic_maintenance"
pkg.__spec__ = None
sys.modules["agentic_maintenance"] = pkg

# ── Run the dashboard ─────────────────────────────────────────────────────────
import importlib.util

spec = importlib.util.spec_from_file_location(
    "agentic_maintenance.dashboard.app",
    HERE / "dashboard" / "app.py",
)
mod = importlib.util.module_from_spec(spec)
mod.__package__ = "agentic_maintenance.dashboard"
sys.modules["agentic_maintenance.dashboard.app"] = mod
spec.loader.exec_module(mod)
