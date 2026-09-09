# Claims in the PWA — expense, overtime, replacement leave: what was broken, what is fixed, what needs a ruling

9 September 2026, evening. `nz-glass` after `d2cc3dd10`. Nabil: "Cant pull new GL
type for expense claim from ERP … HR need to modify for PWA claim expense type …
NOT ONLY OT CLAIM, EVERY TYPE OF CLAIM … ensuring it is working in PWA."

Evidence labels: **code** (file:function on HEAD), **live** (reproduced on the
dev site fresh.local today, as Administrator or as the audit employee through
the PWA endpoints), **trace** (the two read-only traces this evening), **live:
unknown** (only Verifica can answer).

---

## 1. Expense claims

### 1.1 The GL account problem, root to leaf

| Step | Fact | Evidence |
|---|---|---|
| Companies on Verifica are shells | Built by "Pull Companies" with ERPNext's generic **Standard** chart; the source ERP's real GL accounts never cross (Account is not mirrored). | code: `hrms/sync/company_shells.py SHELL_DEFAULTS`; `hrms/sync/runner.py` has no Account |
| An Expense Claim Type needs an account per company | `Expense Claim Account.default_account` is mandatory; the picker filters `root_type` Expense/Asset for that company. | code: `expense_claim_account.json`, `expense_claim_type.js` |
| HR could not pick the ERP's account | The hub only holds the Standard chart under that company. | = "can't pull new GL type from ERP" |
| A type without a row is a trap | The PWA offered every type; save threw "Set the default account for the Expense Claim Type …" after the whole form was filled. | **live**: reproduced, `HR-EXP` insert refused for type Medical |
| A saved claim died at approval | `payable_account` stayed empty (shells have no `default_expense_claim_payable_account`; ERPNext only sets `default_payable_account`); the approver's submit posted GL and threw **"Account is required"**. | **live**: draft saved, submit failed with that message |

### 1.2 Fixed today

| Commit | What |
|---|---|
| `bb07bd2b1` | **Pull → GL Accounts from Source** on the HRMS ERP Instance form: reads the source's Expense and Asset accounts for the served companies, creates the missing ones here through the normal insert, parents first; a parent the hub lacks is replaced by the hub's root group and reported. HR then picks the ERP's own account on the Expense Claim Type. The form's eleven buttons became three groups (Pull / Checks / Danger). |
| `e33e70fad` | The PWA offers only the types that have an account for the employee's company. **live**: audit employee now sees `Medical` only. |
| `d2cc3dd10` | `payable_account` defaults server-side to the company's expense-claim payable, else its ordinary payable (Creditors). **live**: the same claim now submits (`Unpaid`, payable `Creditors - _TC`). |
| `<minors>` | Second pull run recognises accounts under their local name; log level; labels. |

### 1.3 Still open on expense

| # | Finding | Evidence | Action |
|---|---|---|---|
| E-PWA3 | A **new** form never arms the "unsaved changes" confirm; Back discards silently. | trace: `FormView.vue` watcher returns on `!props.id` | fix in flight (frontend worker) |
| E-approver | The audit employee has no expense approver and `is_mandatory=1`: the form cannot be submitted until HR sets Employee.expense_approver or a Department approver. | **live** on the dev site; **live: unknown** on Verifica | HR config; readiness should name it |
| E-taxes | Taxes tab shows `account_head` (required Link to Account). On the dev site the employee can search accounts; on Verifica **live: unknown** (Employee has no Account read in the shipped JSON). | **live** (dev) | verify once on Verifica as a staff user |
| E-dead | `ExpenseAdvancesTable.vue`, `get_salary_currency`, the `from_date/to_date` branch in `ExpenseClaimItem.vue` are dead code. | trace | delete in a chore |

---

## 2. Overtime claims (OT Request) and replacement leave

### 2.1 How it works today (trace)

Employee: Attendance dashboard card "Overtime to claim" → OT Request form (date, hours, explanation; compensation forced from `Employee.eligible_for_overtime_pay`) → save (draft) → approver notified → approver decides in the Requests panel or from the notification → `decide` submits. Approved + Replacement Leave grants leave days at once (per-day ratio, half-day steps). The old **Replacement Leave Claim** (a monthly bank) was hard-zeroed when that per-day grant landed; its screens, card and route are still wired.

### 2.2 Defects found, and their status

| # | Defect | Effect on staff | Status |
|---|---|---|---|
| D1 | OT Request History list has no row component registered → blank rows | "my OT list is empty" | fix in flight |
| D2 | A rejected request shows **Approved** (chip reads docstatus only; API omits `status`) | wrong outcome shown to employee and manager | fix in flight (both halves) |
| D3 | No outcome notification for OT Request; none at all for RL Claim; the Reject dialog promises one | silence after filing = "back and forth" | fix in flight |
| D6 | RL discovery reads `Attendance.ot_hours`; the form and the save use the check-in scan → "nothing to claim" after tapping an offered day | the exact ping-pong reported | fix in flight |
| D7 | RL claim form hardcodes 8 h per day | wrong refusals when HR sets 6 h | fix in flight |
| D9 | Cancel from the detail form uses `set_value` → silently fails on a submitted request | "cancel does nothing" | fix in flight |
| D10 | Approver's review sheet omits the mandatory Explanation | approver decides blind | fix in flight |
| D13 | `company` never set from the Employee (user default instead) | multi-company fence trips | fix in flight |
| D4/D5/D8 | Replacement Leave Claim is a dead end (bank always 0); its own test suite contradicts the OT one; card reads a key the API does not return | screens that can only refuse | **ruling needed** (§3 Q1) |
| D11 | No rejection reason anywhere | employee re-files blind | small schema change — **word needed** |
| D12 | After a decision the employee has no action; a rejected date stays reserved | "I can't claim that day again" | **ruling needed** (§3 Q2) |
| D14 | Overtime Slip and OT Request are two unconnected pay paths | double pay if both enabled | guard or document — **ruling** (§3 Q4) |
| D15 | Stale comments ("no decision field") | misleads the next fix | cleaned where touched |

### 2.3 Dev-site state for verification (live)

No Overtime Type, no attendance with OT hours, no expense approver on the dev site: the OT flow can be verified there only after seeding a shift with overtime enabled, punches and an approver. The bench-free suites cover the rules; the PWA build and the endpoint contracts were exercised as the audit employee (`get_claimable_ot_summary`, `get_ot_claim_summary`, `get_replacement_leave_bank_summary`, `get_doctype_fields` for all three doctypes answer with the expected shapes).

---

## 3. Rulings Nabil / HR must give (nothing here is guessed in code)

| Q | Question | Default if no answer |
|---|---|---|
| Q1 | **Replacement Leave Claim**: retire the monthly-bank claim (route, card, screens) now that RL is granted per day on OT approval? | retire the surfaces; keep the doctype for history |
| Q2 | **Rejected OT date**: does a rejection release the date for re-filing, or is the day spent until HR cancels? | release (exclude Rejected from the duplicate guard and from the claimed-date set) |
| Q3 | **RL cap**: are Replacement Leave claims capped (daily / monthly / 30-minute bands) like OT Pay, or raw hours as today? | raw hours (current code) |
| Q4 | **Overtime Slip**: is the upstream Overtime Slip path used anywhere? If not, guard it off. | guard off |
| Q5 | **Four-month backdating** (still open from 8 Sep) | two payroll cycles (current code) |
| Q6 | **Rejection reason field** on OT Request / RL Claim (small schema change) | add `decision_remark` |

---

## 4. Verifica checklist after deploy

1. HRMS ERP Instance → **Pull → GL Accounts from Source** (preview first). Then open each Expense Claim Type and add the ERP account per company.
2. Company → check `Default Expense Claim Payable Account`; if empty, the code now uses the ordinary payable (Creditors). Set it explicitly if finance wants a separate account.
3. Employee → `Expense Approver` (or Department expense approvers) for everyone who files claims.
4. As a staff user in the PWA: New Expense Claim → the type list shows only configured types → save → approver approves → claim reads Unpaid (submitted). Taxes tab: does the Account picker answer?
5. OT: file one OT Request, reject it, confirm the list says Rejected and the employee gets the notification.
