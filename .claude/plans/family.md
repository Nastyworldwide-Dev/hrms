CLASS: a Desk-permission shortcut that staff pass, because Employee is an org-wide directory in Desk
hrms/api/org_chart.py photo same-root — the shortcut is for callers with no Employee only; staff always meet the company fence
hrms/api/org_chart.py get_node not-affected — never consulted has_permission; its fence is _fence on the caller's company
hrms/patches/v16_0/repair_public_selfies.py:50 not-affected — a log line mentioning 'photo'; the patch never calls photo
