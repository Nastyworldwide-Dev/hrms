import { gToast } from "@/components/glass/toast"
import { inject } from "vue"
import { firstMessage } from "@/utils/loudRequest"

export function useDownloadPDF() {
	// inject() must run synchronously during a component's setup(), which is
	// why this sits here rather than inside downloadPDF() below — every call
	// site so far invokes useDownloadPDF() at the top of <script setup>, so
	// this is always reached in time. `__` was previously referenced
	// unimported in the catch handler below: a real download failure threw
	// ReferenceError instead of showing the user anything, so the one path
	// meant to explain the failure silently ate it instead.
	const __ = inject("$translate")
	console.info("[commonUtils] useDownloadPDF initialised")

	async function downloadPDF({ doctype, docname, filename = null }) {
		const headers = {
			"X-Frappe-Site-Name": window.location.hostname,
		}
		if (window.csrf_token) {
			headers["X-Frappe-CSRF-Token"] = window.csrf_token
		}

		fetch("/api/method/hrms.api._download_pdf", {
			method: "POST",
			headers,
			body: new URLSearchParams({ doctype: doctype, docname: docname }),
			responseType: "blob",
		})
			.then((response) => {
				if (response.ok) {
					return response.blob()
				} else {
					gToast({
						title: "Download Failed",
						text: `Error downloading PDF`,
						variant: "error",
					})
				}
			})
			.then((blob) => {
				if (!blob) return
				const blobUrl = window.URL.createObjectURL(blob)
				const link = document.createElement("a")
				link.href = blobUrl
				link.download = `${filename || docname}.pdf`
				link.click()
				setTimeout(() => {
					window.URL.revokeObjectURL(blobUrl)
				}, 3000)
			})
			.catch((error) => {
				gToast({
					title: __("Error"),
					text: __("Error downloading PDF: {0}", [firstMessage(error)]),
					variant: "error",
				})
			})
	}

	return {
		downloadPDF,
	}
}
