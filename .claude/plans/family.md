CLASS: a PWA door to banked overtime. HR policy (owner, 23 Sep 2026): "we dont
use banked overtime" — the server already treats the bank as deprecated
(ot_request.py: "replacement-leave bank deprecated — per-day grant now").

Doors and verdicts:
frontend/src/views/ot/ReplacementLeave.vue — same-root, deleted (the bank page).
frontend/src/views/ot/ReplacementLeaveClaimForm.vue — same-root, deleted (spend-the-bank form).
frontend/src/components/ReplacementLeaveCard.vue — same-root, deleted (converter on the Leaves dashboard).
frontend/src/router/ot.js — same-root, /replacement-leave/* redirects to /requests (saved links).
hrms/api/needs_you.py ROW_COPY — same-root, a still-open claim routes the approver to Approvals.
hrms/hr/doctype/pwa_notification/pwa_notification.py PWA_DETAIL_PATHS — same-root, entry removed; such a push opens Home.
frontend/src/components/ReplacementLeaveClaimItem.vue + RequestPanel lists — not-affected here: they show EXISTING claims in the employee's history (records, not a bank); removing history is data, left for the owner.
hrms/api/approval.py DECIDE_THEN_SUBMIT "Replacement Leave Claim" — not-affected here: an open claim must still be decidable; removing the doctype is schema/policy, left for the owner.
frontend/src/views/ot/OTRequestForm.vue "Replacement Leave" compensation option — ticket: owner ruling needed (the OT form still offers RL as compensation, per employee setting; that is pay policy, not a bank screen).
