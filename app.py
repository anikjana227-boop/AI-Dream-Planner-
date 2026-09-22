"""
app.py — Financial Dream Planner web backend

Wraps the same model + logic used by main.py (CLI) behind a small Flask
JSON API, and serves the static frontend in /static.

Run:
    python app.py
Then open:
    http://localhost:5000
"""

import os
from datetime import date

import joblib
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

MODEL_PATH = os.path.join(os.path.dirname(__file__), "house_model.pkl")
GOAL_TYPES = ["car", "house", "property"]

app = Flask(__name__, static_folder="static", static_url_path="")

_bundle = None


def get_bundle():
    global _bundle
    if _bundle is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"{MODEL_PATH} not found. Train it first with: python train.py"
            )
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


# --------------------------------------------------------------------------
# Prediction logic (mirrors main.py)
# --------------------------------------------------------------------------

def build_feature_row(profile, goal, feature_cols):
    row = {
        "monthly_salary": profile["monthly_salary"],
        "monthly_expenses": profile["monthly_expenses"],
        "current_savings": profile["current_savings"],
        "annual_return_pct": profile["annual_return_pct"],
        "goal_cost": goal["cost"],
    }
    for gt in GOAL_TYPES:
        row[f"goal_type_{gt}"] = 1 if goal["goal_type"] == gt else 0
    return pd.DataFrame([row])[feature_cols]


def predict_months(bundle, profile, goal):
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    X = build_feature_row(profile, goal, feature_cols)
    pred = model.predict(X)[0]
    return max(0, round(pred))


def add_months_to_today(months):
    today = date.today()
    total = today.month - 1 + months
    year = today.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1)


def tip_for_goal(profile, goal, months_needed):
    surplus = max(0.0, profile["monthly_salary"] - profile["monthly_expenses"])
    ratio = surplus / profile["monthly_salary"] if profile["monthly_salary"] else 0

    if months_needed == 0:
        return "You can already afford this today."
    if months_needed >= 600:
        return "Not realistically reachable at this pace — increase income or cut expenses significantly."
    if ratio < 0.15:
        return "Your savings rate is low (under 15% of salary). Trimming monthly expenses will speed this up a lot."
    if goal["goal_type"] == "house":
        return "Consider a higher-return investment vehicle (index funds, PPF+equity mix) for a long-horizon goal like this."
    if goal["goal_type"] == "car":
        return "A shorter timeline goal — a dedicated high-yield savings account or short-term FD often works well here."
    return "Keep contributions consistent; even small increases in monthly surplus compound significantly over time."


def validate_profile(data):
    errors = []
    for field in ["monthly_salary", "monthly_expenses", "current_savings", "annual_return_pct"]:
        if field not in data:
            errors.append(f"Missing field: {field}")
        else:
            try:
                float(data[field])
            except (TypeError, ValueError):
                errors.append(f"{field} must be a number")
    if "goals" not in data or not isinstance(data["goals"], list) or len(data["goals"]) == 0:
        errors.append("At least one goal is required")
    else:
        for i, g in enumerate(data["goals"]):
            if not g.get("name", "").strip():
                errors.append(f"Goal {i + 1}: name is required")
            if g.get("goal_type") not in GOAL_TYPES:
                errors.append(f"Goal {i + 1}: goal_type must be one of {GOAL_TYPES}")
            try:
                float(g.get("cost"))
            except (TypeError, ValueError):
                errors.append(f"Goal {i + 1}: cost must be a number")
    return errors


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

@app.route("/api/plan", methods=["POST"])
def api_plan():
    data = request.get_json(force=True, silent=True) or {}

    errors = validate_profile(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        bundle = get_bundle()
    except FileNotFoundError as e:
        return jsonify({"errors": [str(e)]}), 500

    profile = {
        "monthly_salary": float(data["monthly_salary"]),
        "monthly_expenses": float(data["monthly_expenses"]),
        "current_savings": float(data["current_savings"]),
        "annual_return_pct": float(data["annual_return_pct"]),
    }
    surplus = max(0.0, profile["monthly_salary"] - profile["monthly_expenses"])

    results = []
    for g in data["goals"]:
        goal = {
            "name": g["name"].strip(),
            "goal_type": g["goal_type"],
            "cost": float(g["cost"]),
        }
        months = predict_months(bundle, profile, goal)
        target = add_months_to_today(months) if months < 600 else None
        results.append({
            "name": goal["name"],
            "goal_type": goal["goal_type"],
            "cost": goal["cost"],
            "months_needed": months,
            "target_date": target.isoformat() if target else None,
            "tip": tip_for_goal(profile, goal, months),
        })

    results.sort(key=lambda r: r["cost"])

    return jsonify({
        "summary": {
            "monthly_salary": profile["monthly_salary"],
            "monthly_expenses": profile["monthly_expenses"],
            "monthly_surplus": surplus,
            "current_savings": profile["current_savings"],
            "annual_return_pct": profile["annual_return_pct"],
        },
        "goals": results,
    })


@app.route("/api/health", methods=["GET"])
def health():
    model_ready = os.path.exists(MODEL_PATH)
    return jsonify({"status": "ok", "model_ready": model_ready})


# --------------------------------------------------------------------------
# Frontend
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
