GOAL: an "Approva User" role that shows Approva in Nadi and grants nothing else; existing roles keep Approva.
DONE WHEN: role created by patch (idempotent); get_my_apps offers approva for it; the five existing roles still get it; red then green; fresh.local add/remove shows and hides the link.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/api/test_app_links.py
