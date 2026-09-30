# HANDOFF
prompt:   Approva User role (special case, existing roles keep Approva)
status:   done
commit:   699adbb7f on nz-glass (tag v2.0.0-alpha.24)
files:    hrms/api/app_links.py
          hrms/patches/v16_0/add_approva_user_role.py
          hrms/patches.txt
          hrms/api/test_app_links.py
verify:   Desk User -> Roles -> tick Approva User -> that person sees Approva in Nadi
flags:    approving inside Approva still needs Approva's Reporting Manager role or being the named approver
next:     alpha.25 larger text; ticket .claude/plans/ticket-one-my-team-rule.md
