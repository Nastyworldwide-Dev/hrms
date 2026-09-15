<template>
	<GPage>
		<ion-content class="ion-padding">
			<div class="flex min-h-full w-full flex-col justify-center">
				<GModal :is-open="showDialog" :title="__('Login failed')" @did-dismiss="onDismissed">
					<p class="g-confirm__body">{{ reason }}</p>
					<GButton :label="__('Go to Login')" @click="() => session.logout.submit()" />
				</GModal>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import GButton from "@/components/glass/GButton.vue"
import GModal from "@/components/glass/GModal.vue"
import GPage from "@/components/glass/GPage.vue"
import { IonContent, onIonViewWillLeave } from "@ionic/vue"
import { computed, inject, ref } from "vue"
import { createResource } from "frappe-ui"
import { useRouter } from "vue-router"

const session = inject("$session")
// `__` is a global property, so the template resolves it on its own; script
// setup does not, and the fallback string below is built here.
const __ = inject("$translate")
const router = useRouter()
const showDialog = ref(true)

// The sheet is an ion-modal, presented at the app root, not inside this page:
// leaving the route left it open on top of every page after it (runtime crawl,
// 15 Sep 2026). It closes when the page is left. Its did-dismiss signs the user
// out, so a close caused by navigation must not count as the user's dismissal.
let leaving = false
function closeForNavigation() {
	leaving = true
	showDialog.value = false
}
onIonViewWillLeave(() => {
	console.info("[InvalidEmployee] leaving the page — closing the sheet")
	closeForNavigation()
})

function onDismissed() {
	showDialog.value = false
	if (leaving) return
	session.logout.submit()
}

// One dialog used to cover five different causes — no employee record, an
// inactive one, an ambiguous one, an unauthenticated session, or a lookup that
// simply failed — which sent people to the wrong support queue. The server
// knows which it is; ask it. Fetched only here, on the failure page, so the
// happy path costs nothing.
const identity = createResource({
	url: "hrms.api.get_employee_identity_status",
	auto: true,
	onSuccess(status) {
		// A valid employee is never shown "Login failed". The router guard sends
		// them Home before this page; this covers an employee fetch that failed
		// or answered late while the account itself is fine.
		if (status?.reason !== "ok") return
		console.info("[InvalidEmployee] identity is ok — routing Home")
		closeForNavigation()
		router.replace({ name: "Home" })
	},
	onError(error) {
		console.warn("[InvalidEmployee] Could not fetch identity status:", error?.message)
	},
})

const fallback = computed(() =>
	__(
		"No active employee found associated with the email ID {0}. Try logging in with your employee email ID or contact your HR manager for access.",
		[session?.user]
	)
)

const reason = computed(() => identity.data?.message || fallback.value)
</script>
