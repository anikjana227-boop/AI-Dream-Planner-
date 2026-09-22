"""
train.py — Financial Dream Planner: model training

Generates a synthetic but financially-realistic training set (based on
compound-savings simulation) and trains a RandomForestRegressor that
predicts how many months it will take someone to save enough for a goal
(car / house / property), given their salary, expenses, savings, assumed
return rate, goal type, and goal cost.

Produces:
    data.csv        — the training dataset (so it's inspectable / editable)
    house_model.pkl — the trained model + encoding metadata (joblib dump)

Run:
    python train.py
"""

import random

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

GOAL_TYPES = ["car", "house", "property"]
MODEL_PATH = "house_model.pkl"
DATA_PATH = "data.csv"


# --------------------------------------------------------------------------
# Ground-truth simulator (this is what generates realistic labels)
# --------------------------------------------------------------------------

def months_to_reach(monthly_salary, monthly_expenses, current_savings,
                     annual_return_pct, goal_cost, max_months=1200):
    """Simulate month-by-month compounding savings until goal_cost is reached."""
    surplus = max(0.0, monthly_salary - monthly_expenses)
    r = (annual_return_pct / 100) / 12
    balance = current_savings

    if balance >= goal_cost:
        return 0
    if surplus <= 0 and r <= 0:
        return max_months  # effectively unreachable

    months = 0
    while balance < goal_cost and months < max_months:
        balance = balance * (1 + r) + surplus
        months += 1
    return months


# --------------------------------------------------------------------------
# Synthetic data generation
# --------------------------------------------------------------------------

def generate_synthetic_data(n=4000, seed=42) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []

    goal_cost_ranges = {
        "car": (300_000, 2_500_000),
        "house": (1_500_000, 15_000_000),
        "property": (500_000, 8_000_000),
    }

    for _ in range(n):
        salary = rng.uniform(20_000, 400_000)
        # expenses realistically scale with salary but vary a lot
        expense_ratio = rng.uniform(0.35, 0.95)
        expenses = salary * expense_ratio
        savings = rng.uniform(0, salary * 24)
        annual_return_pct = rng.uniform(0, 14)
        goal_type = rng.choice(GOAL_TYPES)
        low, high = goal_cost_ranges[goal_type]
        goal_cost = rng.uniform(low, high)

        months = months_to_reach(salary, expenses, savings, annual_return_pct, goal_cost)

        rows.append({
            "monthly_salary": round(salary, 2),
            "monthly_expenses": round(expenses, 2),
            "current_savings": round(savings, 2),
            "annual_return_pct": round(annual_return_pct, 2),
            "goal_type": goal_type,
            "goal_cost": round(goal_cost, 2),
            "months_to_reach": months,
        })

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Feature encoding (must match what main.py uses at prediction time)
# --------------------------------------------------------------------------

def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    encoded = df.copy()
    for gt in GOAL_TYPES:
        encoded[f"goal_type_{gt}"] = (encoded["goal_type"] == gt).astype(int)
    feature_cols = [
        "monthly_salary",
        "monthly_expenses",
        "current_savings",
        "annual_return_pct",
        "goal_cost",
    ] + [f"goal_type_{gt}" for gt in GOAL_TYPES]
    return encoded[feature_cols]


# --------------------------------------------------------------------------
# Main training routine
# --------------------------------------------------------------------------

def main():
    print("Generating synthetic training data...")
    df = generate_synthetic_data(n=4000)
    df.to_csv(DATA_PATH, index=False)
    print(f"Saved {len(df)} rows to {DATA_PATH}")

    X = encode_features(df)
    y = df["months_to_reach"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("Training RandomForestRegressor...")
    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    print(f"Validation MAE: {mae:.1f} months")

    joblib.dump(
        {
            "model": model,
            "goal_types": GOAL_TYPES,
            "feature_cols": list(X.columns),
        },
        MODEL_PATH,
    )
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
