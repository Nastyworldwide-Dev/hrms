# HANDOFF
prompt:   appraisal template not mandatory, on Appraisal and Appraisal Cycle (owner, 3 Nov 2026)
status:   done
commit:   alpha.81 on nz-glass (d3c0099e6)
files:    hrms/hr/doctype/appraisal/appraisal.json
hrms/hr/doctype/appraisal_cycle/appraisal_cycle.py
hrms/hr/doctype/employee_performance_feedback/employee_performance_feedback.py
hrms/tests/test_appraisal_template_is_optional.py
verify:   deploy WITH migrate; Desk -> Ilhan's appraisal -> clear template -> Save; cycle -> Create Appraisals with one employee lacking a template
flags:    bench appraisal suites not run here (no local site with hrms); empty-template appraisals start with no goals
next:     calendar day sheet (mockup-calendar-day-sheet-v2.html) waits on "build it"
