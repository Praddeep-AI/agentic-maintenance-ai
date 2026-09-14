"""
Configuration loader — reads config.yaml and provides a cached config dict.
"""
from __future__ import annotations

import pathlib
from functools import lru_cache
from typing import Any

_CONFIG_PATH = pathlib.Path(__file__).parent / "config.yaml"


@lru_cache(maxsize=1)
def get_config() -> dict[str, Any]:
    """Return the parsed config.yaml as a dict. Cached after first load."""
    try:
        import yaml  # type: ignore
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Fallback minimal config without PyYAML
        return {
            "system": {"offline_mode": True, "log_level": "INFO"},
            "financials": {
                "production_rate_usd_per_hour": 85000,
                "product_margin_pct": 0.22,
                "ai_system_annual_cost_usd": 250000,
                "labor_rate_usd_per_hour": 95,
                "contractor_rate_usd_per_hour": 145,
            },
            "workflow": {"approval_timeout_minutes": 30},
        }
    except Exception:
        return {}
