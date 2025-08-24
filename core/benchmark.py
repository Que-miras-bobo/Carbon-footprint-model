AVG_PER_CAPITA_TONNES = {
    "IN": 1.9,
    "US": 14.0,
    "EU": 6.5,
    "GLOBAL": 4.7
}
def benchmark(per_capita_tonnes: float, region: str="GLOBAL") -> str:
  ref = AVG_PER_CAPITA_TONNES.get(region, AVG_PER_CAPITA_TONNES["GLOBAL"])
  if per_capita_tonnes < ref*0.6:
    return "excellent (well below regional average)"
  if per_capita_tonnes < ref:
    return "good (below regional average)"
  if per_capita_tonnes < ref*1.2:
    return "around regional average"
  return "above regional average—room to improve"