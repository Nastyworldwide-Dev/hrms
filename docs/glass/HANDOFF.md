# HANDOFF
prompt:   HR: Letters Issued child table on Employee (7 Nov 2026)
status:   partial
commit:   95f5ae936 (alpha.85, tag v2.0.0-alpha.85) on sepia-tricorne; feat 09f570b3d, fix f3a3a896c
files:    hrms/utils/employee_letters.py
hrms/hr/doctype/hr_letter_type/
hrms/hr/doctype/employee_letter_issued/
hrms/patches/v16_0/add_employee_letters_issued.py
hrms/setup.py, hrms/hooks.py, hrms/patches.txt
hrms/tests/test_employee_letters.py
verify:   deploy WITH migrate; Employee -> "Letters Issued" under Cost Tag/Center; HR Letter Type has 16 rows
flags:    permlevel 1 per owner, so HR User sees letters too; fixtures -> setup.py+patch; not migrated (no bench here)
next:     migrate on Verifica, then open an Employee as HR Manager and as staff to confirm visibility
