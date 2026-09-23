CLASS: a sheet presented as a phone sheet on a desktop (audit F-5 / APP-14).
Measured 23 Sep at 1280x800: wrapper flush to the bottom (y=663); the scrim
lived inside the page's content box, so it started at x=216 and the side nav
stayed bright and clickable under an open sheet.

Surfaces and verdicts:
frontend/src/components/glass/GModal.vue — same-root: scrim teleported to body (covers the side nav; tap there closes).
frontend/src/theme/glass-components.css .g-modal at lg — same-root: ::part(content) centred (top 50%, translate -50%).
GActionSheet / every GModal caller — same-root by inheritance (one component).
Phone (<1024px) — not-affected: live at 390x844 still a bottom sheet (y=707).
