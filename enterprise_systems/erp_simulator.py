"""
Enterprise Systems Layer — ERP Simulator
Simulates SAP ERP / Oracle ERP material management, cost centers, and purchase orders.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simulated parts inventory
# ---------------------------------------------------------------------------
_INVENTORY: dict[str, dict] = {
    "SKF-6315-C3": {
        "part_number": "SKF-6315-C3",
        "description": "Deep groove ball bearing, 75mm bore, C3 clearance",
        "qty_on_hand": 4,
        "unit_cost_usd": 285.0,
        "lead_time_days": 3,
        "min_stock_level": 2,
        "vendor": "SKF Industrial",
        "storage_location": "Warehouse A, Bin 3-12",
        "last_updated": "2024-06-01",
    },
    "SKF-6316-C3": {
        "part_number": "SKF-6316-C3",
        "description": "Deep groove ball bearing, 80mm bore, C3 clearance",
        "qty_on_hand": 2,
        "unit_cost_usd": 310.0,
        "lead_time_days": 3,
        "min_stock_level": 2,
        "vendor": "SKF Industrial",
        "storage_location": "Warehouse A, Bin 3-13",
        "last_updated": "2024-06-01",
    },
    "bearing_housing_seal_kit": {
        "part_number": "bearing_housing_seal_kit",
        "description": "Bearing housing O-ring and gasket seal kit - Sulzer MBN-100",
        "qty_on_hand": 8,
        "unit_cost_usd": 95.0,
        "lead_time_days": 1,
        "min_stock_level": 4,
        "vendor": "Sulzer OEM Parts",
        "storage_location": "Warehouse A, Bin 1-05",
        "last_updated": "2024-05-15",
    },
    "suction_valve_stage1_K201": {
        "part_number": "suction_valve_stage1_K201",
        "description": "Suction valve assembly, Stage 1, Dresser-Rand DATUM-38",
        "qty_on_hand": 1,
        "unit_cost_usd": 4250.0,
        "lead_time_days": 14,
        "min_stock_level": 1,
        "vendor": "Dresser-Rand / Siemens",
        "storage_location": "Warehouse B, Bin 2-08",
        "last_updated": "2024-03-01",
    },
    "discharge_valve_stage1_K201": {
        "part_number": "discharge_valve_stage1_K201",
        "description": "Discharge valve assembly, Stage 1, Dresser-Rand DATUM-38",
        "qty_on_hand": 0,
        "unit_cost_usd": 4850.0,
        "lead_time_days": 21,
        "min_stock_level": 1,
        "vendor": "Dresser-Rand / Siemens",
        "storage_location": "OUT OF STOCK",
        "last_updated": "2024-04-15",
    },
    "valve_gasket_kit_K201": {
        "part_number": "valve_gasket_kit_K201",
        "description": "Valve gasket and seal kit, K-201 compressor",
        "qty_on_hand": 3,
        "unit_cost_usd": 380.0,
        "lead_time_days": 2,
        "min_stock_level": 2,
        "vendor": "Generic OEM",
        "storage_location": "Warehouse A, Bin 2-14",
        "last_updated": "2024-05-20",
    },
    "tube_bundle_E401_spare": {
        "part_number": "tube_bundle_E401_spare",
        "description": "Replacement tube bundle, E-401 TEMA AES-850, Stainless 316L",
        "qty_on_hand": 0,
        "unit_cost_usd": 38500.0,
        "lead_time_days": 60,
        "min_stock_level": 0,
        "vendor": "TEMA Custom Fabricators",
        "storage_location": "OUT OF STOCK - Long Lead",
        "last_updated": "2024-01-01",
    },
    "tube_plugs_x24": {
        "part_number": "tube_plugs_x24",
        "description": "SS316L tube plugs, set of 24, 25.4mm OD",
        "qty_on_hand": 6,
        "unit_cost_usd": 45.0,
        "lead_time_days": 1,
        "min_stock_level": 4,
        "vendor": "Mechanical Products Inc",
        "storage_location": "Warehouse A, Bin 5-02",
        "last_updated": "2024-04-01",
    },
    "gasket_set_E401": {
        "part_number": "gasket_set_E401",
        "description": "Full gasket replacement set, E-401",
        "qty_on_hand": 2,
        "unit_cost_usd": 1250.0,
        "lead_time_days": 5,
        "min_stock_level": 1,
        "vendor": "Flexitallic",
        "storage_location": "Warehouse B, Bin 1-11",
        "last_updated": "2024-02-15",
    },
    "PSV-501-spring-kit": {
        "part_number": "PSV-501-spring-kit",
        "description": "Spring replacement kit, Fisher ED Series PSV, 82 bar set",
        "qty_on_hand": 1,
        "unit_cost_usd": 620.0,
        "lead_time_days": 7,
        "min_stock_level": 1,
        "vendor": "Emerson / Fisher",
        "storage_location": "Warehouse A, Bin 4-03",
        "last_updated": "2024-03-10",
    },
    "PSV-501-seat-disc": {
        "part_number": "PSV-501-seat-disc",
        "description": "Seat disc assembly, Fisher ED Series PSV",
        "qty_on_hand": 2,
        "unit_cost_usd": 285.0,
        "lead_time_days": 5,
        "min_stock_level": 1,
        "vendor": "Emerson / Fisher",
        "storage_location": "Warehouse A, Bin 4-04",
        "last_updated": "2024-03-10",
    },
    "catalyst_bed_R301_full_charge": {
        "part_number": "catalyst_bed_R301_full_charge",
        "description": "Hydrotreating catalyst full charge, R-301 - Haldor Topsoe TK-574",
        "qty_on_hand": 0,
        "unit_cost_usd": 185000.0,
        "lead_time_days": 90,
        "min_stock_level": 0,
        "vendor": "Haldor Topsoe",
        "storage_location": "OUT OF STOCK - Procurement Required",
        "last_updated": "2024-01-01",
    },
    "insulation_cladding_T601_zone_A": {
        "part_number": "insulation_cladding_T601_zone_A",
        "description": "Mineral wool insulation + aluminum cladding, T-601 Zone A, 120m²",
        "qty_on_hand": 0,
        "unit_cost_usd": 22000.0,
        "lead_time_days": 30,
        "min_stock_level": 0,
        "vendor": "Industrial Insulation Ltd",
        "storage_location": "OUT OF STOCK",
        "last_updated": "2024-01-01",
    },
}

_RESERVATIONS: dict[str, list[dict]] = {}

_COST_CENTERS: dict[str, dict] = {
    "CDU": {"id": "CDU", "name": "Crude Distillation Unit", "budget_usd": 2500000, "ytd_spend_usd": 850000},
    "NHT": {"id": "NHT", "name": "Naphtha Hydrotreater", "budget_usd": 1800000, "ytd_spend_usd": 620000},
    "GPU": {"id": "GPU", "name": "Gas Processing Unit", "budget_usd": 2200000, "ytd_spend_usd": 910000},
}


def check_parts_availability(part_numbers: list[str]) -> dict[str, dict]:
    """Return inventory status for a list of part numbers."""
    result = {}
    for pn in part_numbers:
        if pn in _INVENTORY:
            item = _INVENTORY[pn].copy()
            item["available"] = item["qty_on_hand"] > 0
            result[pn] = item
        else:
            result[pn] = {
                "part_number": pn,
                "available": False,
                "qty_on_hand": 0,
                "lead_time_days": 30,
                "unit_cost_usd": 0,
                "description": "Part not found in catalog",
            }
    logger.debug("ERP: Parts availability checked for %d parts", len(part_numbers))
    return result


def reserve_parts(work_order_id: str, part_numbers: list[str]) -> dict:
    """Reserve parts against a work order. Returns reservation summary."""
    reservations = []
    for pn in part_numbers:
        if pn in _INVENTORY and _INVENTORY[pn]["qty_on_hand"] > 0:
            _INVENTORY[pn]["qty_on_hand"] -= 1
            reservations.append({"part_number": pn, "status": "RESERVED", "reserved_at": datetime.now().isoformat()})
        else:
            lead_time = _INVENTORY.get(pn, {}).get("lead_time_days", 30)
            eta = (datetime.now() + timedelta(days=lead_time)).isoformat()
            reservations.append({"part_number": pn, "status": "BACKORDER", "eta": eta})
    _RESERVATIONS[work_order_id] = reservations
    logger.info("ERP: Parts reserved for WO %s — %d items", work_order_id, len(reservations))
    return {"work_order_id": work_order_id, "reservations": reservations}


def calculate_parts_cost(part_numbers: list[str]) -> float:
    """Return total cost of a parts list."""
    total = 0.0
    for pn in part_numbers:
        total += _INVENTORY.get(pn, {}).get("unit_cost_usd", 0)
    return round(total, 2)


def get_cost_center(area_code: str) -> Optional[dict]:
    return _COST_CENTERS.get(area_code)
