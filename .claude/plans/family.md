CLASS: text and columns that each screen sized and placed its own way
design/tokens.json type scale — same-root (Apple leading/size, SF tracking; one-line numerals kept 1.0)
frontend/tailwind.config.js fontSize — same-root (frappe-ui 13px/420/+0.02em -> iOS styles; 56 templates)
frontend/src/theme/glass-components.css .g-cal__dow — same-root (contrast 3.26 -> ink2)
design/tokens.json content-column-lg — same-root (672, owner ruling R2)
frontend/src/theme/glass-components.css one desktop column — same-root (bar row + large title on the content column)
frontend/src/views/*.vue, ListView/FormView/WorkflowActionSheet — same-root (no lg:mx-0 / lg:p-7 / max-w-3xl / sm:w-96 / two-column split)
design/tokens.json tab-label tracking — not-affected — kept 0 to fit 320 px
