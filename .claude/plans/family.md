CLASS: a library imported by name pulls its whole component set into every first download
frontend/vite.config.js alias frappe-ui -> src/frappeUiLean.js — same-root (only the data helpers, toast, ErrorMessage)
frontend/vite.config.js alias Toast icon -> src/toastIcons.js — same-root (6 glyphs instead of all of feather-icons)
frontend/vite.config.js manualChunks frappe-ui — same-root (removed: forced the whole library into one chunk)
frontend/src/components/FormField.vue TextEditor — same-root (loaded only when a rich-text field shows)
frontend/src/main.js Button/Input/FormControl — same-root (unused global registrations removed)
frontend/src/components/PdfInlineViewer.vue — not-affected — already lazy (SOP page only)
@ionic/core (542 KB) — ticket: next largest; needs per-component imports, own slice
