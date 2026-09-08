import { personalCacheKey } from "@/utils/personalCache"
import { createResource } from "frappe-ui"

export const hrContactsResource = createResource({
	url: "hrms.api.hr_contacts.list_hr_contacts",
	cache: personalCacheKey("nsty:hr-contacts"),
	auto: false,
})

export const reportingManagerResource = createResource({
	url: "hrms.api.hr_contacts.get_reporting_manager",
	cache: personalCacheKey("nsty:reporting-manager"),
	auto: false,
})
