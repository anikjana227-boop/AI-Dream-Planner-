(function () {
  "use strict";

  const goalList = document.getElementById("goal-list");
  const addGoalBtn = document.getElementById("add-goal");
  const form = document.getElementById("plan-form");
  const submitBtn = document.getElementById("submit-btn");
  const demoBtn = document.getElementById("demo-btn");

  const emptyState = document.getElementById("empty-state");
  const resultsEl = document.getElementById("results");
  const errorState = document.getElementById("error-state");
  const errorText = document.getElementById("error-text");

  const summaryStrip = document.getElementById("summary-strip");
  const goalCards = document.getElementById("goal-cards");
  const chart = document.getElementById("horizon-chart");

  const GOAL_TYPES = [
    { value: "car", label: "Car" },
    { value: "house", label: "House" },
    { value: "property", label: "Property" },
  ];

  let goalRowCount = 0;

  const inrFormatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  });

  function formatINR(n) {
    return inrFormatter.format(n);
  }

  function monthsToHuman(months) {
    if (months === 0) return "Already there";
    if (months >= 600) return "Not reachable";
    const years = Math.floor(months / 12);
    const rem = months % 12;
    const parts = [];
    if (years) parts.push(years + "y");
    if (rem) parts.push(rem + "m");
    return parts.join(" ") || "0m";
  }

  function formatDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
  }

  // -------------------------------------------------------------------
  // Goal rows
  // -------------------------------------------------------------------

  function addGoalRow(prefill) {
    goalRowCount += 1;
    const id = "goal-" + goalRowCount;

    const row = document.createElement("div");
    row.className = "goal-row";
    row.dataset.rowId = id;

    const typeOptions = GOAL_TYPES.map(
      (t) => `<option value="${t.value}">${t.label}</option>`
    ).join("");

    row.innerHTML = `
      <button type="button" class="remove-goal" aria-label="Remove goal" title="Remove goal">×</button>
      <div class="goal-row-top">
        <input type="text" class="goal-name" placeholder="e.g. Hatchback car" required>
        <select class="goal-type">${typeOptions}</select>
      </div>
      <label class="field goal-cost">
        <span>Estimated cost</span>
        <div class="input-rupee">
          <span class="rupee">₹</span>
          <input type="number" class="goal-cost-input" min="0" step="1000" placeholder="8,00,000" required>
        </div>
      </label>
    `;

    row.querySelector(".remove-goal").addEventListener("click", () => {
      row.remove();
    });

    if (prefill) {
      row.querySelector(".goal-name").value = prefill.name;
      row.querySelector(".goal-type").value = prefill.goal_type;
      row.querySelector(".goal-cost-input").value = prefill.cost;
    }

    goalList.appendChild(row);
  }

  addGoalBtn.addEventListener("click", () => addGoalRow());

  function readGoals() {
    return Array.from(goalList.querySelectorAll(".goal-row")).map((row) => ({
      name: row.querySelector(".goal-name").value.trim(),
      goal_type: row.querySelector(".goal-type").value,
      cost: parseFloat(row.querySelector(".goal-cost-input").value),
    }));
  }

  // -------------------------------------------------------------------
  // Submission
  // -------------------------------------------------------------------

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    submitBtn.querySelector(".btn-label").textContent = isLoading
      ? "Charting your path…"
      : "Plan my dreams";
    submitBtn.querySelector(".btn-spinner").hidden = !isLoading;
  }

  function showError(message) {
    emptyState.hidden = true;
    resultsEl.hidden = true;
    errorState.hidden = false;
    errorText.textContent = message;
  }

  async function submitPlan(payload) {
    setLoading(true);
    errorState.hidden = true;
    try {
      const res = await fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        showError((data.errors || ["Something went wrong."]).join(" "));
        return;
      }
      renderResults(data);
    } catch (err) {
      showError("Couldn't reach the planner. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
      monthly_salary: parseFloat(document.getElementById("salary").value),
      monthly_expenses: parseFloat(document.getElementById("expenses").value),
      current_savings: parseFloat(document.getElementById("savings").value),
      annual_return_pct: parseFloat(document.getElementById("return-pct").value),
      goals: readGoals(),
    };
    submitPlan(payload);
  });

  demoBtn.addEventListener("click", () => {
    document.getElementById("salary").value = 80000;
    document.getElementById("expenses").value = 45000;
    document.getElementById("savings").value = 300000;
    document.getElementById("return-pct").value = 6;

    goalList.innerHTML = "";
    addGoalRow({ name: "Hatchback Car", goal_type: "car", cost: 800000 });
    addGoalRow({ name: "2BHK Flat Down Payment", goal_type: "house", cost: 3000000 });
    addGoalRow({ name: "Small Land Plot", goal_type: "property", cost: 1500000 });

    submitPlan({
      monthly_salary: 80000,
      monthly_expenses: 45000,
      current_savings: 300000,
      annual_return_pct: 6,
      goals: [
        { name: "Hatchback Car", goal_type: "car", cost: 800000 },
        { name: "2BHK Flat Down Payment", goal_type: "house", cost: 3000000 },
        { name: "Small Land Plot", goal_type: "property", cost: 1500000 },
      ],
    });
  });

  // -------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------

  function renderResults(data) {
    emptyState.hidden = true;
    errorState.hidden = true;
    resultsEl.hidden = false;

    renderSummary(data.summary);
    renderChart(data.goals);
    renderCards(data.goals);
  }

  function renderSummary(summary) {
    const cells = [
      { label: "Monthly salary", value: formatINR(summary.monthly_salary) },
      { label: "Monthly expenses", value: formatINR(summary.monthly_expenses) },
      { label: "Monthly surplus", value: formatINR(summary.monthly_surplus), cls: "surplus" },
      { label: "Current savings", value: formatINR(summary.current_savings) },
    ];
    summaryStrip.innerHTML = cells
      .map(
        (c) => `
        <div class="summary-cell ${c.cls || ""}">
          <p class="label">${c.label}</p>
          <p class="value">${c.value}</p>
        </div>`
      )
      .join("");
  }

  function renderCards(goals) {
    goalCards.innerHTML = goals
      .map((g) => {
        const stateCls =
          g.months_needed === 0 ? "reached" : g.months_needed >= 600 ? "unreachable" : "";
        return `
        <article class="goal-card ${stateCls}">
          <div class="goal-card-head">
            <h3>${escapeHtml(g.name)}</h3>
            <span class="goal-type-pill ${g.goal_type}">${g.goal_type}</span>
          </div>
          <p class="cost">${formatINR(g.cost)}</p>
          <div class="timeline-row">
            <span class="months">${monthsToHuman(g.months_needed)}</span>
            <span class="date">${formatDate(g.target_date)}</span>
          </div>
          <p class="tip">${escapeHtml(g.tip)}</p>
        </article>`;
      })
      .join("");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // -------------------------------------------------------------------
  // Horizon chart (custom SVG — no charting library)
  // -------------------------------------------------------------------

  const SVG_NS = "http://www.w3.org/2000/svg";
  const CHART_W = 900;
  const CHART_H = 340;
  const PAD_L = 60;
  const PAD_R = 40;
  const PAD_T = 30;
  const PAD_B = 50;

  function svgEl(tag, attrs) {
    const el = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => el.setAttribute(k, v));
    return el;
  }

  function renderChart(goals) {
    chart.innerHTML = "";

    const reachable = goals.filter((g) => g.months_needed < 600);
    const plotW = CHART_W - PAD_L - PAD_R;
    const plotH = CHART_H - PAD_T - PAD_B;

    const maxMonths = Math.max(1, ...reachable.map((g) => g.months_needed), 12);
    const maxCost = Math.max(1, ...goals.map((g) => g.cost));

    const xFor = (m) => PAD_L + (m / maxMonths) * plotW;
    const yFor = (cost) => PAD_T + plotH - (cost / maxCost) * plotH;

    // baseline (today)
    chart.appendChild(
      svgEl("line", {
        x1: PAD_L,
        y1: PAD_T + plotH,
        x2: CHART_W - PAD_R,
        y2: PAD_T + plotH,
        stroke: "var(--line-soft)",
        "stroke-width": 1,
      })
    );

    const todayLabel = svgEl("text", {
      x: PAD_L,
      y: PAD_T + plotH + 22,
      fill: "var(--text-light-60)",
      "font-family": "var(--font-mono)",
      "font-size": 11,
    });
    todayLabel.textContent = "today";
    chart.appendChild(todayLabel);

    const sorted = [...reachable].sort((a, b) => a.months_needed - b.months_needed);

    if (sorted.length) {
      // area + path rising toward the horizon, anchored at "today"
      const points = [{ x: PAD_L, y: PAD_T + plotH }, ...sorted.map((g) => ({
        x: xFor(g.months_needed),
        y: yFor(g.cost),
      }))];

      const pathD = catmullRomPath(points);

      const areaD =
        pathD +
        ` L ${points[points.length - 1].x},${PAD_T + plotH} L ${points[0].x},${PAD_T + plotH} Z`;

      const gradId = "horizonFill";
      const defs = svgEl("defs", {});
      const grad = svgEl("linearGradient", { id: gradId, x1: 0, y1: 0, x2: 0, y2: 1 });
      grad.appendChild(svgEl("stop", { offset: "0%", "stop-color": "var(--gold)", "stop-opacity": 0.28 }));
      grad.appendChild(svgEl("stop", { offset: "100%", "stop-color": "var(--gold)", "stop-opacity": 0 }));
      defs.appendChild(grad);
      chart.appendChild(defs);

      chart.appendChild(svgEl("path", { d: areaD, fill: `url(#${gradId})`, stroke: "none" }));
      chart.appendChild(
        svgEl("path", {
          d: pathD,
          fill: "none",
          stroke: "var(--gold)",
          "stroke-width": 1.75,
        })
      );
    }

    // markers + labels for every goal (including unreachable, pinned to right edge)
    goals.forEach((g) => {
      const reachableGoal = g.months_needed < 600;
      const x = reachableGoal ? xFor(g.months_needed) : CHART_W - PAD_R;
      const y = reachableGoal ? yFor(g.cost) : PAD_T + 14;

      const color =
        g.goal_type === "car" ? "var(--gold-soft)" : g.goal_type === "house" ? "var(--teal)" : "#8FA8D0";

      chart.appendChild(
        svgEl("circle", {
          cx: x,
          cy: y,
          r: 5,
          fill: reachableGoal ? color : "var(--rust)",
          stroke: "var(--ink)",
          "stroke-width": 2,
        })
      );

      const label = svgEl("text", {
        x: Math.min(Math.max(x, PAD_L + 4), CHART_W - PAD_R - 4),
        y: y - 14,
        fill: "var(--text-light)",
        "font-family": "var(--font-body)",
        "font-size": 12,
        "text-anchor": x > CHART_W - 120 ? "end" : "middle",
      });
      label.textContent = g.name;
      chart.appendChild(label);

      const sub = svgEl("text", {
        x: Math.min(Math.max(x, PAD_L + 4), CHART_W - PAD_R - 4),
        y: y - 1,
        fill: "var(--text-light-60)",
        "font-family": "var(--font-mono)",
        "font-size": 10,
        "text-anchor": x > CHART_W - 120 ? "end" : "middle",
      });
      sub.textContent = reachableGoal ? formatDate(g.target_date) : "600+ months";
      chart.appendChild(sub);
    });
  }

  // simple smooth path through points using a light catmull-rom -> bezier conversion
  function catmullRomPath(points) {
    if (points.length < 2) {
      return points.length === 1 ? `M ${points[0].x},${points[0].y}` : "";
    }
    let d = `M ${points[0].x},${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i - 1] || points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = points[i + 2] || p2;

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      d += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`;
    }
    return d;
  }

  // -------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------

  addGoalRow({ name: "Hatchback Car", goal_type: "car", cost: "" });
})();
