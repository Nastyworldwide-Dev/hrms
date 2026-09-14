# HANDOFF
prompt:   HR bug sweep 14 Sep (cancel rule, OT hours/claims, Desk links, ERP punch import, stuck check-outs)
status:   done
commit:   bc7a13c0e on nz-glass
files:    hrms/utils/approved_request_guard.py
          hrms/api/correction_cancel.py
          hrms/sync/checkin_import.py
          hrms/utils/offshift_punch_heal.py
          hrms/utils/dry_run.py
          frontend/src/views/ot/OTRequestForm.vue
          hrms/patches/v16_0/ (4 patches: source_checkin field, HR User cancel, Desk links, HR Manager read)
verify:   bench --site <site> execute hrms.sync.missing_checkins.report --kwargs '{"from_date":"2026-09-01","to_date":"2026-09-14"}'
flags:    old gaps (Danial 3-4 Sep, Ria 9 Sep) NOT repaired — dry runs await Nabil; unmapped hub-native staff' ERP punches never imported; same-second phone+ERP punch can still double
next:     Nabil deploys on Frappe Cloud; then review dry runs before any repair
