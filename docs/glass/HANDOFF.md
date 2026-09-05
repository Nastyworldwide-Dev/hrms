# HANDOFF
prompt:   RL cancel no longer freezes when a grant is reversed to zero
status:   done, reviewed (frappe-reviewer + verifier CONFIRMED), pushed
commit:   a988d6e1b on nz-glass
files:    hrms/hr/utils.py — reverse_replacement_leave: no validate() on reduce,
            clamp to untaken (_reversible_days); grant path unchanged
          hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py —
            on_cancel routes through shared reverse (dup bug gone)
          hrms/hr/test_utils.py — 8 bench-free tests (clamp math + no-validate guard)
verify:   python3 hrms/hr/test_utils.py  (8/8, no bench needed)
          Smoke: RL 4h day -> approve -> cancel -> cancels clean (no freeze), ½ day removed.
          Consumed case: take the leave -> cancel -> cancels with HR warning, day stays.
flags:    First fix (c93df286f, unpushed) cited wrong throw (LessAllocationError);
          real freeze is set_total_leaves_allocated "mandatory" throw on zero-out.
          Squashed into a988d6e1b. RL leave type is neither earned nor compensatory.
next:     deploy; next candidates: config-gap surfacing, or cutover (unlock mirrored writes).
