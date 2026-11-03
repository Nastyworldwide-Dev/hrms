# HANDOFF
prompt:   expense claim: multiple attachments, per line and for the whole claim (owner, 3 Nov 2026)
status:   done
commit:   alpha.80 on nz-glass (ef28d2759)
files:    frontend/src/components/ReceiptRow.vue
frontend/src/utils/lineReceipts.js
frontend/src/views/expense_claim/Form.vue
hrms/hr/doctype/expense_claim/expense_claim.py
hrms/hr/doctype/expense_claim_detail/expense_claim_detail.json
verify:   deploy WITH migrate; new claim -> line: add 2 files -> whole claim: add 1 -> send -> approver opens all 3
flags:    not tried on a real site; alpha.80 includes alpha.79 (second login email, laptop sidebar)
next:     Approva nightly login disable: owner fixing in the Approva repo
