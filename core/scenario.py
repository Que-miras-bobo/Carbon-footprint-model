from typing import Dict, Any
from core import FactorRegistry

class ScenarioEngine:
  def __init__(self, registry: FactorRegistry):
    self.registry = registry

  def apply(self, payload: Dict[str, Any], region: str, actions: Dict[str, Any]) -> Dict[str, Any]:
    newp = payload.copy()
    if "efficiency_pct" in actions:
      eff = max(0.0, min(100.0, actions["efficiency_pct"])) / 100.0
      newp["electricity_kWh"] = newp.get("electricity_kWh", 0.0)*(1 - eff)
    if "solar_share" in actions:
      solar = max(0.0, min(100.0, actions["solar_share"]))/100.0
      newp["electricity_kWh"] = newp.get("electricity_kWh", 0.0)*(1 - solar)
      newp["onsite_solar_kWh"] = newp.get("electricity_kWh", 0.0)*solar
    if "ev_switch_pct" in actions:
      sw = max(0.0, min(100.0, actions["ev_switch_pct"]))/100.0
      shift = newp.get("car_km", 0.0)*sw
      newp["car_km"] = newp.get("car_km", 0.0)-shift
      newp["ev_km"] = newp.get("ev_km", 0.0)+shift
    if "mode_shift" in actions:
      ms = actions["mode_shift"]
      pct = max(0.0, min(100.0, ms.get("pct", 0)))/100.0
      to = ms.get("to","bus")
      shift = newp.get("car_km", 0.0)*pct
      newp["car_km"] -= shift
      key = f"{to}_km"
      newp[key] = newp.get(key, 0.0)+shift
    if "grid_factor_reduction_pct" in actions:
      red = max(0.0, min(100.0, actions["grid_factor_reduction_pct"]))/100.0
      newp["_grid_factor_override_pct"] = red

    return newp