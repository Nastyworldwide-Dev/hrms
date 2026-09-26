GOAL: a check-out after midnight shows on its work day, and the next date says where it counted
DONE WHEN: real-DB probe with the owner's taps: 25 Sep has 4 taps, last next_day; 26 Sep has 0 taps + counted_on 25 Sep
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/api/test_day_taps_belong_to_the_work_day.py
