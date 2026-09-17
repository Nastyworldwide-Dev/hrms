# HANDOFF
prompt:   selfie PermissionError + attendance editing questions
status:   done
commit:   c1438f2b1 on nz-glass (f3774c15f, bfe749214, c5e7ba53e)
files:    hrms/api/remote_checkin.py
          frontend/src/components/CheckInPanel.vue
          hrms/tests/test_selfie_upload_survives_a_public_file_lockdown.py
          .claude/plans/family.md
          .claude/plans/ticket-remote-checkin-refactor.md
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_selfie_upload_survives_a_public_file_lockdown.py
flags:    upload_selfie inserts the File with ignore_permissions, so the punch
          photo is an exception to the site's "only System Managers may upload
          public files" setting — owner ruling wanted. Danial's 3/4 Sep
          off-shift OUT needs no code: the endgame repair heals it on deploy.
next:     Nabil deploys nz-glass; then rule on the Shift Attendance master edit.
