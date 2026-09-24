> **Verified 24 Sep 2026 (Claude, against code):** produced by a read-only helper. Claims checked:
> - "expenses table not prevented from empty submission (CRITICAL)": **REFUTED.** `FormView.vue:850` treats an empty required table as missing, and the server requires the table (`reqd: 1`).
> - "Leave Application: no jargon": **REFUTED.** Employees see "Leave type", "Leave approver", "Leave approver name", "Total leave days" (measured, alpha6-pages.md §F).
> - Risks 4–10 ("company hidden", "depends on auto-fill"): **not defects.** The screen journey filed every type successfully (`frontend/e2e/alpha6-journey.mjs`, 8/8).
> Treat the rest as a field inventory, not as findings.

# PWA Request Form Field Mapping

## Leave Application

| fieldname | label | type | reqd? | default | PWA form | Approver sheet | Notes |
|---|---|---|---|---|---|---|---|
| naming_series | Series | Select | Y | HR-LAP-.YYYY.- | hidden | N | System field |
| employee | Employee | Link | Y | — | hidden on new, shown on existing (readonly) | Y | Auto-filled from session on new |
| employee_name | Employee Name | Data | — | — | hidden on new, shown on existing (readonly) | Y | Fetched from employee |
| leave_type | Leave Type | Link | Y | — | shown | Y | Required user input |
| company | Company | Link | Y | — | hidden on new, shown on existing (readonly) | N | Fetched from employee |
| department | Department | Link | — | — | hidden on new, shown on existing (readonly) | N | Fetched from employee, readonly |
| from_date | From Date | Date | Y | — | shown | Y | Core: leave start date |
| to_date | To Date | Date | Y | — | shown | Y | Core: leave end date |
| half_day | Half Day | Check | — | 0 | shown | Y | Optional: makes half_day_date required |
| half_day_date | Half Day Date | Date | — | — | hidden until half_day checked | Y | Conditional on half_day, constrained to date range |
| total_leave_days | Total Leave Days | Float | — | — | shown (readonly) | Y | Auto-calculated server-side |
| description | Reason | Small Text | — | — | shown | Y | Visible as "Reason" to employees |
| leave_balance | Leave Balance Before Application | Float | — | — | shown (readonly) | Y | Fetched/calculated, shown after leave_type picked |
| leave_approver | Leave Approver | Link | — | — | shown | N | Fetched from department_approvers |
| leave_approver_name | Leave Approver Name | Data | — | — | shown (readonly) | N | Display only, auto-filled |
| status | Status | Select | Y | Open | hidden on new, shown on existing (readonly) | Y | Set by approval workflow |
| posting_date | Posting Date | Date | Y | Today | hidden on new, shown on existing (readonly) | N | Set to today on validate |
| follow_via_email | Follow via Email | Check | — | 1 | hidden | N | Print-hidden, not user-facing |
| salary_slip | Salary Slip | Link | — | — | hidden | N | Backend-only, set by payroll |
| color | Color | Color | — | — | hidden | N | Desk calendar field |
| letter_head | Letter Head | Link | — | — | hidden | N | Print-only field |
| amended_from | Amended From | Link | — | — | hidden | N | Frappe amendment tracking |

### RISKS
- None: all required fields are either shown or auto-filled server-side.
- `half_day_date` is shown conditionally, but becomes required only when `half_day` is checked, and the PWA form handles this dependency.

### JARGON
- None: labels use plain language ("Reason", not "Description").

---

## Expense Claim

| fieldname | label | type | reqd? | default | PWA form | Approver sheet | Notes |
|---|---|---|---|---|---|---|---|
| naming_series | Series | Select | Y | HR-EXP-.YYYY.- | hidden | N | System field |
| employee | From Employee | Link | Y | — | hidden on new, shown on existing (readonly) | Y | Auto-filled from session on new |
| employee_name | Employee Name | Data | — | — | hidden on new, shown on existing (readonly) | Y | Fetched from employee |
| department | Department | Link | — | — | hidden on new, shown on existing (readonly) | N | Fetched from employee if empty |
| company | Company | Link | Y | — | hidden on new, shown on existing (readonly) | N | Fetched from employee; defaults to employee.company |
| expense_approver | Expense Approver | Link | — | — | shown | N | Fetched from department_approvers |
| approval_status | Approval Status | Select | — | Draft | hidden | Y | Set by approval workflow |
| currency | Currency | Link | Y | — | hidden (seeded in model as employee.salary_currency) | N | PWA hardcodes to company currency, not salary_currency |
| exchange_rate | Exchange Rate | Float | Y | — | hidden (seeded to 1.0) | N | PWA always uses rate 1 in company currency |
| expenses | Expenses | Table | Y | — | shown | Y | Expense line items (see Expense Claim Detail below) |
| posting_date | Posting Date | Date | Y | Today | shown | Y | Defaulted to today |
| total_claimed_amount | Total Claimed Amount | Currency | — | — | shown (readonly) | Y | Calculated from expenses table |
| total_sanctioned_amount | Total Sanctioned Amount | Currency | — | — | shown (readonly) | Y | Calculated from expenses table |
| grand_total | Grand Total | Currency | — | — | shown (readonly) | N | Total + taxes, shown on form |
| total_taxes_and_charges | Total Taxes and Charges | Currency | — | — | hidden | Y | Calculated if taxes table present |
| total_amount_reimbursed | Total Amount Reimbursed | Currency | — | — | hidden on new, shown on existing (readonly) | N | Backend-set after payment |
| total_advance_amount | Total Advance Amount | Currency | — | — | hidden | Y | Advance deductions table |
| is_paid | Is Paid | Check | — | 0 | hidden | N | Accounting field |
| mode_of_payment | Mode of Payment | Link | — | — | hidden | N | Accounting field |
| bank_or_cash_account | Bank / Cash Account | Link | — | — | hidden | N | Accounting field |
| payable_account | Payable Account | Link | — | — | hidden (seeded from company default) | N | Accounting field, required if not is_paid |
| cost_center | Cost Center | Link | — | — | hidden (seeded from company default) | N | Accounting field, allow_on_submit |
| project | Project | Link | — | — | hidden | N | Accounting field, allow_on_submit |
| gain_loss_account | Gain Loss Account | Link | — | — | hidden | N | Exchange gain/loss field |
| total_exchange_gain_loss | Total Exchange Gain/Loss | Currency | — | — | hidden | N | Exchange gain/loss field |
| taxes | Expense Taxes and Charges | Table | — | — | hidden in PWA (form shows only one tab with expenses) | N | Tax table, not in employee flow |
| advances | Advances | Table | — | — | hidden | N | Advance deductions table |
| vehicle_log | Vehicle Log | Link | — | — | hidden | N | Integration field |
| delivery_trip | Delivery Trip | Link | — | — | hidden | N | Integration field |
| remark | Remark | Small Text | — | — | hidden | N | Backend notes |
| status | Status | Select | — | Draft | hidden on new, shown on existing (readonly) | Y | Calculated: Draft/Paid/Unpaid/Rejected/Submitted/Cancelled |
| amended_from | Amended From | Link | — | — | hidden | N | Frappe amendment tracking |
| base_total_sanctioned_amount | Total Sanctioned Amount (Company Currency) | Currency | — | — | hidden | N | Exchange tracking |
| base_total_advance_amount | Total Advance Amount (Company Currency) | Currency | — | — | hidden | N | Exchange tracking |
| base_grand_total | Grand Total (Company Currency) | Currency | — | — | hidden | N | Exchange tracking |
| base_total_claimed_amount | Total Claimed Amount (Company Currency) | Currency | — | — | hidden | N | Exchange tracking |
| base_total_taxes_and_charges | Total Taxes and Charges (Company Currency) | Currency | — | — | hidden | N | Exchange tracking |
| clearance_date | Clearance Date | Date | — | — | hidden | N | Accounting field |

### Expense Claim Detail (Child Table)

| fieldname | label | type | reqd? | default | PWA form | Notes |
|---|---|---|---|---|---|---|
| expense_date | Expense Date | Date | — | Today | shown | When the expense was incurred |
| expense_type | Expense Claim Type | Link | Y | — | shown | Must link to Expense Claim Type |
| default_account | Default Account | Link | — | — | hidden (readonly) | Fetched from expense_type |
| description | Description | Text Editor | — | — | shown | Rich text, employee enters details |
| amount | Amount | Currency | Y | — | shown | What employee claims |
| sanctioned_amount | Sanctioned Amount | Currency | — | — | shown | What approver allows (auto-filled by approver workflow) |
| cost_center | Cost Center | Link | — | — | hidden on child, allow_on_submit | Can be overridden by parent cost_center |
| project | Project | Link | — | — | hidden on child, allow_on_submit | For project costing |
| base_amount | Amount (Company Currency) | Currency | — | — | hidden | Exchange-converted |
| base_sanctioned_amount | Sanctioned Amount (Company Currency) | Currency | — | — | hidden | Exchange-converted |

### RISKS
- **CRITICAL**: `expenses` table is required (reqd: 1) but form does not prevent empty submission. Employee must add at least one expense item or save fails. The component prevents visual submission without items, but no server-side guard.
- `currency` defaults to employee.salary_currency on the doctype, but PWA explicitly sets it to company currency (line 133 of Form.vue). If this seed fails, the field is required and form blocks submit.
- `exchange_rate` is required but always set to 1.0 by PWA before save.
- `payable_account` is required if `is_paid` = 0, but it's seeded from company default, so should not fail.

### JARGON
- "From Employee" is not a common phrasing; "Employee" would be clearer.
- "Expense Claim Type" is jargon; "Expense Category" or just "Type" would be plainer.

---

## Shift Request

| fieldname | label | type | reqd? | default | PWA form | Approver sheet | Notes |
|---|---|---|---|---|---|---|---|
| shift_type | Shift Type | Link | Y | — | shown | Y | Required: which shift to request |
| employee | Employee | Link | Y | — | hidden on new, shown on existing (readonly) | Y | Auto-filled from session on new |
| employee_name | Employee Name | Data | — | — | hidden on new, shown on existing (readonly) | Y | Fetched, display only |
| department | Department | Link | — | — | hidden on new, shown on existing (readonly) | N | Fetched from employee, readonly |
| company | Company | Link | Y | — | hidden on new, shown on existing (readonly) | N | Required, fetched from employee |
| approver | Approver | Link | Y | — | shown | N | Fetched from employee.shift_request_approver |
| from_date | From Date | Date | Y | — | shown | Y | Start date of shift request |
| to_date | To Date | Date | — | — | shown | Y | End date (optional on doctype, but form suggests both dates) |
| status | Status | Select | Y | Draft | hidden on new, shown on existing (readonly) | Y | Approval status |
| amended_from | Amended From | Link | — | — | hidden | N | Frappe amendment tracking |

### RISKS
- `company` is required but hidden on new form. It's auto-filled from employee.company during validation (line 117 of ShiftRequestForm.vue sets it via validateForm), so should not fail.
- `to_date` is not marked required on doctype but from_date > to_date validation suggests both are expected. The backend likely has a custom validation. Passing this to the backend without to_date may fail validation.

### JARGON
- None identified.

---

## Attendance Request

| fieldname | label | type | reqd? | default | PWA form | Approver sheet | Notes |
|---|---|---|---|---|---|---|---|
| employee | Employee | Link | Y | — | hidden on new, shown on existing (readonly) | N | Auto-filled from session |
| employee_name | Employee Name | Data | — | — | hidden on new, shown on existing (readonly) | N | Fetched, display only |
| status | Status | Select | — | Open | hidden on new, shown on existing (readonly) | Y | Approval status (readonly) |
| department | Department | Link | — | — | hidden on new, shown on existing (readonly) | N | Fetched from employee, readonly |
| company | Company | Link | Y | — | hidden on new, shown on existing (readonly) | N | Fetched from employee, required |
| from_date | From Date | Date | Y | — | shown | Y | Request start date |
| to_date | To Date | Date | Y | — | shown | Y | Request end date |
| half_day | Half Day | Check | — | 0 | shown | Y | Check if half-day request |
| half_day_date | Half Day Date | Date | — | — | hidden until half_day checked | Y | Which day is half-day |
| include_holidays | Include Holidays | Check | — | 0 | shown | Y | Whether to include holiday dates |
| shift | Shift | Link | — | — | shown | Y | Shift type (optional, but comment says "will not overwrite") |
| in_time | In Time | Time | — | — | shown | Y | Actual worked hours: start time (optional, must pair with out_time) |
| out_time | Out Time | Time | — | — | shown | Y | Actual worked hours: end time (optional, must pair with in_time; overnight shifts supported) |
| reason | Reason | Select | Y | — | shown | Y | Work From Home / On Duty |
| explanation | Explanation | Small Text | — | — | shown | N | Why the attendance request |
| amended_from | Amended From | Link | — | — | hidden | N | Frappe amendment tracking |

### RISKS
- `company` is required but hidden on new form. Auto-filled from employee.company during validateForm (line 122 of AttendanceRequestForm.vue should do this, though it only sets employee).
- `in_time` and `out_time` have no individual `reqd` flag, but form validation (line 101-102) blocks submit if only one is set: "Give both the time in and the time out". This is a client-side check; server may allow partial submission.
- `half_day_date` has `mandatory_depends_on: "half_day"` but the PWA does not set this — it only conditionally hides the field. If submitted with half_day=1 but no half_day_date, the backend may reject.

### JARGON
- "On Duty" is ERP jargon; "On Official Work" or "On Assignment" might be plainer.

---

## OT Request

| fieldname | label | type | reqd? | default | PWA form | Approver sheet | Notes |
|---|---|---|---|---|---|---|---|
| employee | Employee | Link | Y | — | hidden on new, shown on existing (readonly) | Y | Auto-filled from session |
| employee_name | Employee Name | Data | — | — | hidden on new, shown on existing (readonly) | N | Fetched, display only |
| status | Status | Select | — | Open | hidden on new, shown on existing (readonly) | Y | Approval status (readonly) |
| department | Department | Link | — | — | hidden on new, shown on existing (readonly) | N | Fetched from employee, readonly |
| company | Company | Link | Y | — | hidden on new, shown on existing (readonly) | N | Fetched from employee, required |
| ot_date | OT Date | Date | Y | — | shown (via "Days you can claim" quick-picks) | Y | Which day the OT was worked |
| shift | Shift | Link | — | — | hidden on new, shown on existing (readonly) | Y | Auto-resolved from attendance for the day |
| punch_ot_hours | Punch-verified OT (hours) | Float | — | — | hidden on new (shown in summary panel as "Available to claim"), shown on existing (readonly) | Y | How much OT the punches prove; readonly |
| claimed_hours | Claimed Hours | Float | Y | — | shown (with error validation: ≤punch_ot_hours) | Y | How many hours the employee actually claims |
| compensation | Compensation | Select | — | — | hidden on new (shown in summary panel as "You claim"), shown on existing (readonly) | Y | Overtime Pay or Replacement Leave; set by employee.eligible_for_overtime_pay |
| explanation | Explanation | Small Text | Y | — | shown | Y | Why the OT is being claimed (made required by Form.vue line 286) |
| leave_allocation | Leave Allocation | Link | — | — | hidden | N | For RL: the allocation topped up on approval (for reversal on cancel) |
| leave_days_granted | Leave Days Granted | Float | — | — | hidden | N | For RL: exact days granted (for reversal if HR changes hours-per-day ratio) |
| amended_from | Amended From | Link | — | — | hidden | N | Frappe amendment tracking |

### RISKS
- `claimed_hours` is required but depends on `punch_ot_hours` being fetched. The form blocks submit with error messages (line 388-390 of OTRequestForm.vue) if `punch_ot_hours` is not yet loaded or if claimed > punch_ot_hours. Server-side validation should catch this, but the backend error may be confusing to the employee.
- `explanation` is made required by the PWA (line 286 of OTRequestForm.vue, reqd: 1), overriding the doctype's non-required field. This is intentional (HR asked for it back), but the PWA's requirement differs from the doctype's soft default.

### JARGON
- "Punch-verified OT" is jargon for check-in/check-out hours. Plainer: "Hours from your check-ins".
- "Compensation" is corporate speak; "How you'll be paid" or "Payout type" would be plainer.
- "Replacement Leave" is HR jargon; "Time Off" would be plainer.

---

## Employee Issue

| fieldname | label | type | reqd? | default | PWA form | Approver sheet | Notes |
|---|---|---|---|---|---|---|---|
| employee | Employee | Link | Y | — | hidden on new, shown on existing (readonly) | N | Auto-filled from session on new |
| employee_name | Employee Name | Data | — | — | hidden on new, shown on existing (readonly) | N | Fetched, display only |
| department | Department | Link | — | — | hidden on new, shown on existing (readonly) | N | Fetched from employee, readonly |
| company | Company | Link | — | — | hidden on new, shown on existing (readonly) | N | Fetched from employee, readonly |
| issue_type | What are you reporting? | Select | Y | — | shown | N | Leave Balance Discrepancy / Check-in / Check-out Problem / Other HR Issue |
| urgency | Urgency | Select | — | Medium | shown | N | Low / Medium / High |
| status | Status | Select | — | Open | hidden on new, shown on existing (readonly) | N | Open / In Progress / Completed (managed by HR, readonly) |
| leave_type | Which leave type? | Link | — | — | shown only if issue_type = "Leave Balance Discrepancy" | N | Conditional on issue_type |
| balance_shown | Balance shown (days) | Float | — | — | shown only if issue_type = "Leave Balance Discrepancy" | N | What employee sees |
| balance_expected | Balance you expect (days) | Float | — | — | shown only if issue_type = "Leave Balance Discrepancy" | N | What employee thinks is correct |
| affected_date | Affected date | Date | — | — | shown only if issue_type = "Check-in / Check-out Problem" | N | Which day had the issue |
| punch_affected | Which punch? | Select | — | — | shown only if issue_type = "Check-in / Check-out Problem" | N | Check-in / Check-out / Both |
| what_happened | What happened? | Select | — | — | shown only if issue_type = "Check-in / Check-out Problem" | N | Did not register / Wrong time / Could not access / Other |
| details | Describe the issue | Long Text | Y | — | shown | N | Free text, required |
| hr_section | HR | Section Break | — | — | hidden | N | HR-only section |
| hr_notes | Internal HR Notes | Small Text | — | — | hidden (permlevel: 1) | N | HR-only notes, never shown to employee |

### RISKS
- Conditional sections: `leave_type`, `balance_shown`, `balance_expected` are only shown if `issue_type = "Leave Balance Discrepancy"`, but they have no `reqd` flag on the doctype. The form does not enforce these as required even when shown. Submitting a Leave issue without filling leave fields may be accepted.
- Similarly, `affected_date`, `punch_affected`, `what_happened` are only shown for Check-in/Checkout issues but are not marked required. Employee can submit without filling them.
- `details` is required and always shown, so that's safe.
- **NEVER visible to employee**: `hr_notes` has permlevel: 1, which means it's invisible to Employee role on detail view. It won't render on existing issues.

### JARGON
- None identified; labels use plain language like "What are you reporting?" and "Describe the issue".

---

## Compensatory Leave Request

**No PWA Form**. Only shown in approver action sheet (requestSummaryFields.js, COMPENSATORY_LEAVE_REQUEST_FIELDS).

| fieldname | label | type | reqd? | default | PWA form | Approver sheet | Notes |
|---|---|---|---|---|---|---|---|
| employee | Employee | Link | Y | — | N/A | Y | Who is requesting |
| employee_name | Employee Name | Data | — | — | N/A | N | Fetched, display only |
| leave_type | Leave Type | Link | — | — | N/A | Y | Which leave type |
| leave_allocation | Leave Allocation | Link | — | — | N/A | N | Link to allocation, readonly |
| status | Status | Select | Y | Open | N/A | Y | Approval status |
| department | Department | Link | — | — | N/A | N | Fetched, readonly |
| work_from_date | Work From Date | Date | Y | — | N/A | Y | Holiday worked start date |
| work_end_date | Work End Date | Date | Y | — | N/A | Y | Holiday worked end date |
| half_day | Half Day | Check | — | 0 | N/A | Y | Is it a half-day comp leave |
| half_day_date | Half Day Date | Date | — | — | N/A | N | Which day (if half-day) |
| reason | Reason | Small Text | Y | — | N/A | Y | Why compensatory leave is requested |
| worked_on | Worked On Holiday | Section Break | — | — | N/A | N | Layout only |
| amended_from | Amended From | Link | — | — | N/A | N | Frappe amendment tracking |

### RISKS
- Employees cannot FILE Compensatory Leave Requests via the PWA; this form doesn't exist in the app. Only approvers see them in the request summary sheet.
- All required fields must be populated elsewhere (likely by backend or HR manager creation).

---

## Cross-Form Risks Summary

1. **Auto-filled required fields on new forms**: Most forms hide required fields from employees on creation, auto-filling them from the session or defaults:
   - `employee`, `employee_name`, `company`, `department` (on all forms)
   - These are shown (readonly) only when viewing existing records

2. **Conditional required fields**: Some fields become required based on checkboxes but depend on frontend validation:
   - `half_day_date` in Leave Application and Attendance Request
   - `in_time`/`out_time` pairing in Attendance Request
   - Leave/Attendance sections in Employee Issue

3. **Jargon in employee-facing labels**:
   - "From Employee" (should be "Employee")
   - "Expense Claim Type" (should be "Category" or "Type")
   - "On Duty" (unclear abbreviation)
   - "Punch-verified OT"
   - "Replacement Leave"
   - "Compensatory Leave Request" (complex compound term)

4. **Backend vs. PWA differences**:
   - OT Request: `explanation` is non-required on doctype but required by PWA
   - Expense Claim: `currency` is auto-filled to company currency, not employee.salary_currency (differs from doctype default)
   - Expense Claim: `exchange_rate` always 1.0, not fetched from actual rates

5. **Approver sheet depth**: The approver action sheet shows a subset of fields per doctype (defined in requestSummaryFields.js). Approvers see different data than employees see on forms.

