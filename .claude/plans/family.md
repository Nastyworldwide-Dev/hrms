CLASS: a second scroller nested inside ion-content (page scrolls past its content; double scroll chain)
frontend/src/components/ListView.vue:inner div — same-root (fixed here: ion-content is the one scroller, ionScroll drives paging)
frontend/src/components/FormView.vue:48 — not-affected — FormView is not inside ion-content; its scroller is the page's only one (sticky action bar); audit shows no overscroll
frontend/src/views/ChangePassword.vue:11 — not-affected — audit: fits, no overscroll (grow inside min-h-full column)
frontend/src/views/sop/SopDetail.vue:17 — not-affected — no ion-content wrapper; single scroller
frontend/src/components/ExpensesTable.vue:78 — not-affected — bounded field list inside a sheet
frontend/src/components/PdfInlineViewer.vue:10 — not-affected — max-h 70vh viewer, intended inner scroll
