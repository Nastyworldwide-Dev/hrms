<template>
	<GPage>
		<ion-content class="ion-padding">
			<div class="flex h-screen w-screen flex-col justify-center bg-ground">
				<GModal
					:is-open="showDialog"
					:title="__('Login failed')"
					@did-dismiss="() => { session.logout.submit(); showDialog = false }"
				>
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
import { IonContent } from "@ionic/vue"
import { computed, inject, ref } from "vue"
import { Dialog, createResource } from "frappe-ui"

const session = inject("$session")
// `__` is a global property, so the template resolves it on its own; script
// setup does not, and the fallback string below is built here.
const __ = inject("$translate")
const showDialog = ref(true)

// One dialog used to cover five different causes — no employee record, an
// inactive one, an ambiguous one, an unauthenticated session, or a lookup that
// simply failed — which sent people to the wrong support queue. The server
// knows which it is; ask it. Fetched only here, on the failure page, so the
// happy path costs nothing.
const identity = createResource({
	url: "hrms.api.get_employee_identity_status",
	auto: true,
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
