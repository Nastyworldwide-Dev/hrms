import { createResource } from "frappe-ui"

const companyCurrency = createResource({
	url: "hrms.api.get_company_currencies",
	auto: true,
})

export function getCompanyCurrency(company) {
	return companyCurrency?.data?.[company]?.[0]
}
