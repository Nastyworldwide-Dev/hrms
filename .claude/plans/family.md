# Family — fix(pwa): a pending tap id never outlives its calendar day (21 Sep 2026)
CLASS: a retry token scoped by time only — across local midnight a "retry" replays yesterday's punch and today gets none
Changed symbol: pendingTapId in frontend/src/components/CheckInPanel.vue (adds `day` to the kept id; reuse requires same action, same local day, inside the TTL).
frontend/src/components/CheckInPanel.vue:submitLog same-root — the one caller
hrms/api/remote_checkin.py:punch not-affected — server replay semantics unchanged; a new id is a new tap as before
