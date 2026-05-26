"""nsty.api — whitelisted JSON-RPC endpoints exposed to the SPA.

Submodules:
    geofence        Pre-flight check-in geofence evaluation.
    remote_checkin  Approve / reject / submit remote checkin requests + late checkouts.
    hr_contacts     HR directory lookups for the Profile screen.

This file intentionally carries a docstring so the package marker
survives any deploy/sync tooling that strips zero-byte files. Frappe
Cloud has been observed dropping a previous empty __init__.py, which
manifests as "ModuleNotFoundError: No module named 'nsty.api.geofence';
'nsty.api' is not a package" at runtime.
"""
