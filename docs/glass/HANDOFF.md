# HANDOFF
prompt:   alpha.41 Clean Glass + HR cross-company approver
status:   done
commit:   6feb489e8 on nz-glass (tag v2.0.0-alpha.41)
files:    hrms/hr/utils.py (approval walk ignores company)
          hrms/api/approval.py, hrms/api/remote_checkin.py
          hrms/overrides/{approval,ot,employee_owned}_row_scope.py
          hrms/patches/v16_0/approver_reads_past_company_user_permissions.py
          hrms/hr/doctype/expense_claim/expense_claim.py
          frontend/src (S1-S12 UI fixes, 3 refactors)
verify:   run migrate on the live site; Amran (TNME) opens Approvals and sees his other-company reports
flags:    served gates visual/coherence/ios red from before alpha.41 (ticket-served-gates-stale.md); S12 items 4-5 skipped
next:     re-baseline visual + fix 2 coherence + 1 ios finding before alpha.42
