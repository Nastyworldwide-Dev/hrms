# HANDOFF
prompt:   geofence false "not in area" (HR)
status:   done
commit:   4d6aa75a9 on nz-glass
files:    hrms/utils/geofence.py
          hrms/utils/test_geofence.py
verify:   python3 -m pytest -q hrms/utils/test_geofence.py
flags:    cause was the imprecise-fix rule (accuracy > 250 m) running before the inside-radius test; "0m outside" in the approver notification was the tell; point estimate now trusted inside the radius up to 2000 m; verified on fresh.local with real punches
next:     Nabil deploys; staff who were flagged indoors re-punch; then audit fix plan rows 1-2
