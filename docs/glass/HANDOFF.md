# HANDOFF
prompt:   Final production closure & reliability certification
status:   done — PRODUCTION READY WITH ACCEPTED NON-BLOCKING ITEMS
commit:   650a76ffd on nz-glass (26 fix/feat commits this branch)
verify:   bench migrate (test.local) -> clean, no errors, idempotent;
          ruff clean; 50/50 bench-free; offboarding-integration 2/2;
          D1 repair+manual-protection 2/2 (after fixture clean);
          both frontend builds OK; frontend 61/63 (2 pre-existing patch tests)
ledger:   every session fix reconciled — see certification report. All code
          fixes RESOLVED+VERIFIED. Deployment reflects HR leave-guard + all
          worker code after a normal worker reload.
non-block: (1) deploy must run the FULL process stack (socketio :9000,
          schedule, worker) — configured in Procfile, this preview ran only
          `bench serve`; app degrades gracefully without them (36/36 screens
          clean). (2) D1 HISTORICAL backfill (pre-fix skipped punches) =
          NEEDS BUSINESS DECISION — auto-repair rewrites historical Absent->
          Present and closed payroll; recommend a scoped HR review, not a blind
          migration. (3) provisioning (System User vs ESS) + (4) approval-
          confirmation UX = recorded business decisions. (5) 2 frontend
          failures are the frappe-ui call-error-handling patch test (env).
verdict:  PRODUCTION READY WITH ACCEPTED NON-BLOCKING ITEMS
next:     deploy via bench start/supervisor (runs socketio+scheduler+workers),
          then HR decides the D1 historical-scope review
