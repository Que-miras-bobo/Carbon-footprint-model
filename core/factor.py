import numpy as np
import pandas as pd
from typing import Dict, Any

class FactorRegistry:
  def __init__(self, df : pd.DataFrame):
    self.df = df.copy()
    self._validate()

  def _validate(self):
    required = {"category","subcategory","region","factor","unit","source","year"}
    missing = required - set(self.df.columns)
    if missing:
      raise ValueError(f"Missing columns: {missing}")
    if "low" not in self.df.columns:
      self.df["low"] = np.nan
    if "high" not in self.df.columns:
      self.df["high"] = np.nan

  def lookup(self, category: str, subcategory: str, region: str)->Dict[str, Any]:
    candidates = self.df[(self.df.category == category) & (self.df.subcategory == subcategory) & (self.df.region == region)]
    if candidates.empty and len(region)>=2:
      country = region.split("-")[0]
      candidates = self.df[(self.df["category"] == category) & (self.df["subcategory"] == subcategory) & (self.df["region"] == country)]
    if candidates.empty:
      candidates = self.df[(self.df["category"] == category) & (self.df["subcategory"] == subcategory) & (self.df["region"] == "GLOBAL")]
    if candidates.empty:
      raise ValueError(f"No factors found for {category}, {subcategory}, {region}")
    row = candidates.sort_values("year", ascending=False).iloc[0]
    return row.to_dict()

def load_default_registry(csv_path: str = "data/emission_factors.csv") -> FactorRegistry:
  df = pd.read_csv(csv_path)
  return FactorRegistry(df)