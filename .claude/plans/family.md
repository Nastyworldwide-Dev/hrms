CLASS: a sheet built before the grouped form (labels above boxed controls, "=/>/<" pickers, a footer band of mismatched buttons)

Instance: plan §2 0.6 — Filters sheet on every list (owner's alpha.6 shots).

Sites:
- frontend/src/components/ListFiltersActionSheet.vue — same-root (one inset group of FormField rows, "All" when empty, Reset as a row)
- frontend/src/components/ListView.vue — same-root (Done in the sheet bar applies; condition from utils/listFilters.js)
- frontend/src/components/Link.vue placeholder — same-root (empty Link row reads "All" in a filter; forms pass nothing, unchanged)
- frontend/src/components/FormField.vue — same-root (forwards placeholder to Link)
- the 7 list views' FILTER_CONFIG — not-affected: their fields and options are unchanged; the old "=" default is kept for every field except from/to/start/end dates, which now keep a range (>= / <=) instead of an exact day
- frontend/src/components/glass/GModal.vue confirm slot — not-affected: already existed (alpha.6 B8); first caller

Locked: utils/__tests__/listFilters.test.js (3). Verified in WebKit: rows 44 pt, "All" trailing, Done applies + closes + lights the filter button.
