<template>
	<GModal
		:is-open="props.open"
		:title="props.sopName ? __('Edit SOP') : __('New SOP')"
		@did-dismiss="close"
	>
		<div class="w-full flex flex-col">
			<!-- body -->
			<div class="flex flex-col gap-4 px-4 pb-4">
				<div class="flex flex-col gap-1.5">
					<label class="m-field-label" for="sop-title">{{ __("Title") }}</label>
					<input
						id="sop-title"
						v-model="form.title"
						type="text"
						:placeholder="__('e.g. Cash Handling Procedure')"
						class="m-field-input"
						:class="errors.title ? '!border-red-600' : ''"
					/>
					<span v-if="errors.title" class="text-kra-label font-bold text-red-600">
						{{ __("Title is required.") }}
					</span>
				</div>

				<div class="flex flex-col gap-1.5">
					<label class="m-field-label">{{ __("Scope") }}</label>
					<div class="flex gap-2">
						<button
							v-for="scope in SCOPES"
							:key="scope"
							type="button"
							class="g-eyebrow flex-1 min-h-11 py-2.5 px-2 border"
							:class="
								form.scope === scope
									? 'bg-accent-ink text-ground border-accent-ink'
									: 'bg-surface text-ink-700 border-divider'
							"
							:aria-pressed="form.scope === scope"
							style="
								transition: background-color var(--g-motion-state-change-duration)
										var(--g-motion-state-change-easing),
									color var(--g-motion-state-change-duration) var(--g-motion-state-change-easing),
									border-color var(--g-motion-state-change-duration)
										var(--g-motion-state-change-easing);
							"
							@click="setScope(scope)"
						>
							{{ __(scope) }}
						</button>
					</div>
				</div>

				<div class="flex flex-col gap-1.5">
					<label class="m-field-label" for="sop-department">{{ __("Department") }}</label>
					<select
						id="sop-department"
						v-model="form.department"
						:disabled="form.scope !== 'Department'"
						class="m-field-input disabled:opacity-45"
						:class="errors.department ? '!border-red-600' : ''"
					>
						<option value="">{{ __("Select department…") }}</option>
						<option
							v-for="department in departments.data || []"
							:key="department.name"
							:value="department.name"
						>
							{{ departmentLabel(department.name) }}
						</option>
					</select>
					<span v-if="errors.department" class="text-kra-label font-bold text-red-600">
						{{ __("Pick a department for a department-scoped SOP.") }}
					</span>
				</div>

				<div
					v-for="toggle in TOGGLES"
					:key="toggle.field"
					class="flex items-center justify-between"
				>
					<span class="flex flex-col gap-0.5">
						<span class="text-card-title font-bold text-inkbase">
							{{ __(toggle.label) }}
						</span>
						<span class="text-kra-label text-ink-700">{{ __(toggle.hint) }}</span>
					</span>
					<button
						type="button"
						role="switch"
						class="flex h-11 w-control-lg -my-2.5 -mr-1 flex-none items-center justify-center"
						:aria-label="__(toggle.label)"
						:aria-checked="form[toggle.field]"
						@click="form[toggle.field] = !form[toggle.field]"
					>
						<!-- The track is 44x24 and the knob 20, so the travel is
						     exactly 44 - 20 - (2 + 2) = 20px = translate-x-5. It was
						     42 wide, which left the knob 2px short of its own end
						     stop. -->
						<span
							class="relative h-icon-lg w-11"
							:class="form[toggle.field] ? 'bg-accent-ink' : 'bg-ink-400'"
							style="
								transition: background-color var(--g-motion-state-change-duration)
									var(--g-motion-state-change-easing);
							"
						>
							<span
								class="absolute top-0.5 left-0.5 h-icon-md w-icon-md bg-ground"
								:class="form[toggle.field] ? 'translate-x-5' : ''"
								style="
									transition: transform var(--g-motion-state-change-duration)
										var(--g-motion-state-change-easing);
								"
							></span>
						</span>
					</button>
				</div>

				<div class="flex flex-col gap-1.5">
					<label class="m-field-label" for="sop-content">{{ __("Content") }}</label>
					<textarea
						id="sop-content"
						v-model="form.content"
						rows="4"
						:placeholder="__('Write the procedure…')"
						class="m-field-input resize-y min-h-20"
					/>
				</div>

				<div class="flex flex-col gap-1.5">
					<label class="m-field-label">{{ __("Attachment") }}</label>
					<div class="flex items-center gap-2 flex-wrap">
						<label
							class="g-eyebrow g-touch flex items-center gap-1.5 border border-divider rounded-input text-inkbase px-3 py-2.5 cursor-pointer hover:bg-icon-bg"
						>
							<Paperclip class="h-3.5 w-3.5" />
							{{ __("Choose file") }}
							<input type="file" class="hidden" @change="onFileSelect" />
						</label>
						<span
							v-if="attachmentName"
							class="inline-flex items-center gap-1.5 bg-accent-100 text-accent-700 px-2 py-1.5 text-kra-label font-bold"
						>
							{{ attachmentName }}
							<button
								type="button"
								class="flex text-accent-700"
								:aria-label="__('Remove file')"
								@click="clearAttachment"
							>
								<X class="h-3 w-3" />
							</button>
						</span>
					</div>
				</div>
			</div>

			<!-- footer -->
			<div
				class="sticky bottom-0 flex gap-2.5 p-4 border-t border-divider bg-ground flex-none standalone:pb-safe-bottom"
			>
				<button
					type="button"
					class="flex-1 py-3 border border-accent-ink text-accent-ink text-card-title font-extrabold"
					@click="close"
				>
					{{ __("Cancel") }}
				</button>
				<button
					type="button"
					class="flex-1 py-3 border border-accent-ink bg-accent-ink text-ground text-card-title font-extrabold disabled:opacity-60"
					:disabled="saving"
					@click="save"
				>
					{{ saving ? __("Saving…") : __("Save") }}
				</button>
			</div>
		</div>
	</GModal>
</template>

<script setup>
import { departmentLabel } from "@/utils/departmentLabel"
import { Paperclip, X } from "lucide-vue-next"
import { personalCacheKey } from "@/utils/personalCache"
import GModal from "@/components/glass/GModal.vue"
import { createListResource, createResource, toast } from "frappe-ui"
import { computed, inject, reactive, ref, watch } from "vue"
import { firstMessage } from "@/utils/loudRequest"

const __ = inject("$translate")

const props = defineProps({
	open: { type: Boolean, default: false },
	// null = create, otherwise the SOP being edited
	sopName: { type: String, default: null },
})
const emit = defineEmits(["update:open", "saved"])

// i18n source strings: __("General"), __("Department")
const SCOPES = ["General", "Department"]
const TOGGLES = [
	{
		field: "pinned",
		label: "Pin to Essentials",
		hint: "Shows at the top for everyone",
	},
	{
		field: "published",
		label: "Published",
		hint: "Unpublished SOPs stay visible to HR only",
	},
]

const emptyForm = () => ({
	title: "",
	scope: "General",
	department: "",
	pinned: false,
	published: true,
	content: "",
})

const form = reactive(emptyForm())
const errors = reactive({ title: false, department: false })
const saving = ref(false)
const selectedFile = ref(null)
const existingAttachment = ref(null)
const attachmentCleared = ref(false)

const attachmentName = computed(
	() => selectedFile.value?.name || existingAttachment.value?.file_name || ""
)

const departments = createListResource({
	doctype: "Department",
	fields: ["name"],
	filters: { is_group: 0 },
	orderBy: "name asc",
	pageLength: 500,
	auto: true,
	cache: personalCacheKey("hrms:sop_departments"),
})

const detail = createResource({
	url: "hrms.api.sop.get_sop",
	onSuccess(doc) {
		Object.assign(form, {
			title: doc.title || "",
			scope: doc.scope || "General",
			department: doc.department || "",
			pinned: !!doc.pinned,
			published: !!doc.published,
			content: doc.content || "",
		})
		existingAttachment.value = doc.attachment || null
	},
	onError(error) {
		console.warn("[SOP] Failed to load for edit:", error)
	},
})

const sopDocs = createListResource({ doctype: "SOP Document" })

const updateSop = createResource({ url: "frappe.client.set_value" })
// clearing the field is not enough: legacy/Desk-attached files live only as
// File rows (empty field) and the server fallback would resurrect them
const removeAttachment = createResource({ url: "hrms.api.sop.remove_attachment" })

const prefill = () => {
	Object.assign(form, emptyForm())
	errors.title = false
	errors.department = false
	selectedFile.value = null
	existingAttachment.value = null
	attachmentCleared.value = false
	if (props.sopName) detail.fetch({ name: props.sopName })
}

//: Fresh form each time the sheet is asked to open (was ion-modal's willPresent).
watch(
	() => props.open,
	(open) => {
		if (open) prefill()
	}
)

const close = () => {
	emit("update:open", false)
}

const setScope = (scope) => {
	form.scope = scope
	errors.department = false
	if (scope === "General") form.department = ""
}

const onFileSelect = (event) => {
	selectedFile.value = event.target.files?.[0] || null
	if (selectedFile.value) attachmentCleared.value = false
}

const clearAttachment = () => {
	selectedFile.value = null
	if (existingAttachment.value) {
		existingAttachment.value = null
		attachmentCleared.value = true
	}
}

// A textarea holds plain text but `content` is a Text Editor field rendered
// with v-html — keep paragraph breaks instead of collapsing to one run-on line.
const escapeHtml = (text) =>
	text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")

const toHtml = (text) => {
	const value = (text || "").trim()
	if (!value || /<[a-z][\s\S]*>/i.test(value)) return value
	return value
		.split(/\n{2,}/)
		.map((block) => `<p>${escapeHtml(block).replace(/\n/g, "<br>")}</p>`)
		.join("")
}

// private file attached to the SOP: Frappe serves it to whoever passes
// has_permission on the SOP itself (the row-scope hook)
const uploadAttachment = async (docname, file) => {
	const body = new FormData()
	body.append("file", file, file.name)
	body.append("is_private", "1")
	body.append("doctype", "SOP Document")
	body.append("docname", docname)
	body.append("fieldname", "attachment")

	const headers = { "X-Frappe-Site-Name": window.location.hostname }
	if (window.csrf_token) headers["X-Frappe-CSRF-Token"] = window.csrf_token

	const response = await fetch("/api/method/upload_file", {
		method: "POST",
		headers,
		body,
	})
	const result = await response.json()
	if (!response.ok || !result?.message?.file_url) {
		throw new Error(result?.exception || __("Upload failed"))
	}
	console.info("[SOP] Attachment uploaded:", result.message.file_url)
	// Frappe's upload_file only creates the File row — it never writes the
	// file_url back into the docfield, so the caller must persist it.
	return result.message.file_url
}

const save = async () => {
	errors.title = !form.title.trim()
	errors.department = form.scope === "Department" && !form.department
	if (errors.title || errors.department) return

	saving.value = true
	try {
		const values = {
			title: form.title.trim(),
			scope: form.scope,
			department: form.scope === "Department" ? form.department : "",
			pinned: form.pinned ? 1 : 0,
			published: form.published ? 1 : 0,
			content: toHtml(form.content),
		}
		if (attachmentCleared.value) values.attachment = ""

		let docname = props.sopName
		const isCreate = !docname
		// Create + pending upload: insert unpublished, publish only once the file
		// is actually attached — a failed upload must never publish an SOP whose
		// attachment is missing.
		const deferPublish = isCreate && !!selectedFile.value && values.published === 1

		if (docname) {
			if (attachmentCleared.value) {
				await removeAttachment.fetch({ name: docname })
				console.info("[SOP] Attachment removed:", docname)
			}
			await updateSop.fetch({
				doctype: "SOP Document",
				name: docname,
				fieldname: values,
			})
		} else {
			const doc = await sopDocs.insert.submit(deferPublish ? { ...values, published: 0 } : values)
			docname = doc?.name || sopDocs.insert.data?.name
		}

		if (selectedFile.value && docname) {
			let fileUrl
			try {
				fileUrl = await uploadAttachment(docname, selectedFile.value)
			} catch (error) {
				// on edit the old attachment survives — let the generic handler
				// report it; on create the draft exists and must stay unpublished
				if (!isCreate) throw error
				console.warn("[SOP] Attachment upload failed after create:", error)
				toast({
					title: __("Attachment failed"),
					text: __(
						"Saved as an unpublished draft without the attachment — open it to retry. ({0})",
						[firstMessage(error)]
					),
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500",
				})
				emit("saved")
				close()
				return
			}
			await updateSop.fetch({
				doctype: "SOP Document",
				name: docname,
				fieldname: deferPublish ? { attachment: fileUrl, published: 1 } : { attachment: fileUrl },
			})
		}

		toast({
			title: __("Success"),
			text: props.sopName ? __("SOP updated") : __("SOP created"),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		emit("saved")
		close()
	} catch (error) {
		console.warn("[SOP] Save failed:", error)
		toast({
			title: __("Error"),
			text: firstMessage(error, __("Could not save the SOP")),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
	} finally {
		saving.value = false
	}
}
</script>

<style scoped>
/* mockup field styling — 10px label over a surface-filled square
   input; scoped so it cannot leak into other forms */
.m-field-label {
	font-size: 10px;
	font-weight: 800;
	letter-spacing: 0.07em;
	color: rgb(var(--g-ink2));
	font-family: var(--g-font-display);
}
.m-field-input {
	width: 100%;
	background: rgb(var(--g-glass-fill-fallback));
	border: 1px solid var(--g-hair);
	padding: 10px 11px;
	font-family: var(--g-font-ui);
	font-size: 13px;
	color: rgb(var(--g-ink));
	outline: none;
}
.m-field-input:focus {
	border-color: var(--g-accent-ink);
}
</style>
