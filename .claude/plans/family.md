CLASS: a shared "fill the rest" flex rule growing a fixed-size icon, stealing the value's space
frontend/src/theme/glass-components.css:3998 same-root — the rule now skips svg
frontend/src/components/EmployeeCheckinItem.vue:8 same-root — the chevron that grew (fixed by the rule)
frontend/src/components/RequestBalances.vue:1 same-root — its chevron has its own flex rule; the rule change is harmless
frontend/src/components/RequestList.vue:1 not-affected — icons sit in .g-row, not .g-form-row
frontend/src/components/Announcements.vue:1 not-affected — same
frontend/src/views/Profile.vue:1 not-affected — same
