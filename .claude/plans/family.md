CLASS: an owner ruling (claimed hours = verified hours, read-only) undone by a later refactor with no test pinning it
frontend/src/views/ot/OTRequestForm.vue claimed_hours same-root — fixed: read_only on new claims, test pins it
hrms/hr/doctype/ot_request/ot_request.py validate_claimed_hours not-affected — server cap check stays as the guard
