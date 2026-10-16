<!--
  Shift Attendance, to download (owner, 14 Oct 2026).

  For the "Attendance Report Viewer" role: pick a month, get the company's
  Shift Attendance as an Excel file. Reached from More > Apps (data/appLinks.js
  `route`). The server (hrms/api/attendance_download.py) fixes the company to
  the viewer's own Company permission and refuses everyone else, so this screen
  only shows what it is told and never chooses a company.

  The download is a plain GET of the method, handed to the browser: it saves the
  attachment, and being the same origin the session cookie goes with it.
-->
<template>
	<GPage>
		<ShellHeader :title="__('Shift attendance')" />
		<ion-content class="ion-padding g-page__content">
			<div class="w-full max-w-content-column-lg mx-auto p-4 flex flex-col gap-3">
				<!-- Not a viewer: a plain line, no button (the download refuses too) -->
				<p v-if="noAccess" class="g-form-footer" role="status">
					{{ __("This is for staff HR has given the Attendance Report Viewer role.") }}
				</p>

				<ResourceError v-else-if="company.error" :resource="company" what="your company" />

				<template v-else>
					<div class="g-form-section">
						<div class="g-form-group">
							<div class="g-form-row">
								<span class="g-form-row__label">{{ __("Month") }}</span>
								<GSelect v-model="month" :options="months" :aria-label="__('Month')" />
							</div>
							<div v-value-row class="g-form-row g-form-row--readonly">
								<span class="g-form-row__label">{{ __("Company") }}</span>
								<span class="g-form-row__value">{{ companyName }}</span>
							</div>
							<div v-value-row class="g-form-row g-form-row--readonly">
								<span class="g-form-row__label">{{ __("Dates") }}</span>
								<span class="g-form-row__value">{{ dates }}</span>
							</div>
						</div>
						<p class="g-form-footer">
							{{
								__(
									"Everyone in your company, one row per person per day: shift, status, in, out, hours, late, early."
								)
							}}
						</p>
					</div>

					<GButton
						:label="__('Download Excel')"
						:pending="saving"
						:disabled="!canDownload || saving"
						@click="download"
					/>
					<p v-if="saved" class="g-form-footer g-download__saved" role="status"><span aria-hidden="true">✓</span> {{ saved }}</p>
					<p v-if="failed" class="g-form-footer g-download__failed" role="alert">{{ failed }}</p>
					<p v-if="!online" class="g-form-footer" role="status">
						{{ __("You are offline. Connect to download.") }}
					</p>

					<button
						type="button"
						class="g-focusable g-list-more px-4 py-3 text-sm text-ink-600 bg-transparent border-none"
						:disabled="!online"
						@click="openDesk"
					>
						{{ __("Open the full report in Desk") }} ›
					</button>
				</template>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import { computed, inject, ref } from "vue"
import { IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"

import GButton from "@/components/glass/GButton.vue"
import GPage from "@/components/glass/GPage.vue"
import GSelect from "@/components/glass/GSelect.vue"
import ResourceError from "@/components/ResourceError.vue"
import ShellHeader from "@/components/ShellHeader.vue"
import { useOnline } from "@/composables/useOnline"
import { downloadUrl, monthDates, monthOptions } from "@/utils/attendanceDownload"
import { sessionUser } from "@/utils/personalCache"
import { isNoAccess } from "@/utils/sessionLost"

const __ = inject("$translate")
const online = useOnline()

// The current month and the 11 before it; opens on the current month.
const months = monthOptions(new Date())
const month = ref(months[0].value)
const dates = computed(() => monthDates(month.value))

// The server's own answer (GET only; frappe-ui defaults to POST). Not cached:
// it is a small read and a stale company name on a download screen would lie.
const company = createResource({
	url: "hrms.api.attendance_download.my_company",
	method: "GET",
	auto: true,
})
const companyName = computed(() => (company.data?.companies || []).join(", ") || "—")

// A refusal from someone still signed in: they do not hold the role.
const noAccess = computed(() =>
	isNoAccess(company.error, { signedIn: Boolean(sessionUser()) })
)

const canDownload = computed(
	() => online.value && !company.loading && !company.error && Boolean(company.data)
)

// Fetched, not navigated to (reviews of 399090a5a): a refusal or an expired
// session stays on this screen as a sentence, instead of leaving Nadi for a
// raw error page. The file is saved the way the PDF download saves one.
const saving = ref(false)
const saved = ref("")
const failed = ref("")

async function download() {
	if (saving.value) return
	saving.value = true
	saved.value = failed.value = ""
	const name = `shift-attendance-${month.value}.xlsx`
	console.info("[AttendanceDownload] downloading", month.value)
	try {
		const response = await fetch(downloadUrl(month.value), { credentials: "same-origin" })
		if (!response.ok) throw new Error(await refusalOf(response))
		const blob = await response.blob()
		const url = window.URL.createObjectURL(blob)
		const link = document.createElement("a")
		link.href = url
		link.download = name
		link.click()
		setTimeout(() => window.URL.revokeObjectURL(url), 3000)
		// iPhone shows a preview to save from, so "started", not "saved" (review of cddd5c784)
		saved.value = __("Download started: {0}", [name])
	} catch (error) {
		console.warn("[AttendanceDownload] download failed", error)
		failed.value = error?.message || __("Could not download the file. Try again.")
	} finally {
		saving.value = false
	}
}

//: The server's own sentence for a refusal (frappe sends it in _server_messages / exception).
async function refusalOf(response) {
	try {
		const body = await response.json()
		const messages = body?._server_messages ? JSON.parse(body._server_messages) : []
		const first = messages.length ? JSON.parse(messages[0])?.message : ""
		// never a Python class path ("frappe.exceptions.PermissionError: ..."): only its sentence
		const plain = String(body?.exception || "").split(": ").pop()
		return first || plain || __("Could not download the file. Try again.")
	} catch {
		return __("Could not download the file. Try again.")
	}
}

function openDesk() {
	console.info("[AttendanceDownload] opening the full report in Desk")
	window.location.assign("/desk/query-report/Shift%20Attendance")
}
</script>

<style>
.g-download__saved {
	color: var(--g-success-ink);
	font-weight: 600;
}
.g-download__failed {
	color: var(--g-danger-ink);
}
</style>
