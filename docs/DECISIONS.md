# Decisions

- Follow the PRD's Python, Streamlit, SQLAlchemy, SQLite, pandas and pytest stack.
- Use synthetic coordinates on a plane, Euclidean distance × 1.25, 25 km/h, ceiling to whole travel minutes and 2-minute stop dwell.
- Generate school dates from configured start date while skipping weekends; default is 2026-01-05.
- Seeded Python `random.Random` and SHA-256-derived outcomes avoid dependence on process-global randomness.
- Hard rules precede score: student/address, stop approval, service radius, route feasibility, accessibility, pickup window, duplicate effective assignment and capacity.
- Candidate score follows the PRD weights (distance + 0.5 × projected hours + 2 × post-assignment utilization + 0.1 × stop count), with stable route/stop ID tie breaks.
- Simulated notifications use `.invalid` addresses only. Consent/verification failures become `SUPPRESSED` records; no external message service is called.
- Rejected/otherwise unassigned generation outcomes are currently exposed as aggregate unassigned counts rather than an assignment-decision table; see limitations.
- The implementation prioritizes clear, inspectable local behavior. Full-scale one-million-row attendance throughput has not yet been measured.
