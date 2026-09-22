# TICKET — G13 is the one guard with no test

Raised 22 Sep 2026, verifying the Fix Attendance plan against the code.

`.claude/plans/fix-attendance-plan.md` lists fifteen guards, "each = one test".
Fourteen are referenced in the module, the bundle or the suites. G13 is not
referenced anywhere in hrms/:

  G13  nightly/hourly recompute the same answer from the same punches
       (invariant test)

WHY IT MATTERS: G13 is the only guard about the system AGREEING WITH ITSELF
over time. Every other guard checks one save. G13 checks that the nightly pass
does not quietly produce a different day from the same punches a Fix Attendance
save just wrote — which is the shape of the attendance incident recorded in
memory (a sync rewriting mirrored rows), and the shape HR would report as
"I fixed it and it came back wrong".

It is also the guard a green suite is least likely to catch the absence of:
every other guard fails loudly at save time.

WHAT THE TEST WOULD BE: fix a day through save_day, run the nightly recompute
over the same window, assert the Attendance row is byte-identical — status,
hours, in/out, shift. Red today would mean the two paths already disagree.

NOT DONE HERE because it needs a real-DB fixture (the opt-in env-var suite),
not the stubbed pytest path, and that is a slice of its own.
