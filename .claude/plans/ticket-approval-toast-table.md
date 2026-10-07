# Ticket: approvalToast — table of outcomes

Hotspot: frontend/src/utils/approvalToast.js (4 fixes/90d; 23 Sep: hours as
time, then the zero-hours empty slot).

Do: one table of (decision, repair shape) -> {title, text, tone} with a test
row per shape (repaired with hours, repaired to 0, not repaired + each reason
code, reject). Build sentences from parts that exist, never a fixed template
with an optional slot.

Upgrade trigger: the next bug in approvalToast.js.
