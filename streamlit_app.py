"""
Streamlit Community Cloud entry point — Page 1: Industrial AI Transformation Showcase
Main file path in Streamlit Cloud settings: streamlit_app.py

Structure:
  streamlit_app.py            → Page 1: Showcase (this file)
  pages/2_📊_Dashboard.py    → Page 2: Full Executive Dashboard
"""
import sys
import types
import pathlib

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))

# Create `agentic_maintenance` namespace alias pointing to this directory
pkg = types.ModuleType("agentic_maintenance")
pkg.__path__ = [str(HERE)]
pkg.__package__ = "agentic_maintenance"
pkg.__spec__ = None
sys.modules["agentic_maintenance"] = pkg

# Run the showcase as the main page
import importlib.util
spec = importlib.util.spec_from_file_location(
    "agentic_maintenance.dashboard.showcase",
    HERE / "dashboard" / "showcase.py",
)
mod = importlib.util.module_from_spec(spec)
mod.__package__ = "agentic_maintenance.dashboard"
sys.modules["agentic_maintenance.dashboard.showcase"] = mod
spec.loader.exec_module(mod)
