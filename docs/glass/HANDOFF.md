# HANDOFF
prompt:   Track B — glass transformation gaps, closed with instruments
status:   done - 9 commits, all 8 gates MEASURED on one build, 7 straight green,
          visual green on rerun (one recorded flake)
commit:   8e8e629e6 on nz-glass
files:    glass-components.css (opacity invariant, header, dropdown skin)
          GPage/App (field per page), router (focus release)
          Notifications.vue (3 states), 3 doctype json + 2 forms (status display)
          patches/frappe-ui (Popover guard), design/baselines (64 re-shot)
verify:   set -a; . .env; set +a; node design/gates/run.mjs   -> no SKIP
flags:    the AUDIT_PW route works from this repo — the gates were never
          actually blocked, only uncredentialed. shift-requests-new-1440-dark
          flaked once; if again, re-measure noise floor, do not raise the cap.
          Field/modal consolidation (14 non-Glass inputs, 9 ion-modal) is the
          measured remainder; Ionic motion is the out-of-scope-ruling to revisit.
next:     deploy (build only — no migrate needed beyond the earlier batch),
          then the user re-tests the five screenshot findings on a phone.
