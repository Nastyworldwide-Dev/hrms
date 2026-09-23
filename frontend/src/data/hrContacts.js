import { personalCacheKey } from "@/utils/personalCache"
import { createResource } from "frappe-ui"

export const hrContactsResource = createResource({
	url: "hrms.api.hr_contacts.list_hr_contacts",
	cache: personalCacheKey("nsty:hr-contacts"),
	auto: false,
})

