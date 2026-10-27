<template>
	<!-- On the kit (owner, 25 Sep 2026: hand-rolled screens): grouped rows,
	     the kit's input, segmented scope, picker, switches and text area, and
	     its two buttons. Behaviour unchanged. -->
	<GModal
		:is-open="props.open"
		:title="props.sopName ? __('Edit SOP') : __('New SOP')"
		@did-dismiss="close"
	>
		<div class="g-form-body">
			<section class="g-form-section">
				<div class="g-form-group">
					<label class="g-form-row">
						<span class="g-form-row__label">{{ __("Title") }}</span>
						<GInput
							v-model="form.title"
							:aria-label="__('Title')"
							:placeholder="__('e.g. Cash Handling Procedure')"
							:error="errors.title ? __('Title is required.') : ''"
						/>
					</label>
				</div>
			</section>

			<section class="g-form-section">
				<h2 class="g-form-section__title">{{ __("Who sees it") }}</h2>
				<GSegmented
					:buttons="SCOPES.map((scope) => ({ key: scope, label: __(scope) }))"
					:model-value="form.scope"
					:label="__('Scope')"
					@update:model-value="setScope"
				/>
				<div v-if="form.scope === 'Department'" class="g-form-group">
					<label class="g-form-row">
						<span class="g-form-row__label">{{ __("Department") }}</span>
						<GSelect
							:options="(departments.data || []).map((d) => ({ value: d.name, label: departmentLabel(d.name) }))"
							:model-value="form.department"
							:aria-label="__('Department')"
							:placeholder="__('Required')"
							@update:model-value="(v) => (form.department = v)"
						/>
					</label>
				</div>
				<p v-if="errors.department" class="g-form-footer g-field__error" role="alert">
					{{ __("Pick a department for a department-scoped SOP.") }}
				</p>
				<!-- Which companies (15 Oct 2026). Left out, Frappe filled in the HR
				     user's own company from their Company permission, so an SOP meant
				     for everyone reached one company only. Sent on every save. -->
				<div class="g-form-group">
					<label class="g-form-row">
						<span class="g-form-row__label">{{ __("Company") }}</span>
						<GSelect
							:options="companyOptions"
							:model-value="sopCompany"
							:disabled="!companyReady"
							:aria-label="__('Company')"
							@update:model-value="(v) => (sopCompany = v || '')"
						/>
					</label>
				</div>
				<p class="g-form-footer" aria-live="polite">{{ whoSees }}</p>
			</section>

			<!-- Folder (owner, 27 Oct 2026): an SOP sits in one folder, or none. -->
			<section class="g-form-section">
				<div class="g-form-group">
					<label class="g-form-row">
						<span class="g-form-row__label">{{ __("Folder") }}</span>
						<GSelect
							:key="folderPickerKey"
							:options="folderOptions"
							:model-value="form.folder"
							:aria-label="__('Folder')"
							:placeholder="__('No folder')"
							@update:model-value="pickFolder"
						/>
					</label>
				</div>
				<p class="g-form-footer">{{ __("An SOP sits in one folder. Staff find it there.") }}</p>
			</section>

			<section class="g-form-section">
				<div class="g-form-group">
					<div v-for="toggle in TOGGLES" :key="toggle.field" class="g-form-row">
						<span class="g-form-row__label">{{ __(toggle.label) }}</span>
						<GSwitch
							class="g-form-row__switch"
							:aria-label="__(toggle.label)"
							:model-value="Boolean(form[toggle.field])"
							@update:model-value="(on) => (form[toggle.field] = on)"
						/>
					</div>
				</div>
				<p class="g-form-footer">{{ TOGGLES.map((t) => __(t.hint)).join(" · ") }}</p>
			</section>

			<section class="g-form-section">
				<div class="g-form-group">
					<div class="g-form-row g-form-row--stacked">
						<span :id="contentLabelId" class="g-form-row__label">{{ __("Content") }}</span>
						<GSegmented
							v-model="mode"
							:buttons="MODES.map((m) => ({ key: m.key, label: __(m.label) }))"
							:label="__('Content view')"
						/>
						<!-- Stays mounted while previewing, so nothing typed is lost. -->
						<div
							v-show="mode === 'write'"
							class="g-texteditor"
							role="group"
							:aria-labelledby="contentLabelId"
						>
							<TextEditor
								:content="form.content"
								@change="(html) => (form.content = html)"
								:fixedMenu="TOOLBAR"
								editor-class="prose-sm p-2 min-h-40"
							/>
						</div>
						<!-- The reader's own door and class (SopDetail): what HR sees here is what staff get. -->
						<div v-if="mode === 'preview'" class="g-sop-preview">
							<div v-if="form.content" class="sop-prose" v-html="safeHtml(form.content)"></div>
							<p v-else class="g-form-footer">{{ __("Nothing to show yet") }}</p>
						</div>
					</div>
				</div>
			</section>

			<section class="g-form-section">
				<div class="g-form-group">
					<label class="g-form-row g-form-row--action">
						<span class="g-form-row__label">{{ attachmentName || __("Add a file") }}</span>
						<Paperclip class="g-row__chevron" aria-hidden="true" />
						<input type="file" class="sr-only" @change="onFileSelect" />
					</label>
					<button
						v-if="attachmentName"
						type="button"
						class="g-form-row g-form-row--action g-form-row--destructive"
						@click="clearAttachment"
					>
						{{ __("Remove file") }}
					</button>
				</div>
			</section>

			<div class="flex flex-row gap-3">
				<GGhostButton class="flex-1" :label="__('Cancel')" @click="close" />
				<GButton class="flex-1" :label="__('Save')" :pending="saving" :disabled="saving" @click="save" />
			</div>
		</div>
	</GModal>

	<GModal :is-open="newFolderOpen" :title="__('New folder')" @did-dismiss="newFolderOpen = false">
		<div class="g-form-body">
			<section class="g-form-section">
				<div class="g-form-group">
					<label class="g-form-row">
						<span class="g-form-row__label">{{ __("Name") }}</span>
						<GInput
							v-model="newFolderName"
							:aria-label="__('Folder name')"
							:placeholder="__('e.g. Safety')"
							:maxlength="80"
							@keydown.enter="submitNewFolder"
						/>
					</label>
				</div>
				<!-- a dimmed Create says why, visibly and to a screen reader -->
				<p
					v-if="!newFolderName.trim()"
					:id="newFolderHintId"
					class="g-form-footer"
					aria-live="polite"
				>
					{{ __("Name the folder") }}
				</p>
			</section>
			<GButton
				:label="__('Create')"
				:pending="createFolder.loading"
				:disabled="!newFolderName.trim() || createFolder.loading"
				:aria-describedby="newFolderName.trim() ? undefined : newFolderHintId"
				@click="submitNewFolder"
			/>
		</div>
	</GModal>
</template>

<script setup>
import { departmentLabel } from "@/utils/departmentLabel"
import { safeHtml } from "@/utils/safeHtml"
import { Paperclip } from "lucide-vue-next"
import { personalCacheKey } from "@/utils/personalCache"
import GModal from "@/components/glass/GModal.vue"
import GButton from "@/components/glass/GButton.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GInput from "@/components/glass/GInput.vue"
import GSegmented from "@/components/glass/GSegmented.vue"
import GSelect from "@/components/glass/GSelect.vue"
import GSwitch from "@/components/glass/GSwitch.vue"
import { createListResource, createResource } from "frappe-ui"
import { gToast } from "@/components/glass/toast"
import { computed, defineAsyncComponent, inject, reactive, ref, useId, watch } from "vue"
import { firstMessage, saveFailedSentence } from "@/utils/loudRequest"

// Loaded only when the sheet opens (alpha.12 C4, as FormField does): a static
// import would pull the whole editor into every page's first download.
const TextEditor = defineAsyncComponent(() => import("frappe-ui/src/components/TextEditor/TextEditor.vue"))

// What staff can actually read. No Image or Video: the editor stores those inside
// the text as data:, which the reader's safeHtml removes, so staff saw an empty
// picture (review of S1, 6 Oct). A picture goes through "Add a file" below, a
// private file attached to the SOP.
const TOOLBAR = [
	["Heading 1", "Heading 2", "Heading 3"],
	"Paragraph",
	"Separator",
	"Bold",
	"Italic",
	"Separator",
	"Bullet List",
	"Numbered List",
	"Separator",
	"Link",
	"Blockquote",
]

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

// i18n source strings: __("Write"), __("As staff see it")
const MODES = [
	{ key: "write", label: "Write" },
	{ key: "preview", label: "As staff see it" },
]

const emptyForm = () => ({
	title: "",
	scope: "General",
	department: "",
	pinned: false,
	published: true,
	content: "",
	folder: "",
})

const form = reactive(emptyForm())
const errors = reactive({ title: false, department: false })
const saving = ref(false)
const mode = ref("write")
const contentLabelId = useId()
// the SOP's company ("" = every company); get_sop does not carry it, so it is read separately
const sopCompany = ref("")
// an edit only sends a company once the SOP's own company has been read: saving
// before that would send "" and widen it to every company (security review of e6e42d136)
const companyReady = ref(true)
const selectedFile = ref(null)
const existingAttachment = ref(null)
const attachmentCleared = ref(false)

// One plain line under Scope: who will actually see this SOP.
const whoSees = computed(() => {
	if (form.scope === "Department") {
		const dept = form.department
			? __("Only {0}", [departmentLabel(form.department)])
			: __("Only the department you pick")
		// the company row narrows a department SOP too, so the line says so
		return sopCompany.value ? __("{0}, in {1}", [dept, sopCompany.value]) : dept
	}
	return sopCompany.value ? __("Everyone in {0}", [sopCompany.value]) : __("Everyone")
})

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
			// an old plain-text SOP opens as paragraphs the editor can show
			content: toHtml(doc.content),
			folder: doc.folder || "",
		})
		existingAttachment.value = doc.attachment || null
	},
	onError(error) {
		console.warn("[SOP] Failed to load for edit:", error)
	},
})

// every company the site has, as the picker's choices; "" = all of them
const companies = createResource({ url: "hrms.api.get_company_currencies", auto: true })
// the SOP's own company is always a choice, even before (or without) the list:
// otherwise an SOP for one company showed "All companies" (design review of e6e42d136)
const companyOptions = computed(() => {
	const names = new Set(Object.keys(companies.data || {}))
	if (sopCompany.value) names.add(sopCompany.value)
	return [
		{ value: "", label: __("All companies") },
		...[...names].sort().map((name) => ({ value: name, label: name })),
	]
})

const companyLookup = createResource({
	url: "frappe.client.get_value",
	onSuccess(row) {
		sopCompany.value = row?.company || ""
		companyReady.value = true
	},
	onError(error) {
		console.warn("[SOP] Could not read the SOP's company:", error)
	},
})

// The folders are the SOP list's own answer (same cache key as SopList): one
// fetch for the list, the picker and Manage folders.
const library = createResource({
	url: "hrms.api.sop.get_sops",
	cache: personalCacheKey("hrms:sops"),
	auto: true,
})
const NEW_FOLDER = "__new__"
// "No folder" is GSelect's own empty choice (its placeholder), so the list
// never carries two empty-valued options
const folderOptions = computed(() => [
	...(library.data?.folders || []).map((f) => ({ value: f.name, label: f.folder_name })),
	{ value: NEW_FOLDER, label: __("New folder…") },
])

const newFolderOpen = ref(false)
const newFolderName = ref("")
const newFolderHintId = useId()
const createFolder = createResource({ url: "hrms.api.sop.save_folder" })

// the native select shows "New folder…" once picked; re-keying it puts the
// real choice back when the New folder sheet is closed without creating one
const folderPickerKey = ref(0)

const pickFolder = (value) => {
	if (value !== NEW_FOLDER) {
		form.folder = value || ""
		return
	}
	newFolderName.value = ""
	newFolderOpen.value = true
	folderPickerKey.value++
}

const submitNewFolder = async () => {
	if (!newFolderName.value.trim() || createFolder.loading) return
	try {
		const folder = await createFolder.fetch({ folder_name: newFolderName.value.trim() })
		await library.reload()
		form.folder = folder.name
		newFolderOpen.value = false
	} catch (error) {
		console.warn("[SOP] Folder create failed:", error)
		gToast({
			title: __("Error"),
			text: saveFailedSentence(error, __("Could not create the folder")),
			variant: "error",
		})
	}
}

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
	mode.value = "write"
	sopCompany.value = ""
	companyReady.value = !props.sopName
	if (props.sopName) {
		detail.fetch({ name: props.sopName })
		companyLookup.fetch({
			doctype: "SOP Document",
			fieldname: "company",
			filters: { name: props.sopName },
		})
	}
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

// The editor works in HTML. Only a value with no tags at all (an SOP typed
// before the editor existed) is wrapped, once, so its paragraph breaks survive.
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

// An emptied editor reports <p></p>, which is not "no content": the reader
// would show a blank body instead of its empty state.
const contentForSave = (html) => {
	const value = toHtml(html)
	const hasObject = /<(img|hr|table|video|iframe)\b/i.test(value)
	const text = value.replace(/<[^>]*>/g, "").replace(/&nbsp;|\s/g, "")
	return hasObject || text ? value : ""
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
			content: contentForSave(form.content),
			folder: form.folder || "",
		}
		// "" (not missing) is "all companies": a missing company is filled in from
		// the saver's Company permission (frappe update_if_missing). Left out of an
		// edit whose company was never read, so the stored one stays.
		if (companyReady.value) values.company = sopCompany.value || ""
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
				gToast({
					title: __("Attachment failed"),
					text: __(
						"Saved as an unpublished draft without the attachment — open it to retry. ({0})",
						[firstMessage(error)]
					),
					variant: "error",
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

		gToast({
			title: __("Success"),
			text: props.sopName ? __("SOP updated") : __("SOP created"),
			variant: "success",
		})
		emit("saved")
		close()
	} catch (error) {
		console.warn("[SOP] Save failed:", error)
		gToast({
			title: __("Error"),
			text: saveFailedSentence(error, __("Could not save the SOP")),
			variant: "error",
		})
	} finally {
		saving.value = false
	}
}
</script>
