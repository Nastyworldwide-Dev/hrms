GOAL: anyone who can use Nadi can attach a file to their own request — no "Not
allowed via controller permission check".
DONE WHEN: the upload inserts the File as the server (staff hold no File create
right), asks only that the caller may READ the request, and asks once; the
person who uploaded a file may delete it.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/tests/test_nadi_attachments_do_not_need_desk_rights.py hrms/tests/test_get_attachments_reads_by_parent.py
