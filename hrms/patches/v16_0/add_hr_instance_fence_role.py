from hrms.utils.company_fence import create_company_fence_roles


def execute():
	# "HR (Instance)" postdates the create_company_fence_roles patch; the
	# creator is idempotent, so re-running it just adds the missing role.
	create_company_fence_roles()
