GOAL: PWA "My KPI" becomes "KPI", with a CEO-designation-only, read-only Team KPI
      tab carrying a department selector.
DONE WHEN: non-CEO sees today's page unchanged; CEO sees the tab; get_team_kpi
      raises PermissionError for anyone whose Employee.designation is not CEO.
CHECK: verify-bench probe (sites/probe_team_kpi.py) — 10/10 PASS, rolled back;
      `yarn build` green; ruff + eslint clean.
