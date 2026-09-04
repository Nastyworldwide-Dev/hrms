# HANDOFF
prompt:   Replacement Leave = per working day (not banked) + Desk approval + sweep fixes
status:   done, reviewed, pushed — SAFE
commit:   3fcee01f4 on nz-glass (RL: 3fe56575f feat + 3fcee01f4 review-fix)
files:    hrms/utils/ot_calculation.py — replacement_leave_days (4h blocks, unit-tested)
          hrms/hr/utils.py — grant_replacement_leave / reverse_replacement_leave
          hrms/hr/doctype/ot_request/ot_request.{json,py} — per-day grant on approval,
            reverse-by-stored-days on cancel, bank neutered (non-destructive)
          frontend OTRequestForm.vue + attendance/Dashboard.vue — RL shows day blocks, hides <4h
          (earlier: Desk Approve/Reject via approval.decide; Shift Request self-approval guard)
verify:   bench run-tests --module hrms.utils.test_ot_calculation (block conversion)
          Deploy: a Leave Period must cover today, or the RL grant refuses (correctly).
flags:    Review CRITICAL fixed (cancel recomputed days from live ratio -> now reverses the
          stored granted days). Legacy RL card/claim inert + auto-hidden, NOT deleted.
          Confirm no in-flight Replacement Leave Claim data before relying on the new model.
next:     deploy; smoke-test RL: 4h OT day -> approve -> ½ day in balance; cancel -> reversed.
