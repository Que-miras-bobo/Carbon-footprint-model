from typing import Dict, Any, List
import math
import numpy as np
import pandas as pd
from core import FactorRegistry, ElectricityInput, FuelInput, TravelInput, UnitConverter

class FootPrintEngine:
  def __init__(self, registry: FactorRegistry, rf_uplift: float=1.0):
    self.registry = registry
    self.rf_uplift = rf_uplift

  def electricity(self, item: ElectricityInput)->Dict[str, Any]:
    kwh = UnitConverter.energytokwh(item.amount, item.unit)
    meta = self.registry.lookup("electricity", "grid", item.region)
    base = meta["factor"]*kwh
    return {"kgCO2e": base, "meta": meta, "activity": "electricity", "inputkWh": kwh}

  def fuel(self, item: FuelInput)->Dict[str, Any]:
    meta = self.registry.lookup("fuel", item.fuel_type, "GLOBAL")
    base = meta["factor"]*item.liters
    return {"kgCO2e": base, "meta": meta, "activity": f"fuel_{item.fuel_type}", "inputLiters": item.liters}

  def travel(self, item: TravelInput)->Dict[str, Any]:
    km = UnitConverter.distancetokm(item.distance, item.unit)
    subcat = item.mode
    meta = self.registry.lookup("travel", subcat, "GLOBAL")
    factor = meta["factor"]*(self.rf_uplift if subcat.startswith("flight") else 1.0)
    base = factor*km*max(1, item.passengers)/item.passengers
    return {"kgCO2e": base, "meta": meta, "activity": f"travel_{item.mode}", "inputKm": km}

class CarbonCalculator:
  def __init__(self, registry: FactorRegistry, rf_uplift: float = 1.0):
    self.registry = registry
    self.engine = FootPrintEngine(registry, rf_uplift)
  def _sum_months(self, v):
    if isinstance(v, (list, tuple, np.ndarray, pd.Series)):
      return float(np.nansum(v))
    return float(v or 0.0)

  def _grid_factor_override(self, base_factor: float, override_pct: float) -> float:
    return base_factor * (1 - override_pct)

  def calculate(self, payload: Dict[str,Any]) -> Dict[str, Any]:
    region = payload.get("region", "IN")

    items = []
    breakdown = {}

    elec_kwh = self._sum_months(payload.get("electricity_kWh", 0.0))
    if elec_kwh > 0:
      meta = self.registry.lookup("electricity","grid",region)
      override = payload.get("_grid_factor_override_pct", 0.0)
      if override:
        meta = meta.copy()
        meta["factor"] = self._grid_factor_override(meta["factor"], override)
        if not math.isnan(meta.get("low", np.nan)):
          meta["low"] = self._grid_factor_override(meta["low"], override)
        if not math.isnan(meta.get("high", np.nan)):
          meta["high"] = self._grid_factor_override(meta["high"], override)
      it = {"kgCO2e": elec_kwh * meta["factor"], "meta": meta, "activity":"electricity","input_kWh":elec_kwh}
      breakdown["electricity"] = it["kgCO2e"]
      items.append(it)

    fuel = payload.get("fuel", {})
    for ft in ["petrol_liters","diesel_liters","lpg_liters"]:
      vol = self._sum_months(fuel.get(ft, 0.0))
      if vol > 0:
        sub = ft.split("_")[0]
        meta = self.registry.lookup("fuel", sub, "GLOBAL")
        it = {"kgCO2e": vol * meta["factor"], "meta": meta, "activity": f"fuel_{sub}", "input_liters": vol}
        breakdown[f"fuel_{sub}"] = it["kgCO2e"]
        items.append(it)

    for mode in ["car","bus","train"]:
      km = self._sum_months(payload.get(f"{mode}_km", 0.0))
      if km > 0:
        meta = self.registry.lookup("travel", mode, "GLOBAL")
        it = {"kgCO2e": km * meta["factor"], "meta": meta, "activity": f"travel_{mode}", "input_km": km}
        breakdown[f"{mode}"] = it["kgCO2e"]
        items.append(it)

    ev_km = self._sum_months(payload.get("ev_km", 0.0))
    if ev_km > 0:
      kwh_per_km = payload.get("ev_kwh_per_km", 0.15)
      meta = self.registry.lookup("electricity","grid",region)

      override = payload.get("_grid_factor_override_pct", 0.0)
      if override:
        meta = meta.copy()
        meta["factor"] = self._grid_factor_override(meta["factor"], override)
        if not math.isnan(meta.get("low", np.nan)):
          meta["low"] = self._grid_factor_override(meta["low"], override)
        if not math.isnan(meta.get("high", np.nan)):
          meta["high"] = self._grid_factor_override(meta["high"], override)

      ev_kwh = ev_km * kwh_per_km
      it = {"kgCO2e": ev_kwh * meta["factor"], "meta": meta, "activity": "travel_ev", "input_kWh": ev_kwh}
      breakdown["ev"] = it["kgCO2e"]
      items.append(it)

    for subcat in ["flight_short","flight_long"]:
      km = self._sum_months(payload.get(f"{subcat}_km", 0.0))
      if km > 0:
        meta = self.registry.lookup("travel", subcat, "GLOBAL")
        rf = 1.0
        it = {"kgCO2e": km * meta["factor"] * rf, "meta": meta, "activity": f"travel_{subcat}", "input_km": km}
        breakdown[subcat] = it["kgCO2e"]
        items.append(it)

    total = sum(breakdown.values())
    return {"total_kgCO2e": total, "breakdown": breakdown, "items": items}

  @staticmethod
  def eco_score(annual_kg: float) -> float:
    t = annual_kg / 1000.0
    score = 100 - min(100, (t / 20.0) * 100.0)
    return round(max(0.0, score), 1)