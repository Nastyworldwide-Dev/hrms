"""Create the company fence roles on existing sites (v16).

"HR (Company)" and "HR Manager (Group)" split the single "HR" audience once one
site serves 15 companies. Fresh installs get them from
`hrms.setup.after_install` — `install_app` passes `set_as_patched=True`, so a
patch alone would never run there. This patch is the existing-site half.

Creating the roles changes nothing on its own: they carry no DocPerm rows and
nobody holds them until an administrator assigns one. The fence only starts
acting when a user holds "HR (Company)" and their Employee is saved, at which
point `hrms.overrides.employee_hrms_scope` provisions the `allow=Company` User
Permission. Idempotent — safe to re-run.
"""

import logging

from hrms.utils.company_fence import create_company_fence_roles

logger = logging.getLogger(__name__)


def execute():
	created = create_company_fence_roles()
	logger.info("[company_fence] patch done — created %s", created or "nothing (already present)")
