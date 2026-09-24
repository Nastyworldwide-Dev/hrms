CLASS: layout fields kept by kind survive when every data field under them is filtered out (empty section headings)

Instance: New expense showed 9 section headings, 6 empty (Currency, Taxes & charges, Advance payments, Totals, Exchange gain/loss, Accounting dimensions); Time off showed an empty "Other details" (alpha.6 audit §F, 24 Sep 2026).

Where section headings are drawn:
- frontend/src/components/FormView.vue tabbed branch (tabFields) — same-root (fixed: tabFields built from shownFields)
- frontend/src/components/FormView.vue flat branch (props.fields) — same-root (fixed: v-for over shownFields)
- frontend/src/components/FormField.vue Section Break branch — not-affected: draws what it is given; the decision is upstream
- each screen's getFilteredFields (leave, expense, attendance, shift, OT) — not-affected: allowlists are right to keep layout by kind; FormView now decides visibility once for all

Locked: utils/__tests__/visibleSections.test.js (8). Measured after build: expense 9 -> 3 headings, time off "Other details" gone.
