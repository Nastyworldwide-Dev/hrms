import { personalCacheKey, sessionEnded } from "@/utils/personalCache"
import { createResource } from "frappe-ui"

export const employeeResource = createResource({
	url: "hrms.api.get_current_employee_info",
	cache: personalCacheKey("hrms:employee"),
	onError(error) {
		if (error && error.exc_type === "AuthenticationError") {
			sessionEnded()
		}
	},
})
