"""
Streamlit Community Cloud entry point.
Main file path (in Streamlit Cloud settings): streamlit_app.py
"""
import sys
import pathlib

# Add this directory to path so `agentic_maintenance` package is importable
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))

# Run the dashboard
import importlib.util
spec = importlib.util.spec_from_file_location(
    "dashboard",
    HERE / "dashboard" / "app.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
