# YottaFlex Student Transport Operations

A locally runnable synthetic student transport routing and daily operations demo. The supplied PRD is the product specification. No live maps, messaging, real student data, or runtime LLM are used.

## Install and run

Python 3.11+ is required.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
transport-ops generate --scale starter --seed 20261022
transport-ops validate --database data/generated/run_20261022_starter/transport_ops.sqlite
transport-ops scenarios
python -m pytest -q
streamlit run app.py
```

Commands also include `transport-ops generate --scale full`, `transport-ops simulate --database <db> --days 10`, `transport-ops reproduce --scale starter`, and `transport-ops export --database <db>`. Custom sizing is exposed by the Python `generate()` service API. Generation refuses a non-empty database; choose a new path to avoid overwriting data.

## Scope and data handling

All records are synthetic. Guardian email addresses use `.invalid` and phone values are placeholders. Notifications are simulated only. Addresses and contacts are masked in ordinary UI views; the role selector is a demo affordance, not authentication. Route coordinates are synthetic kilometres on a plane. Full generated datasets stay in `data/generated/` and are ignored by Git. Scenario input facts and evaluation ground truth are separate files under `data/scenarios/` and `data/ground_truth/`; decision code reads only the former.

The starter and full presets use the same generator. The full preset is 5,000 students, 100 buses, 300 stops and 200 persisted weekdays. Attendance is created by the `simulate` command or the Daily Operations screen.

## Project map

- `src/transport_ops/models.py`: SQLAlchemy schema and constraints.
- `src/transport_ops/services.py`: deterministic generation, routes, assignment, daily operations, exports.
- `src/transport_ops/validation.py`: persisted-data quality checks.
- `src/transport_ops/scenarios.py`: scenario decisions, then ground-truth evaluation.
- `app.py`: Streamlit pages.
- `docs/`: schema, decisions, validation evidence, limitations, and AI disclosure.
- `prompts/`: request and supplied PRD record.

## Verification status

See `docs/VALIDATION.md` for actual executed test results and full-scale run counts. The full generated dataset and exports are under `data/generated/run_20261022_full_valid/`; generated data is intentionally ignored by Git.
