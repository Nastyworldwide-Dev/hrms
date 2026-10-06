# alpha.37 clarify record (6 Oct 2026)
Owner: "go, yes to P1 and T1". B1, B2, B3, R1 approved; P1 (pipeline commit-scope) and T1 (fresh.local test
accounts only) approved.
- T1 touches fresh.local only (/home/nabil/verify-bench), never a live site. Password goes to the gitignored
  .env, never into the repo or a log.
- B1 fixes the shared component; the visual gate must show no change.
BLOCKERS: 0
