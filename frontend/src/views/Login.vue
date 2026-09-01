<template>
	<GPage>
		<ion-content class="ion-no-padding">
			<!-- §12 Sign in: logo well → title → subtitle → email → password →
			     primary → forgot-password link. Vertically centred, 40px bottom
			     offset. The two-panel accent split this replaces was stock Frappe
			     HR, not this design. §20.8: at lg: the same column simply centres
			     in the viewport — there is no sidebar to align against. -->
			<div class="g-auth">
				<div class="g-auth__column">
					<GLogoWell :label="__('Nadi')" />

					<div>
						<h1 class="g-auth__title">{{ __("Login to Nadi") }}</h1>
						<p class="g-auth__subtitle">{{ __("Employee self-service portal") }}</p>
					</div>

					<form
						v-if="!user_pass_login_disabled.data"
						class="flex flex-col gap-stack-md"
						@submit.prevent="submit"
					>
						<GInput
							v-model="email"
							type="text"
							:label="__('Email')"
							:placeholder="__('johndoe@mail.com')"
							autocomplete="username"
						/>
						<GInput
							v-model="password"
							type="password"
							:label="__('Password')"
							placeholder="••••••"
							:error="errorMessage"
							autocomplete="current-password"
						/>

						<GButton
							type="submit"
							:label="__('Login')"
							:pending-label="__('Signing in…')"
							:pending="session.login.loading"
						>
							<template #trailing>
								<svg
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<line x1="5" y1="12" x2="19" y2="12"></line>
									<polyline points="12 5 19 12 12 19"></polyline>
								</svg>
							</template>
						</GButton>

						<button type="button" class="g-auth__link g-focusable" @click="openForgotDialog">
							{{ __("Forgot Password?") }}
						</button>
					</form>

					<!-- glass-surfaces: bounded — the provider list comes from Social
					     Login Key records, which an administrator configures and which
					     number one or two in practice. Unlike an employee's issue
					     history this cannot grow with usage, so the v-for does not need
					     §15.2 flattening. See design/gates/surfaces.mjs. -->
					<template v-if="authProviders.data?.length">
						<div v-if="!user_pass_login_disabled.data" class="g-auth__or">
							{{ __("or") }}
						</div>
						<div class="flex flex-col gap-stack-sm">
							<GProviderButton
								v-for="provider in authProviders.data"
								:key="provider.name"
								:name="provider.provider_name"
								:icon="provider.icon"
								:href="provider.auth_url"
							/>
						</div>
					</template>

					<div v-else-if="user_pass_login_disabled.data" class="g-auth__subtitle">
						{{ __("No login methods are available. Please contact your administrator.") }}
					</div>
				</div>
			</div>

			<!-- Deferred from 5.1: these three hold forms with their own
			     validation, not confirmations, so they needed the batch that owns
			     Login. GModal carries the focus-trap workaround (§16.3), which
			     matters most here — an OTP field inside a trapped ion-modal is
			     exactly the bug that workaround exists for. -->
			<GModal
				:is-open="resetPassword.showDialog"
				:title="__('Reset password')"
				@did-dismiss="resetPassword.showDialog = false"
			>
				<p class="g-confirm__body">
					{{ __("Your password has expired. Please reset your password to continue") }}
				</p>
				<a class="g-provider" :href="resetPassword.link" target="_blank">
					{{ __("Go to Reset Password page") }}
				</a>
			</GModal>

			<GModal
				:is-open="forgot.showDialog"
				:title="__('Forgot password')"
				@did-dismiss="forgot.showDialog = false"
			>
				<form class="flex flex-col gap-stack-md" @submit.prevent="sendResetLink">
					<GInput
						v-model="forgot.email"
						:label="__('Email')"
						:placeholder="__('johndoe@mail.com')"
						:error="forgot.error"
						autocomplete="username"
					/>
					<p v-if="forgot.sent" class="g-confirm__body">
						{{
							__("If this email is registered, password reset instructions have been sent to it.")
						}}
					</p>
					<GButton
						v-else
						type="submit"
						:label="__('Send Reset Link')"
						:pending-label="__('Sending…')"
						:pending="forgot.loading"
					/>
				</form>
			</GModal>

			<GModal
				:is-open="otp.showDialog"
				:title="__('OTP verification')"
				@did-dismiss="otp.showDialog = false"
			>
				<p v-if="otp.verification.prompt" class="g-confirm__body">
					{{ otp.verification.prompt }}
				</p>
				<form class="flex flex-col gap-stack-md" @submit.prevent="submit">
					<GInput
						v-model="otp.code"
						:label="__('OTP Code')"
						placeholder="000000"
						:error="errorMessage"
						autocomplete="one-time-code"
					/>
					<GButton
						type="submit"
						:label="__('Verify')"
						:pending-label="__('Verifying…')"
						:pending="session.otp.loading"
					/>
				</form>
			</GModal>
		</ion-content>
	</GPage>
</template>

<script setup>
import GLogoWell from "@/components/glass/GLogoWell.vue"
import GInput from "@/components/glass/GInput.vue"
import GModal from "@/components/glass/GModal.vue"
import GProviderButton from "@/components/glass/GProviderButton.vue"
import GPage from "@/components/glass/GPage.vue"
import GButton from "@/components/glass/GButton.vue"
import { IonContent } from "@ionic/vue"
import { inject, reactive, ref } from "vue"
import { createResource } from "frappe-ui"

import { sendPasswordResetLink } from "@/utils/resetPassword"

const email = ref(null)
const password = ref(null)
const errorMessage = ref("")

const forgot = reactive({
	showDialog: false,
	email: "",
	error: "",
	sent: false,
	loading: false,
})

function openForgotDialog() {
	forgot.email = email.value || ""
	forgot.error = ""
	forgot.sent = false
	forgot.showDialog = true
}

async function sendResetLink() {
	if (!forgot.email) {
		forgot.error = __("Please enter your email")
		return
	}
	forgot.error = ""
	forgot.loading = true
	try {
		await sendPasswordResetLink(forgot.email.trim())
		forgot.sent = true
		console.info("[Login] Password reset link requested")
	} catch (err) {
		forgot.error = __(err.message)
	} finally {
		forgot.loading = false
	}
}

const resetPassword = reactive({
	showDialog: false,
	link: "",
})
const otp = reactive({
	showDialog: false,
	tmp_id: "",
	code: "",
	verification: {},
})

const session = inject("$session")
const __ = inject("$translate")

async function submit(_e) {
	try {
		let response
		if (otp.showDialog) {
			response = await session.otp(otp.tmp_id, otp.code)
		} else {
			response = await session.login(email.value, password.value)
		}

		if (response.message === "Password Reset") {
			resetPassword.showDialog = true
			resetPassword.link = response.redirect_to
		} else {
			resetPassword.showDialog = false
			resetPassword.link = ""
		}

		// OTP verification
		if (response.verification) {
			if (response.verification.setup) {
				otp.showDialog = true
				otp.tmp_id = response.tmp_id
				otp.verification = response.verification
			} else {
				// Don't bother handling impossible OTP setup (e.g. no phone number).
				window.open("/login?redirect-to=" + encodeURIComponent(window.location.pathname), "_blank")
			}
		}
	} catch (error) {
		// A network failure or any non-Frappe error has no `.messages`; joining it
		// blindly threw inside the catch, so a failed sign-in showed nothing at all.
		errorMessage.value =
			error?.messages?.join("\n") ||
			error?.message ||
			__("Could not sign in. Please check your connection and try again.")
	}
}

const user_pass_login_disabled = createResource({
	url: "hrms.api.system_settings.get_user_pass_login_disabled",
	method: "GET",
	initialData: 1,
	auto: true,
})

const authProviders = createResource({
	url: "hrms.api.oauth.oauth_providers",
	auto: true,
})
</script>
