# HANDOFF
prompt:   Norazlin 4 Sep / an ignored tap was a wall
status:   done
commit:   951af8d8a on nz-glass
files:    hrms/hr/doctype/shift_type/shift_type.py
          hrms/api/attendance_fix_day.py
          hrms/api/attendance_master_edit.py
          hrms/utils/attendance_recovery.py
          hrms/utils/attendance_day_audit.py
          hrms/utils/extension_custom_fields.py
          hrms/patches/v16_0/add_skipped_as_noise_field.py
          hrms/tests/test_an_ignored_tap_does_not_split_the_day.py
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_an_ignored_tap_does_not_split_the_day.py
flags:    new column Employee Checkin.skipped_as_noise - needs the migrate; until
          it exists every skipped punch simply stays a wall, which is the old
          behaviour. The patch backfills the taps Fix Day already ignored.
next:     deploy, then Rebuild this day on Norazlin 4 Sep - expect Present with
          real hours and claimable OT
