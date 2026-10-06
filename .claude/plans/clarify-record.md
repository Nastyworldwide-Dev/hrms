# alpha.38 clarify record (6 Oct 2026)
Owner: "all as recommended, no push on pipeline works. the rest as normal".
R1 block exact duplicate expense claims (same employee + expense type + expense date + amount, not
   Cancelled/Rejected), warn on near ones (same employee + date + type, different amount).
R2 approver away: after 2 working days a waiting request moves to the next level of the line; both told.
R3 cancel after approval: approver and HR are told; balance/attendance reverse as today.
R4 offline submit: "Not sent: you are offline. Your form is kept." No queue.
R5 reports: probe approver roles' reports on real rows (rolled back), fix leaks.
R6 pipeline hooks: move the 25 /opt/keel links to humanless-pipeline one at a time with tests; LOCAL ONLY.
Push: app branch + tag + GitHub Release as normal (scripts/release.sh). Pipeline repo: never pushed.
BLOCKERS: 0
- 6 Oct (later): H1 put ON HOLD by the orchestrator (keel and humanless-pipeline diverged; re-link would drop work). Scope only narrowed; owner asked to choose the source of truth.
- 6 Oct: owner "yes to all": near-copy warning shown in Nadi; cancel-to-edit keeps the notice; /opt/keel is the pipeline source of truth (port pipeline-only fixes into it, local only). New ask: SOPs work and are visible to everyone the way HR uses them / configures them.
- 6 Oct (later): owner chose option 1 for K1: humanless-pipeline is the pipeline source of truth (reverses "keel is source of truth"; that ruling rested on a wrong count of which copy runs). Port /opt/keel-only behaviour INTO humanless-pipeline one at a time with tests, local only; then register each hook once. The settings.json change is shown to the owner before it is made.
- 6 Oct (later): owner STOPPED K1: "keel isnt ours to modify or push or merge. so we just focus on this nadi." K1 is cancelled. Nothing in /opt/keel or ~/.claude changed by K1; work sat on local branch k1/consolidate in ~/hp-k1 (4 commits, unpushed).
