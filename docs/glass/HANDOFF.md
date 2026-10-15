# HANDOFF
prompt:   SOPs still empty after alpha.50 (15 Oct)
status:   done
commit:   8a9222d70 on nz-glass (tag v2.0.0-alpha.51)
files:    frontend/src/views/sop/SopFormSheet.vue (Company row, All companies default, sent once read)
          frontend/src/views/__tests__/sop-form-company.test.js
verify:   node --test frontend/src/views/__tests__/sop-form-company.test.js
flags:    root cause = Frappe filled HR's own company into a Nadi-made SOP (update_if_missing from the Company UP). Strict UP is OFF on live (owner). Existing SOPs NOT changed: HR re-saves each with Company = All companies.
next:     deploy alpha.51; HR re-saves existing SOPs; check as staff in another company
