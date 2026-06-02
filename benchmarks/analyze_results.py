import sys
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def load_stats(results_dir, prefix):
    path = os.path.join(results_dir, f"{prefix}_stats.csv")
    if not os.path.exists(path):
        print(f"Warning: {path} not found")
        return None
    return pd.read_csv(path)


def analyze(results_dir):
    monolith = load_stats(results_dir, "monolith")
    micro = load_stats(results_dir, "microservices")
    if monolith is None or micro is None:
        print("One or both result files missing. Run the benchmark first.")
        return

    metrics = ["Request Count", "Failure Count", "Median Response Time",
               "Average Response Time", "Min Response Time", "Max Response Time",
               "Average Content Size", "Requests/s", "Failures/s"]

    print("\n" + "="*70)
    print(f"{'Metric':<35} {'Monolith':>15} {'Microservices':>15}")
    print("="*70)

    m_agg = monolith[monolith["Name"] == "Aggregated"].iloc[0] if len(monolith) > 0 else None
    ms_agg = micro[micro["Name"] == "Aggregated"].iloc[0] if len(micro) > 0 else None

    if m_agg is None or ms_agg is None:
        print("Aggregated row not found in one or both result files.")
        return

    for metric in metrics:
        m_val = m_agg.get(metric, "N/A")
        ms_val = ms_agg.get(metric, "N/A")
        print(f"{metric:<35} {str(m_val):>15} {str(ms_val):>15}")

    print("="*70)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Monolith vs Microservices — Performance Comparison", fontsize=14, fontweight='bold')

    endpoints = monolith["Name"].tolist()
    m_times = monolith["Average Response Time"].tolist()
    ms_data = micro[micro["Name"].isin(endpoints)]
    ms_times = [ms_data[ms_data["Name"] == ep]["Average Response Time"].values[0]
                if len(ms_data[ms_data["Name"] == ep]) > 0 else 0 for ep in endpoints]

    x = range(len(endpoints))
    axes[0].bar([i - 0.2 for i in x], m_times, 0.4, label='Monolith', color='#3498db')
    axes[0].bar([i + 0.2 for i in x], ms_times, 0.4, label='Microservices', color='#2ecc71')
    axes[0].set_title('Avg Response Time (ms)')
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels([str(ep)[:15] for ep in endpoints], rotation=45, ha='right')
    axes[0].legend()

    labels = ['Monolith', 'Microservices']
    rps = [float(m_agg.get("Requests/s", 0)), float(ms_agg.get("Requests/s", 0))]
    bars = axes[1].bar(labels, rps, color=['#3498db', '#2ecc71'])
    axes[1].set_title('Requests per Second')
    axes[1].bar_label(bars, fmt='%.1f')

    m_failures = float(m_agg.get("Failures/s", 0))
    ms_failures = float(ms_agg.get("Failures/s", 0))
    bars2 = axes[2].bar(labels, [m_failures, ms_failures], color=['#e74c3c', '#e67e22'])
    axes[2].set_title('Failures per Second')
    axes[2].bar_label(bars2, fmt='%.2f')

    plt.tight_layout()
    chart_path = os.path.join(results_dir, "comparison_chart.png")
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    print(f"\nChart saved to: {chart_path}")


if __name__ == "__main__":
    results_dir = sys.argv[1] if len(sys.argv) > 1 else "./results/latest"
    analyze(results_dir)
