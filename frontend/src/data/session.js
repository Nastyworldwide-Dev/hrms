import { computed, reactive } from "vue"
import { createResource, call } from "frappe-ui"
import { userResource } from "./user"
import { employeeResource } from "./employee"
import router from "@/router"
import { announceSessionChange, clearPersonalCaches, markLoggingOut, sessionUser } from "@/utils/personalCache"
import { clearCachedPages } from "@/utils/cachedPages"
import { handBackPhone } from "@/utils/handBackPhone"

export { sessionUser }

async function handleLogin(response) {
	if (response.message === "Logged In") {
		announceSessionChange()
		// the last person's offline page copy (a session that only expired
		// never passed through logout)
		await clearCachedPages()
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
		await handleLogin(response)
		return response
	},
	otp: async (tmp_id, otp) => {
		const response = await call("login", { tmp_id, otp })
		await handleLogin(response)
		return response
	},
	logout: createResource({
		url: "logout",
		// BEFORE the request, and AWAITED: frappe-ui awaits `validate` but not `beforeSubmit`. Telling
		// the relay to stop sending this phone the leaving person's pushes needs their session, which
		// the logout call ends. It never returns a message, so it can never refuse the logout.
		async validate() {
			await handBackPhone(window.frappePushNotification)
			markLoggingOut()
		},
		async onSuccess() {
			announceSessionChange()
			await clearPersonalCaches(session.user)
			await clearCachedPages()
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
