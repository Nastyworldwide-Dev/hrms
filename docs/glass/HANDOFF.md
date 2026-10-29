# HANDOFF
prompt:   Excel upload renamed "Employee Cost Tag" so Data Import lists it under Employee (owner, 29 Oct 2026)
status:   done
commit:   alpha.73 on nz-glass (rename eff37f43d)
files:    hrms/hr/doctype/employee_cost_tag/employee_cost_tag.json
hrms/hr/doctype/employee_cost_tag/employee_cost_tag.py
hrms/tests/test_employee_cost_tag.py
hrms/hooks.py
verify:   deploy + bench migrate; Data Import -> Document Type, type "employee" -> Employee Cost Tag is listed
flags:    no bench here; office Wi-Fi works but location still fails for some staff -> suspect phone settings, not network
next:     owner checks the failing phone's Location settings (see chat)
