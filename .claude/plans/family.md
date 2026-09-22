CLASS: a REFUSAL read as an ABSENCE. A producer that answers "here is the
answer, or here is why there is none" is consumed as "here is the answer, or
nothing is known" — and the consumer then falls back to a guess on exactly the
inputs the producer refused. The refusal carries the information the fallback
needed; dropping it turns the most-broken case into the least-informed one.

INSTANCE: `day_plan` suggests a pair only when it can READ the day. The dialog's
`fresh_state` read "no suggestion" as "nothing known" and pre-ticked every
counted punch — on a day the planner had explicitly refused. Four ticks are
never 1 IN + 1 OUT, so the dialog refused its own opening state and Save &
rebuild was dead. The only days HR opens this screen for are the refused ones.

CALL SITES of what changed (`_suggested_roles`, `_screen`, `fresh_state`):

 hrms/api/attendance_fix_day.py:_screen        same-root — now also asks
   `suggestion_refusal` when there is no pair, and ships it as
   `suggestion_refusal` on the screen payload.
 hrms/public/js/fix_day.bundle.js:fresh_state  same-root — an unreadable day
   pre-ticks NOTHING; the two "no suggestion" cases are now distinguished.
 hrms/public/js/fix_day.bundle.js:render_summary  same-root — shows the
   planner's own sentence, so HR reads why nothing is ticked.
 hrms/public/js/fix_day.bundle.js:tap_html     same-root (second defect) — a
   punch of this shift-day landing the NEXT calendar morning now carries its
   date, so 07:38 (19 Aug) is not read as a twin of 07:39 (18 Aug).
 hrms/public/dist/js/fix_day.bundle.*.js       not-affected — build output,
   gitignored, regenerated on deploy from the source above.

No other consumer of `day_plan` drops its refusal: `plan_day` and `rebuild_day`
both return/raise it. Verified by grep for `_suggested_roles|fresh_state|
suggestion_refusal` across hrms/ — no call sites outside the two changed files.

LOCKING THE CLASS:
 regression (the instance): hrms/tests/test_fix_day_unreadable_day.py
   TheEngineCannotReadThisDay — Adam's 18 Aug really is refused by the planner.
 invariant (the class): same file, TheScreenSaysSoInsteadOfGuessing —
   a refused day reports the planner's OWN sentence (not a second wording),
   and a readable day reports none. Plus three source-asserted tests in
   hrms/public/js/fix_day.bundle.test.js pinning that the dialog reads the
   refusal rather than inferring it from an empty suggestion.
