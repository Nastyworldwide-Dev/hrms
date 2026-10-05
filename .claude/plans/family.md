CLASS: a data repair that overwrites a value and keeps the old one only in a log nobody can read. The patch cut open OT claims to the half hour and logged "old -> new" through stdlib logging, which a bench does not write, and a column write leaves no Version row, so the original figure was gone (migration check of eb32c90c8).
hrms/patches/v16_0/band_open_ot_claims_to_half_hours.py same-root (fixed here: the old and new figure are written as a Comment on each cut claim, where HR reads it and can put it back; a second run adds none)
hrms/patches/v16_0/band_open_ot_claims_to_half_hours.py:filters same-root (fixed here: status "Open" only, so a draft saved in Desk as Approved or Rejected, which someone decided, is not cut)
hrms/patches/v16_0/ot_request_approved_on_and_payment.py not-affected — fills a blank column, overwrites nothing
hrms/patches/v16_0/verify_ot_hour_precision.py not-affected — verifies, writes nothing
hrms/api/approval.py:_record_rejection_reason not-affected — the same Comment pattern this fix reuses
