import math
import random
import statistics
from typing import Dict, Any, List, Optional
import numpy as np
from core import FactorRegistry

class MonteCarloEstimator:
  def __init__(self, registry: FactorRegistry, rf_uplift: float = 1.0, samples: int = 500, seed: Optional[int]=42):
    self.registry = registry
    self.samples = samples
    self.rf_uplift = rf_uplift
    random.seed(seed)

  @staticmethod
  def _triangular(center: float, low: Optional[float], high: Optional[float])->float:
    if math.isnan(low) and math.isnan(high):
      low=center*0.95
      high=center*1.05
    return random.triangular(low, high, center)

  def _sample_factor(self, row: Dict[str,Any], rf: float = 1.0)->float:
    f = self._triangular(row["factor"], row.get("low", np.nan), row.get("high", np.nan))
    return f * rf

  def run(self, items: List[Dict[str,Any]]) -> Dict[str, Any]:
    totals = []
    for _ in range(self.samples):
        total = 0.0
        for it in items:
            meta = it["meta"]
            rf = self.rf_uplift if str(it["activity"]).startswith("travel_flight") else 1.0
            sampled = self._sample_factor(meta, rf)
            if "input_kWh" in it:
                total += it["input_kWh"] * sampled
            elif "input_liters" in it:
                total += it["input_liters"] * sampled
            elif "input_km" in it:
                total += it["input_km"] * sampled
            else:
                raise RuntimeError("Unknown input payload.")
        totals.append(total)
    mean = statistics.mean(totals)
    p05 = np.percentile(totals, 5)
    p95 = np.percentile(totals, 95)
    return {"mean": mean, "p05": p05, "p95": p95, "samples": self.samples}