<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex h-screen w-screen flex-col justify-center bg-ground">
				<Dialog
					:options="{
						title: __('Login Failed'),
						message: reason,
						size: 'lg',
						actions: [
							{
								label: __('Go to Login'),
								variant: 'solid',
								onClick: () => session.logout.submit(),
							},
						],
					}"
					v-model="showDialog"
					@close="
						() => {
							session.logout.submit()
							showDialog = false
						}
					"
				/>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
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
