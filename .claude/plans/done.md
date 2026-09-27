GOAL: a rest-day or public-holiday overtime claim is banded to 30 minutes like a weekday claim (owner ruling "round like weekday").
DONE WHEN: get_ot_claim_capacity rounds nonworking_hours with round_ot_pay_hours; tests pin 3h14m -> 3.0 and 8h52m -> 9.0 and every claim on a half hour.
CHECK: pytest hrms/tests/test_ot_nonworking_hours.py (3 new red -> green, 4 updated to the ruling); bench savepoint: rest day 09:00-17:52:37 claim 9.0, worked 8.8769 kept
