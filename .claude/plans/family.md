CLASS: an editor button that makes content the reader removes: Image/Video store the file inside the text as data:, safeHtml strips data: URLs, so staff saw an empty picture.
frontend/src/views/sop/SopFormSheet.vue same-root (own TOOLBAR without Image/Video; pictures go through "Add a file", a private File on the SOP)
frontend/src/components/FormField.vue ticket alpha.39 — its Text Editor keeps the default menu (Image included) for other doctypes; same class wherever that HTML is read through safeHtml
frontend/src/utils/safeHtml.js not-affected — stripping data: is correct
