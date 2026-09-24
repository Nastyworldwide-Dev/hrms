<template>
	<GPage>
		<!-- The one header (alpha.5), in place of a hand-drawn bar. -->
		<ShellHeader :title="__('Change password')" />
		<ion-content class="g-page__content">
			<!-- 8.5 — never migrated: imported GPage/GInput/GButton but used only
			     GPage, and a hardcoded `bg-white` painted over the theme so the dark
			     capture rendered a white page with a near-white primary on it. -->
			<div class="flex flex-col h-full w-full">
				<div class="w-full h-full sm:w-96 flex flex-col">
					<div class="grow overflow-y-auto">
						<!-- One inset group, like every form (alpha.6 B2; iOS Settings >
						     Password). Each field is a row: label leading, entry trailing. -->
						<form class="g-form-body" @submit.prevent="submitPasswordChange">
							<section class="g-form-section">
								<div class="g-form-group">
									<label class="g-form-row">
										<span class="g-form-row__label">{{ __("Current") }}</span>
										<GInput
											type="password"
											:aria-label="__('Current password')"
											:placeholder="__('Required')"
											v-model="currentPassword"
											autocomplete="current-password"
										/>
									</label>
									<label class="g-form-row">
										<span class="g-form-row__label">{{ __("New") }}</span>
										<GInput
											type="password"
											:aria-label="__('New password')"
											:placeholder="__('Required')"
											v-model="newPassword"
											autocomplete="new-password"
										/>
									</label>
									<label class="g-form-row">
										<span class="g-form-row__label">{{ __("Confirm") }}</span>
										<GInput
											type="password"
											:aria-label="__('Confirm new password')"
											:placeholder="__('Required')"
											v-model="confirmPassword"
											autocomplete="new-password"
										/>
									</label>
								</div>
								<p v-if="changePasswordError" class="g-form-footer g-field-error" role="alert">
									{{ changePasswordError }}
								</p>
							</section>
						</form>
					</div>

					<div
						class="px-4 pt-4 pb-4 standalone:pb-safe-bottom sm:w-96 bg-ground sticky bottom-0 w-full z-40 border-t border-divider"
					>
						<GButton
							:label="__('Update password')"
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
import ShellHeader from "@/components/ShellHeader.vue"
import GButton from "@/components/glass/GButton.vue"
import GInput from "@/components/glass/GInput.vue"
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { useRouter } from "vue-router"
import { goBackOrHome } from "@/utils/navigation"
import { createResource } from "frappe-ui"
import { gToast } from "@/components/glass/toast"

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
		gToast({
			title: __("Success"),
			text: __("Your password has been updated."),
			variant: "success",
		})
		resetForm()
		goBackOrHome(router)
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
