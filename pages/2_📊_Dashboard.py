"""
Page 2: Full Executive Dashboard
Streamlit multipage — accessible via sidebar navigation
"""
import sys, pathlib
_here = pathlib.Path(__file__).resolve()
for _p in [_here.parent.parent, _here.parent.parent.parent]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "dashboard_app",
    _here.parent.parent / "dashboard" / "app.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
