import gradio as gr
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Any
from core import CarbonCalculator, MonteCarloEstimator, ScenarioEngine, benchmark, load_default_registry

# Init engines
registry = load_default_registry()
calc = CarbonCalculator(registry)
mc = MonteCarloEstimator(registry)
scenario_engine = ScenarioEngine(registry)

# Plot helper
def plot_grouped_breakdown(base_breakdown, after_breakdown, title="Emission Breakdown"):
    categories = list(set(base_breakdown.keys()) | set(after_breakdown.keys()))
    categories.sort()

    baseline_vals = [base_breakdown.get(cat, 0) for cat in categories]
    after_vals    = [after_breakdown.get(cat, 0) for cat in categories]

    x = np.arange(len(categories))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width/2, baseline_vals, width, label="Baseline")
    ax.bar(x + width/2, after_vals, width, label="Scenario")

    ax.set_ylabel("CO₂ Emissions (kg)")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=30, ha="right")
    ax.legend()

    plt.tight_layout()
    return fig

# Payload builders
def build_payload_base(region: str) -> Dict[str, Any]:
    return {"region": region}

def apply_electricity(payload: Dict[str, Any], kwh: float) -> Dict[str, Any]:
    payload["electricity_kWh"] = max(0.0, float(kwh or 0))
    return payload

def apply_fuel(payload: Dict[str, Any], petrol_l: float, diesel_l: float, lpg_l: float) -> Dict[str, Any]:
    payload["fuel"] = {
        "petrol_liters": max(0.0, float(petrol_l or 0)),
        "diesel_liters": max(0.0, float(diesel_l or 0)),
        "lpg_liters":    max(0.0, float(lpg_l or 0)),
    }
    return payload

def apply_travel(payload: Dict[str, Any], car_km: float, bus_km: float, train_km: float,
                 short_km: float, long_km: float, ev_km: float) -> Dict[str, Any]:
    payload["car_km"] = max(0.0, float(car_km or 0))
    payload["bus_km"] = max(0.0, float(bus_km or 0))
    payload["train_km"] = max(0.0, float(train_km or 0))
    payload["flight_short_km"] = max(0.0, float(short_km or 0))
    payload["flight_long_km"]  = max(0.0, float(long_km or 0))
    payload["ev_km"] = max(0.0, float(ev_km or 0))
    return payload

# Main calculation
def run_calculation(
    bill_type: str,
    region: str,
    electricity_kwh: float,
    petrol_l: float, diesel_l: float, lpg_l: float,
    car_km: float, bus_km: float, train_km: float, short_km: float, long_km: float, ev_km: float,
    solar_share: float, efficiency_pct: float, ev_switch_pct: float,
    mode_shift_pct: float, mode_shift_to: str, grid_reduction: float
):
    payload = build_payload_base(region)

    if bill_type == "Electricity":
        apply_electricity(payload, electricity_kwh)
    elif bill_type == "Fuel":
        apply_fuel(payload, petrol_l, diesel_l, lpg_l)
    elif bill_type == "Travel":
        apply_travel(payload, car_km, bus_km, train_km, short_km, long_km, ev_km)
    elif bill_type == "Combined (manual)":
        if electricity_kwh is not None:
            apply_electricity(payload, electricity_kwh)
        apply_fuel(payload, petrol_l, diesel_l, lpg_l)
        apply_travel(payload, car_km, bus_km, train_km, short_km, long_km, ev_km)

    # Baseline
    base = calc.calculate(payload)
    mc_base = mc.run(base["items"])
    annual = base["total_kgCO2e"]
    score = calc.eco_score(annual)
    per_capita_t = (annual / 1000.0) / 4
    bench = benchmark(per_capita_t, region=region)

    # Scenario
    actions = {
        "solar_share": solar_share,
        "efficiency_pct": efficiency_pct,
        "ev_switch_pct": ev_switch_pct,
        "mode_shift": {"to": mode_shift_to, "pct": mode_shift_pct},
        "grid_factor_reduction_pct": grid_reduction
    }
    scen_payload = scenario_engine.apply(payload, region, actions)
    after = calc.calculate(scen_payload)
    mc_after = mc.run(after["items"])

    summary = f"""### Baseline Results  
**Total**: {annual:.2f} kgCO2e/yr  
**95% CI**: {mc_base['p05']:.2f} — {mc_base['p95']:.2f} kgCO2e  
**EcoScore**: {score}/100  
**Per-capita**: {per_capita_t:.2f} tCO2e → {bench}  

### Scenario Results  
**Total**: {after['total_kgCO2e']:.2f} kgCO2e/yr  
**95% CI**: {mc_after['p05']:.2f} — {mc_after['p95']:.2f} kgCO2e  
**Savings**: {annual - after['total_kgCO2e']:.2f} kgCO2e  
({(100*(annual-after['total_kgCO2e'])/annual if annual>0 else 0):.1f}%)  
"""

    fig = plot_grouped_breakdown(base["breakdown"], after["breakdown"],
                                 f"{bill_type} • Baseline vs Scenario")

    return summary, fig

# UI handler to toggle inputs
def toggle_inputs(bill_type):
    return (
        gr.update(visible=bill_type in ["Electricity", "Combined (manual)"]), # electricity
        gr.update(visible=bill_type in ["Fuel", "Combined (manual)"]),        # fuel
        gr.update(visible=bill_type in ["Travel", "Combined (manual)"]),      # travel
    )


# Dynamic visibility helper
def on_bill_type_change(bill_type):
    note = ""
    if bill_type == "Electricity":
        note = "Tip: Scenario controls that affect electricity (solar, efficiency, grid factor) will be applied."
        return note, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
    elif bill_type == "Fuel":
        note = "Tip: Fuel emissions are direct; electricity-related scenarios won't change fuel unless you use the Combined mode."
        return note, gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
    elif bill_type == "Travel":
        note = "Tip: EV switch and mode shift scenarios are most relevant here."
        return note, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
    else:  # Combined
        note = "Tip: Combined mode lets you enter any fields; all relevant scenarios will apply."
        return note, gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)

# Gradio Interface
def create_interface():
    with gr.Blocks() as demo:
        gr.Markdown("# 🌍 GreenChain — Modular Carbon Footprint Calculator")
        gr.Markdown(
            "Choose a **bill type** below. Enter only the fields relevant to that bill. The scenario controls will automatically apply only where they make sense for that bill type.")

        with gr.Row():
            bill_type = gr.Radio(["Electricity", "Fuel", "Travel", "Combined (manual)"], value="Electricity",
                                 label="Bill Type")
            region = gr.Dropdown(["IN", "US", "EU", "GLOBAL"], value="IN", label="Region")

        guidance = gr.Markdown("", elem_id="guidance")

        with gr.Group(visible=True) as electricity_group:
            electricity_kwh = gr.Number(value=3600, label="Electricity (kWh)")

        with gr.Group(visible=False) as fuel_group:
            petrol = gr.Number(value=120, label="Petrol (liters)")
            diesel = gr.Number(value=0, label="Diesel (liters)")
            lpg = gr.Number(value=0, label="LPG (liters)")

        with gr.Group(visible=False) as travel_group:
            car_km = gr.Number(value=5000, label="Car travel (km)")
            bus_km = gr.Number(value=600, label="Bus travel (km)")
            train_km = gr.Number(value=800, label="Train travel (km)")
            flight_short = gr.Number(value=1200, label="Flight short-haul (km)")
            flight_long = gr.Number(value=0, label="Flight long-haul (km)")
            ev_km = gr.Number(value=0, label="EV travel (km)")

        bill_type.change(
            fn=on_bill_type_change,
            inputs=[bill_type],
            outputs=[guidance, electricity_group, fuel_group, travel_group]
        )

        gr.Markdown("### Scenario Settings (auto-applied when relevant)")
        with gr.Row():
            solar_share = gr.Slider(0, 100, value=35, label="Solar Share (%)")
            efficiency_pct = gr.Slider(0, 100, value=20, label="Efficiency (%)")
            grid_reduction = gr.Slider(0, 100, value=20, label="Grid Factor Reduction (%)")
        with gr.Row():
            ev_switch_pct = gr.Slider(0, 100, value=30, label="EV Switch from Car (%)")
            mode_shift_pct = gr.Slider(0, 100, value=15, label="Mode Shift from Car (%)")
            mode_shift_to = gr.Dropdown(["bus", "train"], value="bus", label="Shift Car →")

        run_btn = gr.Button("Calculate Footprint 🚀")
        output_text = gr.Markdown()
        out_fig = gr.Plot()

        run_btn.click(
            fn=run_calculation,
            inputs=[
                bill_type, region,
                electricity_kwh,
                petrol, diesel, lpg,
                car_km, bus_km, train_km, flight_short, flight_long, ev_km,
                solar_share, efficiency_pct, ev_switch_pct, mode_shift_pct, mode_shift_to, grid_reduction
            ],
            outputs=[output_text, out_fig]
        )

    return demo

if __name__ == "__main__":
    demo = create_interface()
    demo.launch()
