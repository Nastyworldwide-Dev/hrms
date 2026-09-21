TICKET: the list filters still offer the STORED pending word

Opened 21 Sep 2026 alongside ecc3b8d7b ("one waiting word").

What: request rows now say "Waiting" while pending, but the status filter on
two list screens still offers the stored word:
  frontend/src/views/leave/List.vue:35            ["Open", "Approved", "Rejected"]
  frontend/src/views/attendance/ShiftRequestList.vue:36  ["Draft", ...]
So a staff member filtering for "Open" gets rows labelled "Waiting", and on the
shift list the word offered is "Draft" — the one word the chip change was meant
to retire.

Why not fixed in that commit: the filter's option string is BOTH the label and
the value sent to the server (ListFiltersActionSheet.vue:58-63 passes
`filter.options` straight into FormField as a Select). Showing "Waiting" while
sending "Open" needs FormField's Select to take {label, value} pairs — a change
to a shared form component that every filter and every form field goes through.
That is its own slice with its own tests, not a drive-by in a chip commit.

Fix shape: teach FormField Select to accept {label, value}, then give the two
FILTER_CONFIGs the pending row as {label: "Waiting", value: <stored word>}.
Pin it with a test that the VALUE sent is still the stored word.

Blocked on nothing. Small, but touches a shared component.
