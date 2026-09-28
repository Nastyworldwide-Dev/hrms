CLASS: one site per person hard-wired into every fence reader (effective_shift_location -> resolve_location -> evaluate_geofence), so HR had no way to let someone work at two sites
hrms/overrides/employee_checkin_override.py:validate_distance_from_shift_location same-root — decides through employee_sites + evaluate_sites, records checked_in_at
hrms/api/geofence.py:check_geofence same-root — strict preflight reads the same site list and rule
hrms/api/geofence.py:get_active_shift_location same-root — map payload adds other_sites
hrms/hr/shift_rules.py not-affected — reads Employee.shift_location only, on purpose; locked by TestShiftRulesNeverReadOtherSites
hrms/sync/runner.py:_write_row not-affected — after cutover leave_existing_row_alone skips existing Employees, so a pull never touches the new fields; an insert omits them (defaults: not ticked)
hrms/utils/readiness.py not-affected — checks each Shift Location's own coordinates and radius; unchanged per site
hrms/overrides/employee_checkin_after_insert.py not-affected — names _remote_nearest_location, now the nearest of the person's sites
