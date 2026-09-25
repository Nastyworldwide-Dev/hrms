GOAL: a person still working at 12 am / 3 am sees Check out and their tap is stored as the check-out
DONE WHEN: WebKit button at 00:01/01:01/03:00/05:59 = Check out, 06:01 = Check in; server tests: tap 00:01/03:00 -> OUT, early-shift arrival -> IN
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/api/test_remote_checkin.py; node --test frontend/src/utils/__tests__/checkinSession.test.js
