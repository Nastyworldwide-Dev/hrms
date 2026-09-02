# HANDOFF
prompt:   Pass 5 — runtime reliability, PWA & performance closure
status:   primitives verified healthy; no defect/pathology found
commit:   73fd8095f on nz-glass (measurement/verification pass — no new code)
pwa/sw:   sw.js has cleanupOutdatedCaches + skipWaiting + clientsClaim (prompt
          update + old-cache purge); pre-paint theme = no FOUC on cold start;
          router.onError reloads once on a stale chunk after deploy (unit-tested,
          latched against loops). Safe, understandable update recovery.
network:  loudRequest surfaces failures as toasts and RETHROWS (onError/try-catch
          still run) — errors are never swallowed as empty states; ResourceError
          for resource failures.
realtime: socket.io reconnectionAttempts=5 (bounded, no storm); the only handler
          is hrms:refetch_resource which reloads an already-cached resource — a
          FRESHNESS optimization, NOT a correctness dependency. Absent socket =>
          data still loads on navigation. Degrades gracefully.
errors:   console CLEAN across home/attend/leaves/more (0 Nadi errors); 0 failed
          API (>=400). startTime/reportAllChanges = browser extension (prior).
idempotency: approval decide() uses a for_update row-lock + docstatus==1 no-op
          (runtime-proven prior); duplicate same-timestamp checkin blocked (prior).
performance(measured): Home = 35 API calls, 21KB total. The apparent duplicates
          are DISTINCT my/team/history queries (different approver_id/filters), all
          auto:true — eager tab pre-load, not redundant. Only genuinely-repeated
          calls are tiny (get_hr_settings x2). No large payload, no N+1, no slow
          load => no clear pathology; per guidance, no fix warranted.
concurrency: approval row-lock + checkin duplicate guard are race-safe (proven).
unverified/env-limited: full concurrent stress load, installed-PWA lifecycle on a
          real device, and live-instance realtime delivery (no live access).
verdict:  RUNTIME RELIABILITY CLOSED — SW update+recovery, graceful realtime,
          error surfacing, idempotency/duplicate guards, clean console/0-failures,
          and a measured-healthy perf profile; no reliability defect or pathology.
