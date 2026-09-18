GOAL: the approver can see the check-in photo again — Remote Approvals showed a
broken image because a PUBLIC File on S3 is addressed as the bucket object, and
the bucket does not serve objects to the public.
DONE WHEN: new selfies are stored private and attached to their punch (so
File.is_downloadable grants everyone with read on that Employee Checkin), and a
patch repairs the ones already taken — private, attached, and readdressed from
the bucket url to the generate_file api url where they were on S3.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/tests/test_selfie_is_private_and_attached.py hrms/api/test_remote_checkin.py
