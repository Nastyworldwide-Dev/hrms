CLASS: a sheet's scroll chains into the page behind it (overscroll-behavior auto on the sheet scroller)
frontend/src/theme/glass-components.css .g-sheet — same-root (fixed: overscroll-behavior-y contain)
frontend/src/components/glass/GModal.vue — not-affected — renders .g-sheet; the rule lives on the class, one place
frontend/src/components/ListView.vue — not-affected — page scroller is ion-content; the document never scrolls (html overflow hidden, d13122051)
