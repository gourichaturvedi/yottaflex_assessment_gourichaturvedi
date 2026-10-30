# Validation and observed results

Validation emits check name, records checked, pass/fail counts, severity, affected IDs, explanation, and elapsed seconds. Checks include SQLite FK integrity, ID patterns, route timing, assignment approval/accessibility/pickup/capacity/effective-date overlap, service calendar weekdays, notification eligibility and student-contact linkage, and attendance/assignment date alignment. Validation never repairs records.

## Phase test runs

- Phase 1 foundation: **2 passed** (`tests/test_foundation.py`).
- Phase 2 starter generation: initial test exposed FK insertion ordering; after flushing parent students before contacts: **3 passed** across foundation and generation.
- Phase 3 routing: initial test selected an already-assigned student; after isolating the capacity candidate: **2 passed**.
- Phase 4 daily simulation: **1 passed**, including same-day rerun idempotency.
- Phase 5 validation, scenario suite and reproducibility: **3 passed**.
- Final complete suite after lifecycle, permissions, metrics, pickup-window, and schema refinements: **15 passed**.
- Streamlit `AppTest` smoke checks on the app and full database dashboard: **0 exceptions**. Bare-mode invocation emitted Streamlit's missing `ScriptRunContext` warning.

## Full-scale run

Generated with seed `20261022` and the full preset. Generation (including export and baseline validation) completed in **9.63 seconds** as measured by the command runner.

| Entity | Persisted rows |
|---|---:|
| Students | 5,000 |
| Buses | 100 |
| Stops | 300 |
| Routes | 100 |
| RouteStop links | 300 |
| Service dates | 200 weekdays (2026-01-05 through 2026-10-09) |
| Assignments | 4,850 |
| Attendance events | 970,000 |
| Route disruptions | 473 |
| Notifications | 38,792 |

The 150 unassigned students are inactive or have an unapproved address; they are not baseline-eligible. The final post-simulation database validation was run after the complete attendance and notification history was persisted. Record its exact duration in the generated `validation_summary.json`.

Notification outcomes from persisted rows: 35,937 `SIMULATED_SENT`; 2,855 `SUPPRESSED`. No external messaging service was called.

The full run's baseline validation initially caught 54 pickup-window conflicts. Candidate selection was fixed to reject those candidates, then the full dataset was regenerated. Final post-simulation validation completed in **3.757 seconds**: **23 checks, zero failures**.

## Reproducibility

`transport-ops reproduce --scale starter --seed 20261022` completed with equal row counts and equal content checksums across two generated databases (`equal: true`). The report is under `data/generated/reproducibility/reproducibility_report.json`.
