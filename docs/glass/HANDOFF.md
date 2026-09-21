# HANDOFF
prompt:   release-1 (audit 2026-09-21 → three-release plan)
status:   done
commit:   f940ba4d7 on nz-glass (26 commits from 4b9290e24; not pushed)
files:    docs/glass/release-1-notes.md
          docs/glass/audit-2026-09-21.md (+ audit/2026-09-21/A–G)
          .claude/plans/current-plan.md
          hrms/hr/doctype/shift_type/shift_type.py (one loader, open day, 20 h cut, sweep)
          hrms/utils/{attendance_recovery,day_remark,restamp,hot_indexes,holiday_access}.py
          hrms/api/{remote_checkin,attendance_fix_day,attendance_master_edit,approval}.py
          frontend/src/components/CheckInPanel.vue
verify:   bash /tmp/claude-1009/-home-nabil-nz-version-16/f6faadaf-fbf0-407c-92cb-48d5396bf104/scratchpad/run_files.sh hrms/tests/test_pairing_rule_table.py hrms/tests/test_day_evidence_is_read_one_way.py hrms/tests/test_restamp.py
flags:    RULINGS before deploy — payroll "consider unmarked attendance as" (open day = paid under default); restamp preview range. Migrate + worker restart needed.
next:     owner reads release-1-notes.md, rules on payroll, deploys; then Release 2 mockup (Correct form on the Check-in page).
