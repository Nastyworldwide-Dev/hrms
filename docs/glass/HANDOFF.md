# HANDOFF
prompt:   geofence ignored GPS accuracy; iOS/desktop parity
status:   done
commit:   95d390367 on nz-glass (backend 9bd167717)
files:    hrms/utils/geofence.py            (accuracy_m arg, 250 m cap)
          hrms/overrides/employee_checkin_override.py (flag -> decision)
          hrms/api/{geofence,remote_checkin}.py       (accept + forward)
          hrms/hr/doctype/geofence_reject_log/*.json  (accuracy_m, reason opt)
          frontend/src/utils/geolocation.js           (new)
          frontend/src/components/{CheckInPanel,RemoteCheckinDialog,StrictRejectionDialog}.vue
verify:   cd /home/nabil/verify-bench/sites && ../env/bin/python -m unittest \
          hrms.utils.test_geofence hrms.overrides.test_employee_checkin_override \
          hrms.api.test_remote_checkin; yarn --cwd frontend test
flags:    250 m cap is a guess - watch imprecise_location volume before tuning.
          Reject Log needs `bench migrate` for the two new columns.
next:     no fix at all still hard-throws "lat/long required" - policy call
