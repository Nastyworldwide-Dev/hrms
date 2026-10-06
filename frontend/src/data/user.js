import { personalCacheKey, sessionEnded } from "@/utils/personalCache"
import { createResource } from "frappe-ui"

export const userResource = createResource({
	url: "hrms.api.get_current_user_info",
	cache: personalCacheKey("hrms:user"),
	onError(error) {
		if (error && error.exc_type === "AuthenticationError") {
			sessionEnded()
		}
	},
})
