# GLASS Frontend — Setup Guide

## Requirements

```
Python 3.10+
PyQt6
```

## Install

```bash
pip install PyQt6
```

## Run

```bash
cd glass/
python main.py
```

---

## Project Structure

```
glass/
├── main.py                  ← Entry point, MainWindow
├── styles/
│   └── theme.qss            ← All CSS-like styles (edit this for colors/fonts)
├── components/
│   ├── sidebar.py           ← Left nav sidebar
│   └── stat_card.py         ← Reusable card components
└── views/
    ├── dashboard.py         ← Dashboard (fully built with mock data)
    └── other_views.py       ← Placeholder pages (Budget, Students, etc.)
```

---

## Connecting Your Python Backend

In `views/dashboard.py`, look for `MOCK = { ... }` at the top of `DashboardView`.

Replace the mock values with real DB calls. Example:

```python
# Before (mock)
"total_budget": "₱25,000.00",

# After (real backend)
plan = db.get_active_budget_plan()
"total_budget": f"₱{plan.total_planned_budget:,.2f}",
```

Each view file has a dedicated section for its data. When your backend is ready,
import your service/repository layer at the top of each view file and swap out the mock data.

---

## Customizing Colors

Edit `styles/theme.qss`. The main accent colors are:
- Purple: `#6C5CE7`  (primary brand, sidebar, progress bars)
- Pink:   `#FD79A8`  (activity cards, secondary accent)
- Green:  `#00B894`  (success, collected payments)
- Background: `#EEF0F8`

---

## Adding Charts (Optional)

For richer charts, install `pyqtgraph` or `matplotlib`:

```bash
pip install pyqtgraph
# or
pip install matplotlib
```

The `MiniChart` and `BudgetBarChart` classes in `views/dashboard.py` are
pure PyQt6 (no dependencies). Swap them with pyqtgraph/matplotlib widgets
for more advanced visualizations.
