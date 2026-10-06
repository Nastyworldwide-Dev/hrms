CLASS: HR could not write an SOP the way staff read it: the Nadi edit sheet was a plain textarea fed stored HTML (HR saw raw "<p>…<img src=…>"), with no headings, lists, bold or pictures, no preview, and no line saying who would see it; the rich editor, once added, collapsed to 2 px in a stacked form row.
frontend/src/views/sop/SopFormSheet.vue same-root (frappe-ui TextEditor as FormField uses it; who-sees line; "As staff see it" preview through safeHtml + .sop-prose; plain-text wrap only for untagged legacy values)
frontend/src/theme/glass-components.css same-root (.sop-prose reading styles have one owner; stacked-row rule so the editor keeps its height: the row fill rule weighs 0,4,1)
frontend/src/views/sop/SopDetail.vue same-root (keeps the class only)
frontend/src/components/FormField.vue not-affected — its Text Editor sits in a non-stacked row (checked: the fill rule's flex:1 1 0 is right there)
hrms/api/sop.py, hrms/overrides/sop_document_row_scope.py not-affected — who sees what probed 6 Oct as staff, supervisor, HR: correct
