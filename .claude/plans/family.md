CLASS: a read of resource.data.<field> while the page is being set up, which throws when that read failed or has not landed (the gate lets such a person through)
frontend/src/data/notifications.js:20 same-root — to_user from the session cookie; imported by the header on every page
frontend/src/views/Profile.vue:305 same-root — details resource built only with an employee; else a failed read with Try again
frontend/src/data/employees.js:31 same-root — guarded
frontend/src/components/CheckInPanel.vue:309 not-affected — inside functions called after the employee loads (Home waits for it)
frontend/src/components/ListView.vue:396 not-affected — inside a computed evaluated on fetch, after the gate
frontend/src/views/attendance/ShiftRequestForm.vue:74 ticket alpha.15 — setup-time read on a form page; same guard to add
frontend/src/views/expense_claim/Form.vue:63 ticket alpha.15 — setup-time read on a form page; same guard to add
