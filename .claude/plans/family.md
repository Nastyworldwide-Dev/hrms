CLASS: a count and the list under it built from two different sets. 55b190300 made the request chips count every type approval decides, which added Compensatory Leave Request; but the Requests panel has no list or screen for that type, so "All" would read higher than the rows a person can open (review of 55b190300). The chips must count what the panel lists.
hrms/api/request_counts.py:LISTED_TYPES same-root (fixed here: the counted types are the panel's types; the decision field of each still comes from approval.DECIDE_THEN_SUBMIT)
frontend/src/data/requestLists.js:REQUEST_LISTS same-root — the panel's list; a test now reads this file and fails when the two differ
frontend/src/utils/requestStatus.js not-affected — status words per type, not counts
hrms/api/approval.py:DECIDE_THEN_SUBMIT not-affected — decides Compensatory Leave Request on the Approvals page, which is a separate screen
