# Limitations and remaining work

- The role switcher and service-layer role checks are demo controls, not production identity or authorization.
- The generator creates one route per bus from synthetic stop partitions; the model has no live roads, traffic, GPS, or external map provider.
- Eligible and assigned records are explained, but rejected/unassigned generation outcomes are not retained row-by-row in a dedicated `AssignmentDecision` table.
- Capacity-change records are validated by the service layer, but the Streamlit UI does not yet provide a complete capacity reduction review/resolution workflow.
- Scenario decisions are repeatable and evaluated against separate ground truth, but their observed results are not persisted into a dedicated operational exception table; support resolution/audit UI is incomplete.
- Metrics cover the persisted assignment, utilization, route, attendance, notification and disruption sources. A full open/resolved exception metric awaits persistent exception records.
- Full-scale generation and attendance completed. The full attendance simulation elapsed time was not separately captured; no throughput claim is made for it.
- Candidate ownership remains with the submitter: personally review, understand and be prepared to explain the logic, tests and limitations before any public submission.
