GOAL: A coarse reading that puts somebody at their desk stops sending them to
 their approver.
DONE WHEN: the allowance is min(accuracy, 250) for any reading inside the trust
 cap, never decreases as accuracy worsens, and the phone's preview agrees with
 the server case for case.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_geofence_allowance_has_no_cliff.py
 hrms/tests/test_geolocation_properties.py
