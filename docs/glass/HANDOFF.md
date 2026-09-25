# HANDOFF
prompt:   alpha.10 — midnight check-out, after-shift OT, own approver, kit sheets, frame, version
status:   done
commit:   see git log nz-glass (7361f0142 release + baselines)
files:    hrms/api/remote_checkin.py, hrms/utils/callback_session.py, hrms/hr/utils.py
          frontend/src/utils/checkinSession.js, noOverscroll.js, CheckInPanel.vue
          frontend/src/components/RemoteCheckinDialog.vue (+5 kit rebuilds)
          hrms/hr/report/missed_checkouts_after_midnight
verify:   set -a && . ./.env && set +a && node design/gates/ios.mjs  (all four audits 0)
flags:    damaged midnight days are listed for HR, never auto-fixed; after-shift OT since 16 Sep counts once on deploy
next:     deploy nz-glass; HR opens "Missed Check-outs After Midnight" and fixes each with Fix a day
