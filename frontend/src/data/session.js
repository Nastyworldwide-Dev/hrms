import { computed, reactive } from "vue"
import { createResource, call } from "frappe-ui"
import { userResource } from "./user"
import { employeeResource } from "./employee"
import router from "@/router"
import { announceSessionChange, clearPersonalCaches, sessionUser } from "@/utils/personalCache"

export { sessionUser }

function handleLogin(response) {
	if (response.message === "Logged In") {
		announceSessionChange()
		session.user = sessionUser()
		console.info("[session] logged in as", session.user, "— full reload")
		// FULL page load, not router.replace: module-scope auto resources
		// already fired (and were held by the guest gate) while this tab was
		// on the login page — only a fresh evaluation of the import graph
		// refetches them with the session cookie present. Mirrors what
		// logout always did with window.location.reload().
		window.location.replace("/hrms")
	}
}

export const session = reactive({
	login: async (email, password) => {
		const response = await call("login", { usr: email, pwd: password })
		handleLogin(response)
		return response
	},
	otp: async (tmp_id, otp) => {
		const response = await call("login", { tmp_id, otp })
		handleLogin(response)
		return response
	},
	logout: createResource({
		url: "logout",
		async onSuccess() {
			announceSessionChange()
			await clearPersonalCaches(session.user)
			userResource.reset()
			employeeResource.reset()

			session.user = sessionUser()
			router.replace({ name: "Login" })
			window.location.reload()
		},
	}),
	user: sessionUser(),
	isLoggedIn: computed(() => !!session.user),
})
