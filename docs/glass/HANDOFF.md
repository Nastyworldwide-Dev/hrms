# HANDOFF
prompt:   Pass 3 — master data & data-backed controls closure
status:   controls PROVEN correct (queries/perms/render); empties genuine
commit:   69362af37 on nz-glass (verification/diagnosis pass — no new code)
mechanism: every Nadi Link field renders via ONE shared component (Link.vue) that
          queries frappe.desk.search.search_link (permission-enforcing) with the
          field's doctype + filters. Select fields come from get_doctype_fields.
empty-vs-broken (search_link AS the employee, exact frontend path, fresh.local):
          Expense Claim Type 5, Leave Type 10, Cost Center 10, Account 10, Shift
          Type 2, Department 10 — ALL load. Shift Location 0 = GENUINE empty (no
          records, matches geofence config-absence), not a broken query. No
          permission fence hides valid data; no wrong doctype/filter.
expense-type: authoritative source = Expense Claim Type doctype. Employee reads it
          (has_permission True) and the dropdown renders every record. Live "No
          results" = missing master data on that instance, provisioned in Verifica
          Desktop -> Expense Claim Type. NOT a code defect.
hidden-fields: cost_center resolves (Main - _TC); currency falls back to company
          currency (salary_currency null -> INR); exchange_rate defaulted 1.
          payable_account = NULL because _Test Company has no
          default_expense_claim_payable_account. It is mandatory_depends_on
          !is_paid, so on a company missing that default the HIDDEN field blocks
          submit with no employee-visible cause (item 5). CONFIG gap (set the
          company default in Verifica Desktop) + a UX-hardening opportunity
          (surface unresolved hidden requirements). Same class as expense-type.
persistence: options render; expense insert+submit was bench-verified in the prior
          expense pass; approver options match the save-time fence (no offer-then-
          reject).
same-class: one pattern — a control depends on backend config; the query path is
          shared+correct and empties are genuine (Expense Type live, Shift
          Location, company payable account). No broken-query defect anywhere.
unverified/provisioning: live provisioning of Expense Claim Types, Shift Locations
          (coords), and the company payable account; live-instance confirmation
          (no access to Verifica).
verdict:  DATA-BACKED CONTROLS CLOSED — the controls query/permission/render
          correctly and empties are genuine config gaps (operationally explicit),
          not code defects. Provisioning + hidden-field UX hardening noted.
