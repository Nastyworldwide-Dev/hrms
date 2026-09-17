GOAL: An applicant with somebody above them never approves their own request,
 whatever the HR Settings tickboxes say.
DONE WHEN: _decision_access asks is_own_employee and refuses an "Approved"
 self-decision while get_designated_approvers finds anyone above the applicant;
 the top of the chain is unchanged; rejecting your own request still works.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_nobody_approves_their_own_request_under_an_approver.py; and
 cd /home/nabil/verify-bench/apps/hrms && /home/nabil/verify-bench/env/bin/python
 -m unittest hrms.api.test_decision_access
