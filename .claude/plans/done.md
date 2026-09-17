GOAL: A staff punch photo reaches the server on a site that forbids public
 file uploads by non-System-Managers.
DONE WHEN: the PWA stores the frame through hrms.api.remote_checkin.upload_selfie
 (image type + size checked, stored for the caller), never frappe's upload_file.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_selfie_upload_survives_a_public_file_lockdown.py; and
 cd frontend && node --experimental-test-module-mocks --test
 src/components/__tests__/CheckInPanel.test.js
