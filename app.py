"""
Flask backend for the Logistics Resource-Allocation dashboard (DAA assignment).

Routes:
    GET  /                  -> dashboard UI
    POST /api/run           -> run DP, Greedy, and Developed on one problem instance
    GET  /api/scalability   -> run all three across increasing input sizes for
                                the scalability / performance-comparison charts
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from flask import Flask, jsonify, render_template, request

from algorithms.dataset import generate_packages, save_csv, load_csv
from algorithms.knapsack import run_all

app = Flask(__name__)

DATA_PATH = BASE_DIR / "data" / "packages.csv"

# Generate a default dataset once at startup so /api/run has data to draw from
if not DATA_PATH.exists():
    save_csv(generate_packages(500, seed=42), DATA_PATH)


def get_dataset(n, seed=42):
    """Return n packages. Regenerates deterministically per (n, seed)."""
    return generate_packages(n, seed=seed)


def summarize(result):
    """Strip the full selected-items list down to a compact summary for JSON responses."""
    r = dict(result)
    selected = r.pop("selected", [])
    r["selected_sample"] = selected[:15]  # cap payload size
    return r


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def api_run():
    payload = request.get_json(force=True) or {}
    n_packages = int(payload.get("n_packages", 200))
    capacity = float(payload.get("capacity", 150))
    seed = int(payload.get("seed", 42))

    n_packages = max(5, min(n_packages, 3000))
    capacity = max(1.0, min(capacity, 5000.0))

    items = get_dataset(n_packages, seed=seed)
    results = run_all(items, capacity)

    return jsonify({
        "n_packages": n_packages,
        "capacity": capacity,
        "dp": summarize(results["dp"]),
        "greedy": summarize(results["greedy"]),
        "developed": summarize(results["developed"]),
    })


@app.route("/api/scalability")
def api_scalability():
    capacity = float(request.args.get("capacity", 150))
    max_n = int(request.args.get("max_n", 300))
    step = int(request.args.get("step", 50))
    seed = int(request.args.get("seed", 42))

    max_n = max(step, min(max_n, 1500))
    sizes = list(range(step, max_n + 1, step))

    series = {"sizes": sizes, "dp": [], "greedy": [], "developed": []}

    for n in sizes:
        items = get_dataset(n, seed=seed)
        results = run_all(items, capacity)
        for key in ("dp", "greedy", "developed"):
            r = results[key]
            series[key].append({
                "n": n,
                "time_ms": r["time_ms"],
                "memory_kb": r["memory_kb"],
                "total_value": r["total_value"],
                "capacity_utilization_pct": r["capacity_utilization_pct"],
                "optimality_gap_pct": r["optimality_gap_pct"],
                "num_selected": r["num_selected"],
            })

    return jsonify(series)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)
