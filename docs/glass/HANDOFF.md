# HANDOFF
prompt:   OT form v2 + claimable discoverability + OT Pay 30-min rounding + Dashboard-0
status:   done (deploy-ready); overnight-checkout + dashboard-0 code fix = next
commit:   aa5c3c264 on nz-glass (chain: f7de30760 f1c38b274 74d85bf23 8e4d6a173 back to 21ba28d72)
files:    hrms/utils/ot_calculation.py — round_ot_pay_hours (30-min bands, OT Pay only)
          hrms/hr/doctype/ot_request/ot_request.{json,py} — punch/claimed Int->Float, apply rounding
          hrms/api/__init__.py — get_ot_claim_summary + get_claimable_ot_summary round for OT-Pay
          frontend/.../OTRequestForm.vue — reason required, attachments removed, claimed read-only
          frontend/.../attendance/Dashboard.vue — "Overtime to claim" card (get_claimable_ot_summary)
          hrms/hr/doctype/hrms_erp_instance/hrms_erp_instance.js — Release Stamp button (contamination recovery)
verify:   bench run-tests --module hrms.utils.test_ot_calculation (round_ot_pay_hours boundaries)
          yarn --cwd frontend test (132/135; 3 pre-existing unrelated fails)
flags:    Dashboard-0 = CONFIG (user has no default company; card filters by it). Not a code bug.
          DO NOT enable Unlock Mirrored Writes until Nasty-Dev cleanup (Release Stamp -> re-sync -> parity 4-clean).
next:     overnight/next-day checkout (checkout after midnight belongs to the shift that began prior day)
