# Metric definitions

Dashboard metrics come from persisted records. The selected service-date range appears with them; assignment metrics use current assigned projections and utilization uses current capacity plus effective capacity events as of the selected end date.

| Metric | Formula / denominator | Source |
|---|---|---|
| Assignment coverage | Distinct currently `ASSIGNED` students ÷ active students | Student, Assignment |
| Unassigned active students | Active students − distinct assigned students | Student, Assignment |
| Capacity utilization | Occupancy ÷ effective bus capacity, per route; average and max across routes | Assignment, RouteStop, Bus, BusCapacityEvent |
| Capacity violations | Count of routes with occupancy > effective capacity | Same as above |
| Inaccessible assignments | Assigned students requiring accessibility on a non-accessible bus or stop | Assignment, Student, Route, Bus, RouteStop, Stop |
| Feasible route percentage | Routes in `FEASIBLE` or `ACTIVE` ÷ all routes | Route |
| Planned route duration | Mean of planned start through final planned departure, in minutes | Route, RouteStop |
| Attendance status counts | Count of persisted AttendanceEvent per status inside selected date range | AttendanceEvent |
| Absence / missed-pickup rate | Status count ÷ all attendance events in selected range | AttendanceEvent |
| Notification delivery rate | `SIMULATED_SENT` ÷ all persisted notifications in selected range | Notification |
| Open disruptions | Count of persisted disruption events with `OPEN` status | RouteDisruptionEvent |

Inactive students are included in total students, excluded from active-student coverage denominator, and do not receive baseline assignments. The UI currently has no persisted exception entity, so open disruption count is presented separately rather than labelled as total open exceptions.
