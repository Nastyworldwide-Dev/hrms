CLASS: a read-only sheet taking its labels from the fillable-fields list (get_doctype_fields drops links the caller cannot open).

Call sites of getFieldInfo / get_doctype_fields for display:
frontend/src/views/Profile.vue Your details — same-root, fixed (own labels, empty rows left out).
Forms (FormView) — not-affected: they SHOULD use the fillable list; a field the employee cannot fill is correctly absent.
