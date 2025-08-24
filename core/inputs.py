from dataclasses import dataclass

@dataclass
class ElectricityInput:
  amount : float
  unit : str = "kWh"
  region : str = "IN"

@dataclass
class FuelInput:
    liters: float
    fuel_type: str = "petrol"

@dataclass
class TravelInput:
    mode: str
    distance: float
    unit: str = "km"
    passengers: int = 1