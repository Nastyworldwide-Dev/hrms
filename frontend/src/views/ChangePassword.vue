<template>
	<GPage>
		<ion-content :fullscreen="true">
			<!-- 8.5 — never migrated: imported GPage/GInput/GButton but used only
			     GPage, and a hardcoded `bg-white` painted over the theme so the dark
			     capture rendered a white page with a near-white primary on it. -->
			<div class="flex flex-col h-full w-full">
				<div class="w-full h-full sm:w-96 flex flex-col">
					<header
						class="flex flex-row bg-ground py-4 px-3 items-center sticky top-0 z-sticky border-b border-divider"
					>
						<GIconButton :label="__('Back')" flush class="mr-1" @click="goBackOrHome(router)">
							<FeatherIcon name="chevron-left" class="h-5 w-5 text-inkbase" />
						</GIconButton>
						<h2 class="text-xl font-extrabold text-inkbase tracking-tight">
							{{ __("Change Password") }}
						</h2>
					</header>

					<div class="grow overflow-y-auto">
						<form class="flex flex-col space-y-4 p-4" @submit.prevent="submitPasswordChange">
							<GInput
								:label="__('Current Password') + ' *'"
								type="password"
								v-model="currentPassword"
								autocomplete="current-password"
							/>
							<GInput
								:label="__('New Password') + ' *'"
								type="password"
								v-model="newPassword"
								autocomplete="new-password"
							/>
							<GInput
								:label="__('Confirm New Password') + ' *'"
								type="password"
								v-model="confirmPassword"
								autocomplete="new-password"
								:error="changePasswordError"
							/>
						</form>
					</div>

					<div
						class="px-4 pt-4 pb-4 standalone:pb-safe-bottom sm:w-96 bg-ground sticky bottom-0 w-full z-40 border-t border-divider"
					>
						<GButton
							:label="__('Update Password')"
							:pending-label="__('Updating…')"
							:pending="updatePasswordResource.loading"
							@click="submitPasswordChange"
						/>
					</div>
				</div>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import GIconButton from "@/components/glass/GIconButton.vue"
import GButton from "@/components/glass/GButton.vue"
import GInput from "@/components/glass/GInput.vue"
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { useRouter } from "vue-router"
import { goBackOrHome } from "@/utils/navigation"
import { FeatherIcon, toast, createResource } from "frappe-ui"

import { inject, ref } from "vue"

const __ = inject("$translate")
const router = useRouter()

const changePasswordError = ref("")
const currentPassword = ref("")
const newPassword = ref("")
const confirmPassword = ref("")

const updatePasswordResource = createResource({
	url: "frappe.core.doctype.user.user.update_password",
	method: "POST",
	onSuccess() {
		toast({
			title: __("Success"),
			text: __("Your password has been updated."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		resetForm()
		router.back()
	},
	onError(error) {
		changePasswordError.value = error.messages?.[0] || __("Failed to update password")
	},
})

function resetForm() {
	changePasswordError.value = ""
	currentPassword.value = ""
	newPassword.value = ""
	confirmPassword.value = ""
}

function submitPasswordChange() {
	if (!currentPassword.value || !newPassword.value || !confirmPassword.value) {
		changePasswordError.value = __("Please fill all fields")
		return
	}

	if (newPassword.value !== confirmPassword.value) {
		changePasswordError.value = __("New passwords do not match")
		return
	}

	changePasswordError.value = ""
	updatePasswordResource.submit({
		old_password: currentPassword.value,
		new_password: newPassword.value,
	})
}
</script>
