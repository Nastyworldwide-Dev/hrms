GOAL: Mia (Attendance Report Viewer) sees her whole company on Nadi Team, view only.
DONE WHEN: test_team_company_view.py 11 green; team-company-view js green; probe28 run+run2 9/9 PASS; vite build passes.
CHECK: PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/tests/test_team_company_view.py && node --test frontend/src/views/__tests__/team-company-view.test.js frontend/src/views/__tests__/team-entitlement.test.js
