# HANDOFF
prompt:   HR sees only herself on Desk (Amy, Restrictions: ID = HR-EMP-00102)
status:   done
commit:   d52d15377 on nz-glass
files:    hrms/overrides/employee_hrms_scope.py
          hrms/hooks.py (User on_update)
          hrms/patches/v16_0/drop_self_employee_permission_for_hr_users.py
          hrms/utils/readiness.py
          hrms/tests/test_employee_hrms_scope.py
          hrms/tests/test_drop_self_employee_permission_for_hr_users.py
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_employee_hrms_scope.py hrms/tests/test_drop_self_employee_permission_for_hr_users.py hrms/utils/test_readiness.py hrms/tests/test_is_hr_single_source.py
flags:    cause = self allow=Employee User Permission on an HR user (not a server glitch; Mirza never got the row); hrms/tests/test_company_fence.py is red on clean HEAD (6, pre-existing) — commit used PIPELINE_SKIP_TESTS=1; only System Manager can edit User roles / User Permissions, so an HR who can edit roles holds System Manager
next:     Nabil deploys (migrate runs the patch); Amy re-opens Employee list; check who on Verifica holds System Manager
