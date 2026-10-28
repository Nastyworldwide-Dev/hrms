CLASS: a whitelist decorator sliding onto a neighbouring function; a GET that may write through identity resolution
hrms/api/org_chart.py photo same-root — own_employees (read-only) instead of get_employee; module-wide endpoint-set test
hrms/api/profile_photo.py set_photo not-affected — POST, and require_employee is meant to resolve there; covered by the endpoint-set test
hrms/patches/v16_0/repair_public_selfies.py:50 not-affected — a log line mentioning 'photo'; the patch never calls photo
