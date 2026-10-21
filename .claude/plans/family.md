CLASS: one fact read from two sources on two screens (shift: default_shift on You vs today's assignment on Home) (UX review F3)
frontend/src/views/Profile.vue:370 same-root — now reads nowResource (hrms.api.now), default as fallback
frontend/src/components/NowBar.vue:188 not-affected — the source of truth (assignment, else default)
frontend/src/views/team/TeamRoster.vue:1 not-affected — the roster shows planned shifts per day by design, not "today's shift"
