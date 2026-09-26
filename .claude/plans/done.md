GOAL: the installed app opens offline: its service worker controls /hrms and keeps the last good page
DONE WHEN: controller = /hrms/sw.js with scope /hrms; an offline relaunch loads Today instead of a browser error
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_pwa_service_worker.py && cd frontend && node --test src/__tests__/sw.test.js
