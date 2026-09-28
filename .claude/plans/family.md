CLASS: a new Employee field meant to be set only by HR on this site — exposed to self-service writes at level 0, and to being overwritten by the mirror pull
hrms/setup.py:multi_site_checkin same-root — permlevel 1 (HR User / HR Manager write; Employee Self Service had level-0 write on Employee)
hrms/setup.py:other_checkin_sites same-root — permlevel 1
hrms/sync/runner.py:LOCALLY_OWNED_FIELDS same-root — the pull drops both fields from every Employee payload
hrms/setup.py:eligible_for_overtime_pay not-affected — already permlevel 1
