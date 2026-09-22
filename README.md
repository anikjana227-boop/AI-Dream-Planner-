# Financial Dream Planner

Predicts how many months until you can afford your goals (car / house /
property), given your salary, expenses, savings, and assumed rate of return.
Powered by the `house_model.pkl` RandomForest model trained in `train.py`.

## Setup

```bash
pip install -r requirements.txt
```

If `house_model.pkl` is missing, train it first:

```bash
python train.py
```

## Web app (new)

```bash
python app.py
```

Then open **http://localhost:5000** — enter your salary, expenses, savings,
and dream goals, and it charts a "horizon" showing when each goal becomes
affordable, plus a plain-English tip per goal.

- `app.py` — Flask API (`/api/plan`, `/api/health`) that wraps the same
  prediction logic as `main.py`, and serves the frontend.
- `static/` — the frontend (`index.html`, `style.css`, `app.js`) — no
  build step, no framework, just static files.

## CLI (original)

```bash
python main.py          # interactive prompts
python main.py --demo   # runs with example data
```
