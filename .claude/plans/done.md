GOAL: nobody picks their approver; the check-in toast names the approver
DONE WHEN: real-DB: staff send the manager above their approver -> saved as their own approver; WebKit: each form's Goes to is one disabled option
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_own_approver_is_set_not_chosen.py
