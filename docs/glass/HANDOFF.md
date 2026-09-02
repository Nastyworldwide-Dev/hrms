# HANDOFF
prompt:   Pass 1 — attendance, clock-in/out & geofence closure
status:   system proven correct on current build; live employee unverifiable
commit:   c371eabf9 on nz-glass (verification pass — no new code; fix is f3860e3f3)
arch:     User -> Employee -> active Shift Assignment (rule/schedule/manual) ->
          shift_location (or Employee.shift_location fallback) -> Shift Location
          (lat/lng/radius) -> resolver (effective_shift_location, shared by
          preflight + enforcing insert) -> Nadi API -> CheckInPanel.
rootcause: the resolver read shift_location off the assignment ONLY; rule- and
          schedule-created assignments carry it (create_shift_assignment sets it),
          manual ones do NOT — so a configured Shift Location + linked Employee
          resolved to "no area". Fixed by the Employee.shift_location fallback
          (f3860e3f3). Reproduced Damansara on fresh.local + verified resolution.
verified-current-build (fresh.local, HR-EMP-00001 linked to Damansara r=1000):
          geofence resolves via fallback; IN@09:00 -> Employee Checkin (no remote);
          next action derived from last log (IN -> shows OUT); OUT@18:00 created;
          duplicate same-timestamp OUT BLOCKED; final [IN,OUT], no dup/contradiction.
inside/outside/remote/camera/approver: proven in the prior geofence pass (inside
          ->ok, outside->remote request->5-tier approver, selfie ownership-checked,
          durable reject audit). Unchanged.
D1:       test_rejected_punch_attendance 2/2 — self-repair holds (rejection sets
          skip_auto_attendance; attendance fetch filters on it).
same-class: the 3 live-fence consumers all route through effective_shift_location;
          roster/report .shift_location reads are display/reporting, not live-fence.
          No other resolver ignores the Employee fallback.
UNVERIFIED: the ACTUAL live Verifica employee's break — no access (:8080 =
          fresh.local). Cannot confirm whether f3860e3f3 is deployed there or the
          live employee is linked (Employee.shift_location / assignment set).
verdict:  ATTENDANCE ENTRY NOT CLOSED — system proven correct+comprehensive on the
          current build, but the live contradiction cannot be reproduced/confirmed
          from this environment.
unblock:  live access (or a snapshot of the affected User->Employee->Shift
          Assignment->Shift Location rows) + confirm f3860e3f3 deployed there.
