CLASS: a section that renders nothing while loading, then pushes the page
down (audit F-12 / APP-28, CWV-CLS limit 0.1). Measured 23 Sep at 390x844:
Home 0.002 (already fixed), Requests 0.391.

Surfaces and verdicts:
frontend/src/components/RequestBalances.vue — same-root, fixed here: holds its place with skeletons (grid + two rows) on first load. Requests after: 0.058.
frontend/src/views/Home.vue — not-affected: 0.002 measured.
