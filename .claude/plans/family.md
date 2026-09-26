CLASS: a failed read renders as the empty state (or as endless placeholders), so a person reads "no records"
frontend/src/components/ListView.vue onMounted — same-root (fixed: workflow lookup guarded, list always requested)
frontend/src/components/ListView.vue GEmptyState — same-root (fixed: only after the list answered)
frontend/src/components/ListView.vue ResourceError what — same-root (fixed: plain words, not the doctype)
frontend/src/views/Profile.vue Manager/Shift — same-root (fixed: ResourceError instead of placeholders forever)
frontend/src/views/More.vue — not-affected — static rows, reads nothing from the server
frontend/src/views/ChangePassword.vue — not-affected — reads nothing until Update password (its own error toast)
frontend/src/views/Settings (Profile.vue route) — same-root (same component as Profile)
