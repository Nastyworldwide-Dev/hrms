# TICKET — a relabelled punch reads as a type_mismatch on every import

Raised by review of e1f4165b7, 18 Sep 2026, and CHECKED: the feared outcome does
not happen. Recording the real, smaller one.

WHAT WAS FEARED: `checkin_import` keys a punch as (employee, time to the second,
log_type). The Fix Day rebuild now relabels a session tap, so the hub says OUT
where the source still says IN — the reviewer's worry was a duplicate insert or a
silent revert of the relabel.

WHAT ACTUALLY HAPPENS, read from the code:
* No duplicate. `drop_already_imported` matches on `source_key(instance,
  remote_name)` — the SOURCE record's name — so a punch already imported is
  dropped whatever its log_type now says.
* No revert. The importer inserts and never updates; its own docstring says so.
* What does happen: `diff_punches` classifies the pair as `type_mismatch`, so the
  punch is REFUSED with that reason on every subsequent import, for ever. HR's
  import report grows a permanent line about a day they already fixed.

WHY IT IS A TICKET AND NOT A FIX TODAY: it is noise, not corruption, and it is in
the sync path — which the owner has just had one bad experience with (18 Sep, a
pull reverting shift and location). Touching it again the same day, for a report
line, is the wrong trade.

WHAT TO DO: let `_local_punches` carry each punch's `source_checkin` key, and
have `diff_punches` count a local punch that already records THIS source punch as
matched, whatever its log_type. Then a relabelled day goes quiet.

TRIGGER: the next change in hrms/sync/checkin_import.py, or the first time HR
asks what the repeating type_mismatch line means.

# ceiling: a relabelled tap reports type_mismatch on every import
# upgrade: the next checkin_import change, or HR asking about the line
