# HANDOFF
prompt:   28 Sep 2026 — alpha.18: HR's new OT rates from the deploy day
status:   done
commit:   3873cdcf6 on nz-glass (tag v2.0.0-alpha.18)
files:    hrms/utils/ot_calculation.py
          hrms/hr/doctype/shift_overtime_rate/shift_overtime_rate.json
          hrms/hr/doctype/shift_type/shift_type.py
          hrms/hr/doctype/ot_request/ot_request.py
          hrms/patches/v16_0/ot_rates_from_policy_date.py
          hrms/tests/test_ot_rates_from_a_date.py
          docs/glass/CHANGELOG.md
verify:   after deploy: Desk > Shift Type > Overtime Rates shows new PH/Off rows dated deploy day; HR Settings has the same date
flags:    the date is set once by the deploy patch — never edit it; a shift HR had already dated is skipped and named in the Error Log
next:     owner deploys alpha.17 + alpha.18; Amy retests 29 Sep; roster Day Type needs the Desk screen name
