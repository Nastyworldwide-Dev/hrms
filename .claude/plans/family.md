CLASS: two figures for ONE quantity rounded by different rules in the same sentence, so a refused claim can read equal to its cap ("at most 8h 52m" against a claim of 8h 52m). The cap must round down (never name time the check refuses) and a refused claim up (always strictly above the cap).
hrms/utils/ot_precision.py:hours_as_words same-root (fixed here: rounding="nearest"|"down"|"up")
hrms/hr/doctype/ot_request/ot_request.py:validate_claimed_hours same-root (fixed here: claim "up", cap "down")
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:86 ticket ticket-ot-request-py-refactor — raw hours in a refusal, same class
frontend/src/components/RequestActionSheet.vue:formatHours ticket ticket-ot-request-py-refactor — OD4 decimals in the sent sheet
hrms/mixins/pwa_notifications.py not-affected — no OT hours in any notice
