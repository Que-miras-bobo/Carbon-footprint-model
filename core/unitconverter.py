

class UnitConverter:
  @staticmethod
  def energytokwh(value: float, unit: str)->float:
    unit = unit.lower()
    if unit == "kwh": return value
    if unit == "mwh": return value*1000.0
    if unit == "wh": return value/1000.0
    raise ValueError(f"Unknown energy unit: {unit}")

  @staticmethod
  def volumetoliters(value: float, unit: str)->float:
    unit = unit.lower()
    if unit == "liter" or unit == "liters": return value
    if unit == "l": return value
    if unit == "gallon_us": return value*3.78541
    if unit == "gallon_uk": return value*4.54609
    raise ValueError(f"Unknown volume unit: {unit}")

  @staticmethod
  def distancetokm(value: float, unit: str)->float:
    unit = unit.lower()
    if unit == "km": return value
    if unit == "mi" or unit == "mile" or unit == "miles": return value*1.60934
    raise ValueError(f"Unknown distance unit: {unit}")