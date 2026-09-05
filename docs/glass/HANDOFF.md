# HANDOFF
prompt:   #1 prove live writes are clean (post-cutover, mirrored writes unlocked)
status:   done — RL + check-in paths proven clean under the manual-sync workflow
commit:   8963f6200 on nz-glass
files:    hrms/hr/utils.py — ponytail note on grant_replacement_leave (why top-up,
            re-pull caveat). No behavior change.
verify:   python3 hrms/hr/test_utils.py  (8/8)
finding:  Every hub write to a MIRRORED doctype (Leave Allocation via RL grant,
          approvals on Leave Application/Shift Request/Attendance Request) survives
          only while no FULL re-pull of that doctype runs. check-in->attendance is
          already safe (checkin_sweeper excludes mirrored rows).
rule:     OPERATIONAL GUARDRAIL — before any full re-pull of a LIVE doctype post-
          cutover, release the mirrored stamps first (hrms.sync.purge.
          release_instance_stamp) or the pull clobbers hub edits. plan_cross_instance_write
          overwrites a NULL-stamp row, so releasing = source can reclaim; that is the
          intended direction only when the source is authoritative, which it no longer is.
          #2 DONE (97c940ff5): partial RL reversal now stamps the un-reversed days
          onto the allocation timeline as a Comment (queryable for HR reconciliation).
          #3 DONE (afd127942): approval Desk<->Python parity guard had a dead path
          (never ran); fixed, lists confirmed in agreement.
          #4 DONE (f082ad116 fix + 46593c343 test): the 3 red frontend tests were 1
          real PWA bug (call() threw SyntaxError/TypeError on malformed/non-JSON
          server errors -> now guarded, patched into frappe-ui) + 1 stale test
          (raw handler count vs the deliberate reconnect handler). Suite 135/135.
flags:    Reverted a speculative "create hub-native RL allocation" fix — it froze OT
          approval on the overlap guard. Top-up is correct under this workflow.
next:     none pending. Full plan (#1-#4) complete.
