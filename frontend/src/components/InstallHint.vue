<!--
  iPhone Safari has no install prompt. This one row on Home says how, once
  per 30 days (alpha.7 0.10). It replaced a lime popover that covered the
  bottom of every page, forms included, with 1.18 contrast.
-->
<template>
	<div v-if="show" class="g-form-group g-install-hint" role="note">
		<div class="g-form-row">
			<Share class="g-install-hint__icon" aria-hidden="true" />
			<span class="g-install-hint__text">
				{{ __("Add Nadi to your Home Screen: tap Share, then “Add to Home Screen”.") }}
			</span>
			<button type="button" class="g-install-hint__close" :aria-label="__('Close')" @click="close">
				<X aria-hidden="true" />
			</button>
		</div>
	</div>
</template>

<script setup>
import { inject, ref } from "vue"
import { Share, X } from "lucide-vue-next"
import { INSTALL_DISMISS_KEY, showIosInstallHint } from "@/utils/installPromptMemory"

const __ = inject("$translate")

function stored() {
	try {
		return localStorage.getItem(INSTALL_DISMISS_KEY)
	} catch (e) {
		return null
	}
}

const show = ref(
	showIosInstallHint({
		userAgent: window.navigator.userAgent,
		standalone: Boolean(window.navigator.standalone),
		stored: stored(),
		now: Date.now(),
	})
)

function close() {
	console.info("[InstallHint] closed; quiet for 30 days")
	show.value = false
	try {
		localStorage.setItem(INSTALL_DISMISS_KEY, String(Date.now()))
	} catch (e) {
		// storage unavailable: the row may return next visit, no worse than before
	}
}
</script>
