GOAL: the last three surfaces that read a tap's day by the clock follow the one work-day rule
DONE WHEN: lone-IN closer, OT form's "why no claim" list and the check-ins list group a no-shift after-midnight OUT on its IN's day; tests red on HEAD, green now
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/api/test_day_taps_belong_to_the_work_day.py hrms/tests/test_lone_in_closer.py && cd frontend && node --test src/utils/__tests__/dayGroups.test.js
