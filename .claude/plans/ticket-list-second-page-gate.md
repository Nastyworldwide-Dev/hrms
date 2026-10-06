# Ticket: prove a list loads its SECOND page (infinite scroll), not only that the scroll handler is reached

DONE 6 Oct 2026: e2e/list-scroll.spec.js proves a real scroll reaches ListView's scroll handler (it failed with the old
camelCase-only listener). The test site's Leave list has 40 rows, under one page (page_length 50), so it cannot prove
that a SECOND page is requested and appended.

DO: seed more than one page of rows for the audit user (or lower page_length for the test), scroll to the bottom,
assert the next `get_list` request (start=50) goes out and the row count grows. Also note the wrapper in that spec
replaces HTMLElement.prototype.addEventListener for ion-content only; it breaks removeEventListener for those two
events inside the test page, which is harmless for a one-page test but should be a plain wrapper map if it grows.
