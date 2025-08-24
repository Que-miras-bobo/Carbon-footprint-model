import gradio as gr
import matplotlib.pyplot as plt
from typing import Dict
from core import CarbonCalculator, MonteCarloEstimator, ScenarioEngine, benchmark, load_default_registry

# Global registry
registry = load_default_registry()

def plot_breakdown(breakdown: Dict[str,float], title: str):
    labels = list(breakdown.keys())
    vals = [breakdown[k] for k in labels]
    plt.figure(figsize=(6,4))
    plt.bar(labels, vals)
    plt.ylabel("kgCO2e")
    plt.title(title)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    return plt

def carbon_app(region, electricity, petrol, diesel, lpg, car_km, bus_km, train_km,
               flight_short, flight_long, ev_km, solar_share, efficiency_pct,
               ev_switch_pct, mode_shift_pct, mode_shift_to, grid_reduction):

    payload = {
        "region": region,
        "electricity_kWh": electricity,
        "fuel": {"petrol_liters": petrol, "diesel_liters": diesel, "lpg_liters": lpg},
        "car_km": car_km, "bus_km": bus_km, "train_km": train_km,
        "flight_short_km": flight_short, "flight_long_km": flight_long,
        "ev_km": ev_km
    }

    calc = CarbonCalculator(registry, rf_uplift=1.9)
    base = calc.calculate(payload)

    mc = MonteCarloEstimator(registry, rf_uplift=1.9, samples=500, seed=42)
    mc_base = mc.run(base["items"])

    annual = base["total_kgCO2e"]
    score = calc.eco_score(annual)
    per_capita_t = (annual/1000.0)/4
    bench = benchmark(per_capita_t, region=region)

    # Scenario
    actions = {
        "solar_share": solar_share, "efficiency_pct": efficiency_pct,
        "ev_switch_pct": ev_switch_pct,
        "mode_shift": {"to": mode_shift_to, "pct": mode_shift_pct},
        "grid_factor_reduction_pct": grid_reduction
    }
    scen = ScenarioEngine(registry).apply(payload, region, actions)
    after = calc.calculate(scen)
    mc_after = mc.run(after["items"])

    summary = f"""
    ### Baseline Results  
    **Total**: {annual:.2f} kgCO2e/yr  
    **95% CI**: {mc_base['p05']:.2f} — {mc_base['p95']:.2f} kgCO2e  
    **EcoScore**: {score}/100  
    **Per-capita**: {per_capita_t:.2f} tCO2e → {bench}  

    ### Scenario Results (with interventions)  
    **Total**: {after['total_kgCO2e']:.2f} kgCO2e/yr  
    **95% CI**: {mc_after['p05']:.2f} — {mc_after['p95']:.2f} kgCO2e  
    **Savings**: {annual - after['total_kgCO2e']:.2f} kgCO2e ({100*(annual-after['total_kgCO2e'])/annual:.1f}%)  
    """

    fig1 = plot_breakdown(base["breakdown"], "Baseline Emissions by Category")
    fig2 = plot_breakdown(after["breakdown"], "Scenario Emissions by Category")

    return summary, fig1, fig2


def create_interface():
    with gr.Blocks() as demo:
        gr.Markdown("# 🌍 Carbon Footprint Calculator")
        with gr.Row():
            with gr.Column():
                region = gr.Dropdown(["IN","US","EU","GLOBAL"], value="IN", label="Region")
                electricity = gr.Number(value=3600, label="Electricity (kWh)")
                petrol = gr.Number(value=120, label="Petrol (liters)")
                diesel = gr.Number(value=0, label="Diesel (liters)")
                lpg = gr.Number(value=0, label="LPG (liters)")
                car_km = gr.Number(value=5000, label="Car travel (km)")
                bus_km = gr.Number(value=600, label="Bus travel (km)")
                train_km = gr.Number(value=800, label="Train travel (km)")
                flight_short = gr.Number(value=1200, label="Flight short-haul (km)")
                flight_long = gr.Number(value=0, label="Flight long-haul (km)")
                ev_km = gr.Number(value=0, label="EV travel (km)")

            with gr.Column():
                gr.Markdown("### Scenario Settings")
                solar_share = gr.Slider(0,100,value=35,label="Solar Share (%)")
                efficiency_pct = gr.Slider(0,100,value=20,label="Efficiency (%)")
                ev_switch_pct = gr.Slider(0,100,value=30,label="EV Switch (%)")
                mode_shift_pct = gr.Slider(0,100,value=15,label="Mode Shift from Car (%)")
                mode_shift_to = gr.Dropdown(["bus","train"], value="bus", label="Shift To")
                grid_reduction = gr.Slider(0,100,value=20,label="Grid Factor Reduction (%)")

        run_btn = gr.Button("Calculate Footprint 🚀")
        output_text = gr.Markdown()
        out_fig1 = gr.Plot()
        out_fig2 = gr.Plot()

        run_btn.click(fn=carbon_app,
                      inputs=[region, electricity, petrol, diesel, lpg, car_km, bus_km, train_km,
                              flight_short, flight_long, ev_km,
                              solar_share, efficiency_pct, ev_switch_pct, mode_shift_pct,
                              mode_shift_to, grid_reduction],
                      outputs=[output_text, out_fig1, out_fig2])

    return demo
