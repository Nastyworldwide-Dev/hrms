# Rest-day overtime rounds like weekday (owner ruling 27 Sep 2026)

FLOW: get_ot_claim_capacity sizes every claim (form summary, discovery list, OTRequest.set_punch_verified_cap). Its holiday part (nonworking_hours) was stored exact; now round_ot_pay_hours like the weekday part. Payroll prices the APPROVED claimed_hours, so pay follows the banded claim. The worked record (Attendance.ot_hours, breakdowns) keeps every minute.

MOCKUP: none (a pay-rule change; the Overtime form shows 9 instead of 8.876944444 in the Hours box).

EXPECTED OUTPUT: rest day 10:08-13:22 claims 3.0 h (was 3.233); 09:00-17:52:37 claims 9.0 h (was 8.876944); every rest-day claim is a multiple of 0.5; mixed days band each part separately; weekday unchanged.

Owner ruling recorded: "round like weekday" (27 Sep 2026, reply to question 2).
