"""
main.py — Financial Dream Planner (ML-powered)

Loads the trained house_model.pkl (see train.py) and, given your salary,
expenses, savings, and dream goals (car / house / property), predicts how
many months until each is affordable — plus a plain-English tip for each.

Run:
    python main.py

If house_model.pkl doesn't exist yet, train it first:
    python train.py
"""

import os
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.prompt import FloatPrompt, Prompt, Confirm
from rich.table import Table

MODEL_PATH = "house_model.pkl"
GOAL_TYPES = ["car", "house", "property"]

console = Console()


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

@dataclass
class Goal:
    name: str
    goal_type: str  # one of GOAL_TYPES
    cost: float
    months_needed: Optional[int] = None
    target_date: Optional[date] = None


@dataclass
class FinancialProfile:
    monthly_salary: float
    monthly_expenses: float
    current_savings: float
    annual_return_pct: float
    goals: List[Goal] = field(default_factory=list)

    @property
    def monthly_surplus(self) -> float:
        return max(0.0, self.monthly_salary - self.monthly_expenses)


# --------------------------------------------------------------------------
# Model loading + prediction
# --------------------------------------------------------------------------

def load_model():
    if not os.path.exists(MODEL_PATH):
        console.print(
            Panel(
                f"[red]{MODEL_PATH} not found.[/red]\n"
                "Train it first with: [bold]python train.py[/bold]",
                title="Model missing",
            )
        )
        raise SystemExit(1)
    return joblib.load(MODEL_PATH)


def build_feature_row(profile: FinancialProfile, goal: Goal, feature_cols: List[str]) -> pd.DataFrame:
    row = {
        "monthly_salary": profile.monthly_salary,
        "monthly_expenses": profile.monthly_expenses,
        "current_savings": profile.current_savings,
        "annual_return_pct": profile.annual_return_pct,
        "goal_cost": goal.cost,
    }
    for gt in GOAL_TYPES:
        row[f"goal_type_{gt}"] = 1 if goal.goal_type == gt else 0
    return pd.DataFrame([row])[feature_cols]


def predict_months(bundle, profile: FinancialProfile, goal: Goal) -> int:
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    X = build_feature_row(profile, goal, feature_cols)
    pred = model.predict(X)[0]
    return max(0, round(pred))


def add_months_to_today(months: int) -> date:
    today = date.today()
    total = today.month - 1 + months
    year = today.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1)


def compute_plan(bundle, profile: FinancialProfile) -> None:
    for goal in profile.goals:
        months = predict_months(bundle, profile, goal)
        goal.months_needed = months
        goal.target_date = add_months_to_today(months)


# --------------------------------------------------------------------------
# Simple rule-based tips (no external AI dependency in this structure)
# --------------------------------------------------------------------------

def tip_for_goal(profile: FinancialProfile, goal: Goal) -> str:
    surplus = profile.monthly_surplus
    ratio = surplus / profile.monthly_salary if profile.monthly_salary else 0

    if goal.months_needed == 0:
        return "You can already afford this today."
    if goal.months_needed >= 600:
        return "Not realistically reachable at this pace — increase income or cut expenses significantly."
    if ratio < 0.15:
        return "Your savings rate is low (<15% of salary). Trimming monthly expenses will speed this up a lot."
    if goal.goal_type == "house":
        return "Consider a higher-return investment vehicle (index funds, PPF+equity mix) for long-horizon goals like this."
    if goal.goal_type == "car":
        return "A shorter timeline goal — a dedicated high-yield savings account or short-term FD often works well here."
    return "Keep contributions consistent; even small increases in monthly surplus compound significantly over time."


# --------------------------------------------------------------------------
# Display
# --------------------------------------------------------------------------

def print_summary(profile: FinancialProfile) -> None:
    table = Table(title="Monthly Snapshot", show_header=False)
    table.add_row("Monthly salary", f"₹{profile.monthly_salary:,.0f}")
    table.add_row("Monthly expenses", f"₹{profile.monthly_expenses:,.0f}")
    table.add_row("Monthly surplus (savings)", f"₹{profile.monthly_surplus:,.0f}")
    table.add_row("Current savings", f"₹{profile.current_savings:,.0f}")
    table.add_row("Assumed annual return", f"{profile.annual_return_pct:.1f}%")
    console.print(table)


def print_goals(profile: FinancialProfile) -> None:
    table = Table(title="Your Dream Goals — Predicted Timeline")
    table.add_column("Goal")
    table.add_column("Type")
    table.add_column("Cost", justify="right")
    table.add_column("Time to reach", justify="right")
    table.add_column("Estimated date", justify="right")
    table.add_column("Tip")

    for g in sorted(profile.goals, key=lambda x: x.cost):
        if g.months_needed == 0:
            time_str, date_str = "Already there!", "Now"
        elif g.months_needed >= 600:
            time_str, date_str = "600+ months", "—"
        else:
            years, months = divmod(g.months_needed, 12)
            parts = [p for p in [f"{years}y" if years else "", f"{months}m" if months else ""] if p]
            time_str = " ".join(parts) or "0m"
            date_str = g.target_date.strftime("%b %Y")

        table.add_row(g.name, g.goal_type, f"₹{g.cost:,.0f}", time_str, date_str, tip_for_goal(profile, g))

    console.print(table)


# --------------------------------------------------------------------------
# Interactive input
# --------------------------------------------------------------------------

def pick_goal_type() -> str:
    choice = Prompt.ask("Goal type", choices=GOAL_TYPES, default="house")
    return choice


def collect_profile_interactively() -> FinancialProfile:
    console.print(Panel.fit("💰 Financial Dream Planner (ML-powered)", style="bold green"))

    salary = FloatPrompt.ask("What is your monthly salary (take-home)")
    expenses = FloatPrompt.ask("What are your average monthly expenses")
    savings = FloatPrompt.ask("How much do you currently have saved", default=0.0)
    use_default = Confirm.ask("Assume a 6% annual return on your savings/investments?", default=True)
    annual_return_pct = 6.0 if use_default else FloatPrompt.ask("Enter assumed annual return as a percent (e.g. 8)")

    profile = FinancialProfile(
        monthly_salary=salary,
        monthly_expenses=expenses,
        current_savings=savings,
        annual_return_pct=annual_return_pct,
    )

    console.print("\n[bold]Now let's add your dream goals[/bold] (car, house, property).")
    console.print("Leave the name blank when you're done adding goals.\n")

    while True:
        name = Prompt.ask("Goal name (blank to finish)", default="")
        if not name.strip():
            break
        goal_type = pick_goal_type()
        cost = FloatPrompt.ask(f"Estimated cost of '{name}'")
        profile.goals.append(Goal(name=name.strip(), goal_type=goal_type, cost=cost))

    return profile


def load_demo_profile() -> FinancialProfile:
    profile = FinancialProfile(
        monthly_salary=80000,
        monthly_expenses=45000,
        current_savings=300000,
        annual_return_pct=6.0,
    )
    profile.goals = [
        Goal(name="Hatchback Car", goal_type="car", cost=800000),
        Goal(name="2BHK Flat Down Payment", goal_type="house", cost=3000000),
        Goal(name="Small Land Plot", goal_type="property", cost=1500000),
    ]
    return profile


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Financial Dream Planner (ML-powered)")
    parser.add_argument("--demo", action="store_true", help="Run with example demo data instead of prompting")
    args = parser.parse_args()

    bundle = load_model()
    profile = load_demo_profile() if args.demo else collect_profile_interactively()

    if not profile.goals:
        console.print("[yellow]No goals entered — nothing to plan. Exiting.[/yellow]")
        return

    compute_plan(bundle, profile)

    console.print()
    print_summary(profile)
    console.print()
    print_goals(profile)


if __name__ == "__main__":
    main()
