GOAL: Fix attendance must stay usable on a day the engine cannot read — the only
kind of day HR opens it for. Today the dialog pre-ticks EVERY counted punch, which
is never a valid 1-IN/1-OUT set, so Save & rebuild is dead and nothing is deleted,
rebuilt or re-shifted.

DONE WHEN:
 1. day_plan refusing (no suggested pair) -> the dialog pre-ticks NOTHING and shows
    the engine's own refusal sentence, instead of pre-ticking every counted punch.
 2. A punch belonging to the shift-day but landing on the NEXT calendar morning is
    shown with its date, so 07:38 (19 Aug) is not misread as a twin of 07:39.
 3. Both proved by tests that are RED on HEAD.

CHECK:
 PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fix_day_unreadable_day.py
 node --test hrms/public/js/fix_day.bundle.test.js
