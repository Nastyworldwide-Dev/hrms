# HANDOFF
prompt:   Clock-in, location & geofence recovery
status:   done — geofence WORKS; audit-durability defect found + fixed
commit:   2af308f30 on nz-glass
model:    Employee.shift_location + department -> Shift Location.shift_rules
          (dept->shift_type) -> daily sync materializes a Shift Assignment ->
          geofence reads Shift Assignment.shift_location + enable_strict_geofence
          -> Shift Location.{latitude,longitude,checkin_radius}. Coordinates are
          owned by Shift Location (unchanged since the old branch).
why-msg:  "No check-in area set" is genuine CONFIG ABSENCE, proven from site data:
          0 Shift Locations on fresh.local AND test.local, 0 employees with
          shift_location, 0 geolocated check-ins ever. Schema intact, patches ran,
          resolver returns null because the data isn't there — NOT a defect, field
          rename, migration loss, or branch regression. Old build had the same
          coord fields + map picker; the "it worked before" impression is UI, not
          stored data (none ever existed).
proof:    test.local, HR-EMP-00014 assigned to a geofenced HQ (3.1390,101.6869
          r=100): get_active_shift_location returns coords; STRICT inside -> ok;
          STRICT outside -> block (6937m>100m) + throw, 0 check-ins created;
          LENIENT outside -> remote request spawned; approver resolves.
DEFECT:   Geofence Reject Log was rolled back by the strict throw (same txn) —
          0 audit rows in prod despite every rejection. FIXED: commit the audit
          (guarded `not in_test`); bench-verified it now survives, still no
          check-in for the rejected attempt. 2 unit tests added.
approver: 5-tier resolve (shift_request_approver->dept->reports_to->HR Mgr
          in-company->site HR Mgr); request never dropped; OUT inherits IN's
          approval (no double submit); HR acts via admin bypass.
verify:   override tests 6/6; geofence resolver 3/3; ruff clean.
accept:   the message disappears only when HR configures a Shift Location with
          coords+radius and sets Employee.shift_location (or a shift_rules row)
          and enables allow_geolocation_tracking — a CONFIG action, not code.
verdict:  geofence implementation CORRECT on current architecture; 1 audit
          defect fixed. Message is truthful pending HQ configuration.
