import { createResource } from "frappe-ui"

export const hrContactsResource = createResource({
	url: "nsty.api.hr_contacts.list_hr_contacts",
	cache: "nsty:hr-contacts",
	auto: false,
})

export const reportingManagerResource = createResource({
	url: "nsty.api.hr_contacts.get_reporting_manager",
	cache: "nsty:reporting-manager",
	auto: false,
})
