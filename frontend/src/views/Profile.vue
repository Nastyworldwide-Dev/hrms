<template>
	<GPage>
		<!-- The one header (alpha.5), in place of a hand-drawn hairline bar. -->
		<ShellHeader :title="__('You')" />
		<ion-content class="ion-padding g-page__content">
			<div class="flex flex-col min-h-full w-full">
				<div class="w-full max-w-content-column-lg mx-auto">
					<div class="flex flex-col gap-5 p-4">
						<!-- Who I am (audit-pages §4 "You"): name, role, and where. -->
						<!-- As iOS Settings draws the account (alpha.8, measured): a 60 pt
						     circle and the name beside it, in one grouped row. -->
						<div class="g-form-group g-account">
							<div class="g-account__row">
								<button
									type="button"
									class="g-account__avatar-btn"
									:class="{ busy: photoUploadBusy }"
									:aria-label="__('Change profile photo')"
									:aria-disabled="photoUploadBusy"
									:aria-describedby="photoUploadBusy ? 'photo-saving' : undefined"
									@click="openPhotoActions"
								>
									<GAvatar
										:image="user.data?.user_image"
										:label="user.data?.first_name"
										:size="60"
										round
									/>
									<span v-if="photoUploadBusy" class="g-account__spinner" aria-hidden="true" />
									<span v-else class="g-account__badge" aria-hidden="true">
										<Camera class="h-3.5 w-3.5" />
									</span>
								</button>
								<div class="g-account__text">
									<!-- a login with no Employee (an Attendance Report Viewer) is named by its account -->
									<span class="g-account__name">{{
										employee?.data?.employee_name || user.data?.full_name
									}}</span>
									<span v-if="roleLine" class="g-account__sub">{{ roleLine }}</span>
									<span
										v-if="photoUploadBusy"
										id="photo-saving"
										class="g-account__sub"
										role="status"
										>{{ __("Saving your photo…") }}</span
									>
									<span v-if="photoError" class="g-account__error" role="alert">
										{{ photoError }}
										<button
											v-if="photoRetry"
											type="button"
											class="g-account__retry g-focusable"
											:disabled="photoUploadBusy"
											@click="retryPhoto"
										>
											{{ __("Try again") }}
										</button>
									</span>
								</div>
							</div>
							<!-- On the page, not in sheets (PAGE-23; shift pattern by owner
							     ruling 3, 23 Sep), now as label/value rows of the same group
							     instead of loose lines between groups (alpha.8). -->
							<!-- Always both rows (alpha.8 r3: they appeared once the record
							     loaded and pushed the page down 44 pt). "None" when unset, as
							     iOS Settings says it; a placeholder while loading. -->
							<!-- A failed read says so, with Try again, instead of two
							     placeholders that never resolve (alpha.12 C2). -->
							<!-- None of this exists for a login the server found no Employee
							     for: no "could not load" that Try again can never fix. -->
							<template v-if="!noEmployee">
								<ResourceError :resource="employeeDoc.get" :what="__('your details')" />
								<div
									v-if="!employeeDoc.get.error"
									v-value-row
									class="g-form-row g-form-row--readonly"
								>
									<span class="g-form-row__label">{{ __("Manager") }}</span>
									<GSkeleton v-if="managerLoading" width="96px" height="11px" />
									<router-link
										v-else-if="employeeDoc.doc?.reports_to"
										:to="{ name: 'OrgChart', query: { employee: employeeDoc.doc.reports_to } }"
										class="g-form-row__value g-form-row__link"
									>
										{{ managerName || __("None") }}
										<span class="g-form-row__chevron">
											<ChevronRight class="h-4 w-4" aria-hidden="true" />
										</span>
									</router-link>
									<span v-else class="g-form-row__value">{{ __("None") }}</span>
								</div>
								<div
									v-if="!employeeDoc.get.error"
									v-value-row
									class="g-form-row g-form-row--readonly"
								>
									<span class="g-form-row__label">{{ __("Shift") }}</span>
									<GSkeleton v-if="!employeeDoc.doc" width="96px" height="11px" />
									<span v-else class="g-form-row__value">{{ shiftName || __("None") }}</span>
								</div>
							</template>
						</div>
						<p v-if="!noEmployee && photoCompany" class="g-form-footer">
							{{ __("Your photo is seen by people in {0}.").replace("{0}", photoCompany) }}
						</p>

						<!-- Details and work: one row, one sheet (was three rows). -->
						<GListPanel>
							<GListRow
								v-for="row in rows"
								:key="row.key"
								:label="row.label"
								:sublabel="row.sublabel"
								@click="row.go()"
							>
								<template #icon>
									<component :is="row.icon" class="g-row-icon" />
								</template>
								<template v-if="row.badge" #badge>
									<GBadge variant="accent">{{ row.badge }}</GBadge>
								</template>
							</GListRow>
						</GListPanel>

						<!-- How the app behaves (alpha.6 B3): ONE grouped list, iOS Settings
						     style. Appearance is a menu row (HIG Pickers: a short list is a
						     pop-up button); each on/off is a switch TRAILING its row (HIG
						     Toggles); what they do is the group footer, not a floating line. -->
						<section class="g-form-section">
							<div class="g-form-group g-you-settings">
								<label class="g-form-row">
									<span class="g-form-row__label">{{ __("Appearance") }}</span>
									<GSelect
										:options="THEME_OPTIONS"
										:model-value="theme.mode"
										:aria-label="__('Appearance')"
										@update:model-value="setTheme"
									/>
								</label>
								<!-- Only where the site can push: a switch that cannot work is
								     not offered (audit-pages §4, "actionable only"). -->
								<div v-if="canPush" class="g-form-row">
									<span class="g-form-row__label">{{ __("Notifications") }}</span>
									<GSwitch
										class="g-form-row__switch"
										:aria-label="__('Notifications')"
										:model-value="pushOn"
										:disabled="pushBusy"
										@update:model-value="togglePush"
									/>
								</div>
								<!-- Owner ruling, 23 Sep 2026: check-in / check-out reminders,
								     the person's own on/off, ON by default. -->
								<div v-if="!noEmployee" class="g-form-row">
									<span class="g-form-row__label">{{ __("Shift reminders") }}</span>
									<GSwitch
										class="g-form-row__switch"
										:aria-label="__('Shift reminders')"
										:model-value="remindersOn"
										:disabled="setReminders.loading"
										@update:model-value="toggleReminders"
									/>
								</div>
							</div>
							<p v-if="canPush || !noEmployee" class="g-form-footer">
								{{
									canPush && noEmployee
										? __("Notifications arrive on this phone.")
										: canPush
										? __(
												"Notifications arrive on this phone. Shift reminders nudge you if you forget to check in or out."
										  )
										: __("Shift reminders nudge you if you forget to check in or out.")
								}}
							</p>
						</section>

						<!-- The way out: a destructive row, red text (HIG Buttons), never
						     the loudest thing on the page. The version is its footer, as
						     iOS puts "About" facts (alpha.9 D9: not a loose line). -->
						<section class="g-form-section">
							<div class="g-form-group">
								<button
									type="button"
									class="g-form-row g-form-row--action g-form-row--destructive"
									@click="logout"
								>
									{{ __("Log out") }}
								</button>
							</div>
							<p class="g-form-footer g-form-footer--center">
								{{
									releaseName
										? __("Nadi {0} · {1}", [versionString, __(releaseName)])
										: __("Nadi {0}", [versionString])
								}}
							</p>
						</section>
					</div>
				</div>
			</div>

			<GModal
				:is-open="detailsOpen"
				:title="__('Your details')"
				@did-dismiss="detailsOpen = false"
			>
				<ProfileInfoModal v-if="detailsOpen" :data="detailRows" />
			</GModal>

			<!-- Photo actions menu -->
			<GActionSheet
				:is-open="photoActionsOpen"
				:title="__('Profile photo')"
				:actions="photoActions"
				@select="onPhotoAction"
				@did-dismiss="photoActionsOpen = false"
			/>

			<!-- Photo crop and upload -->
			<PhotoSheet
				:is-open="photoCropOpen"
				:file="selectedPhotoFile"
				:saving="photoUploadBusy"
				@use="onPhotoUse"
				@error="onPhotoUndecodable"
				@did-dismiss="photoCropOpen = false"
			/>

			<GConfirm
				:is-open="removeConfirmOpen"
				:title="__('Remove your photo?')"
				:confirm-label="__('Remove')"
				destructive
				:pending="photoUploadBusy"
				@confirm="removePhoto"
				@cancel="removeConfirmOpen = false"
			/>

			<!-- Hidden file inputs for photo pick/capture -->
			<input ref="fileInputChoose" type="file" accept="image/*" hidden @change="onFileSelect" />
			<input
				ref="fileInputCapture"
				type="file"
				accept="image/*"
				capture="user"
				hidden
				@change="onFileSelect"
			/>
		</ion-content>
	</GPage>
</template>

<script setup>
import { Camera, ChevronRight, Image as ImageIcon, KeyRound, Trash2, User } from "lucide-vue-next"
import GPage from "@/components/glass/GPage.vue"
import { computed, inject, ref, watch } from "vue"
import { useListUpdate } from "@/composables/realtime"
import { useRouter } from "vue-router"
import { IonContent } from "@ionic/vue"
import GModal from "@/components/glass/GModal.vue"
import GConfirm from "@/components/glass/GConfirm.vue"
import GActionSheet from "@/components/glass/GActionSheet.vue"
import PhotoSheet from "@/components/PhotoSheet.vue"
import { createDocumentResource, createResource } from "frappe-ui"
import { gToast } from "@/components/glass/toast"
import GSwitch from "@/components/glass/GSwitch.vue"
import ShellHeader from "@/components/ShellHeader.vue"
import GAvatar from "@/components/glass/GAvatar.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import ResourceError from "@/components/ResourceError.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GSelect from "@/components/glass/GSelect.vue"

import { formatCurrency } from "@/utils/formatters"
import { nowResource } from "@/data/now"
import { userResource } from "@/data/user"

import ProfileInfoModal from "@/components/ProfileInfoModal.vue"

import { theme, setTheme, THEME_MODES } from "@/data/theme"
import {
	arePushNotificationsEnabled,
	enablePushNotifications as requestPushEnable,
} from "@/data/notifications"
import { checkPick } from "@/utils/photoCrop"

const DOCTYPE = "Employee"

const socket = inject("$socket")
const session = inject("$session")
const user = inject("$user")
const employee = inject("$employee")
const __ = inject("$translate")

const router = useRouter()

//: ONE sheet for the employee record (audit-pages §4: was three rows and
//: three sheets). The manager is on the page itself, so not repeated here.
//: [field, plain label, how to show it]. Labels live here, not in
//: the fillable-fields endpoint: that list is the fields a FORM can fill, and it leaves
//: out links the employee cannot open (department, designation, branch,
//: grade, employment type), which left five rows with no label (live audit
//: 23 Sep). A read-only sheet names its own rows.
const DETAILS = [
	["employee_number", __("Employee number"), "Data"],
	["company", __("Company"), "Data"],
	["department", __("Department"), "Data"],
	["designation", __("Job title"), "Data"],
	["branch", __("Branch"), "Data"],
	["grade", __("Grade"), "Data"],
	["employment_type", __("Employment type"), "Data"],
	["date_of_joining", __("Joined"), "Date"],
	["cell_number", __("Mobile"), "Data"],
	["company_email", __("Work email"), "Data"],
	["personal_email", __("Personal email"), "Data"],
	["prefered_email", __("Preferred email"), "Data"],
	["date_of_birth", __("Date of birth"), "Date"],
	["gender", __("Gender"), "Data"],
	["blood_group", __("Blood group"), "Data"],
]
const detailsOpen = ref(false)

//: "Version 2.0.0-alpha.2 · 2026-09-23 14:02" — answers "which version are
//: you on" in the report a person sends.
//: The release's name beside its number; no date or time (owner, 27 Sep 2026).
const releaseName = typeof __APP_RELEASE_NAME__ === "string" ? __APP_RELEASE_NAME__ : ""
const versionString = typeof __APP_VERSION__ === "string" ? __APP_VERSION__ : "dev"

//: You is only you (alpha.14 O): Approvals moved to More → Your team.
//: The server answered and found no Employee for this login (navigationGate
//: lets an Attendance Report Viewer in without one): nothing here reads one.
const noEmployee = computed(() => employee.fetched && !employee.data)

const rows = computed(() => [
	...(noEmployee.value
		? []
		: [
				{
					key: "details",
					icon: User,
					label: __("Your details"),
					sublabel: null,
					go: () => {
						console.info("[You] opening details")
						detailsOpen.value = true
					},
				},
		  ]),
	{
		key: "password",
		icon: KeyRound,
		label: __("Change password"),
		sublabel: null,
		go: () => router.push({ name: "ChangePassword" }),
	},
])

// __("Light"), __("Dark"), __("System")
const THEME_LABELS = { light: "Light", dark: "Dark", system: "Automatic" }
//: iOS names this "Appearance: Light / Dark / Automatic".
const THEME_OPTIONS = THEME_MODES.map((mode) => ({ value: mode, label: __(THEME_LABELS[mode]) }))

//: Offered only where the site can push (push relay configured and the
//: server allows it); otherwise there is nothing the switch could do.
const canPush = computed(
	() => !!(window.frappe?.boot?.push_relay_server_url && arePushNotificationsEnabled.data)
)
const pushOn = ref(!!window.frappePushNotification?.isNotificationEnabled?.())
const pushBusy = ref(false)

async function togglePush(on) {
	pushBusy.value = true
	try {
		if (on) {
			const data = await requestPushEnable()
			pushOn.value = !!data?.permission_granted
			if (!pushOn.value)
				gToast({
					title: __("Notifications are blocked"),
					text: __("Allow them for this site in your browser settings."),
					variant: "error",
				})
		} else {
			await window.frappePushNotification.disableNotification()
			pushOn.value = false
			// Parity with the Settings page this replaced (review of 518a541e7).
			gToast({
				title: __("Notifications are off"),
				text: __("This phone won't be sent any."),
				variant: "success",
			})
		}
		console.info("[You] notifications", pushOn.value ? "on" : "off")
	} catch (error) {
		// Browser Notification API errors, not server refusals: calm copy.
		console.error("[You] notification toggle failed:", error)
		gToast({
			title: __("Notifications didn't change"),
			text: __("Try again in a moment."),
			variant: "error",
		})
		pushOn.value = !on
	} finally {
		pushBusy.value = false
	}
}

const remindersOn = ref(true)
//: Reminders are per Employee: no auto read for a login the gate let in
//: without one (it 403'd into a "You can't open this" toast).
createResource({
	url: "hrms.utils.shift_reminders.get_shift_reminders",
	auto: !noEmployee.value,
	onSuccess(data) {
		remindersOn.value = !!data
	},
})
const setReminders = createResource({
	url: "hrms.utils.shift_reminders.set_shift_reminders",
	onSuccess(data) {
		remindersOn.value = !!data
		console.info("[You] shift reminders", remindersOn.value ? "on" : "off")
	},
	onError(error) {
		console.error("[You] shift reminders toggle failed:", error)
		remindersOn.value = !remindersOn.value
		gToast({
			title: __("Reminders didn't change"),
			text: __("Try again in a moment."),
			variant: "error",
		})
	},
})

function toggleReminders(on) {
	remindersOn.value = on
	setReminders.submit({ enabled: on ? 1 : 0 })
}

//: The employee record may not be read yet: the navigation gate lets a person
//: through when that read failed or they are offline ("employee unknown").
//: Built from `employee.data.name` directly, this threw during setup and You
//: never mounted (alpha.14, states audit). Without an employee it is a failed
//: read like any other, and Try again reads the employee first.
function detailsResource() {
	if (employee.data?.name)
		return createDocumentResource({
			doctype: DOCTYPE,
			name: employee.data?.name,
			fields: "*",
			auto: true,
			transform: (data) => {
				data.ctc = formatCurrency(data.ctc, data.salary_currency)
				return data
			},
		})
	console.warn("[You] employee not read yet; details wait for Try again")
	return {
		doc: null,
		get: {
			error: new Error("employee unknown"),
			loading: false,
			reload: () => employee.reload().then(() => location.reload()),
		},
		reload: () => employee.reload().then(() => location.reload()),
	}
}
const employeeDoc = detailsResource()

const photoCompany = computed(() => employeeDoc.doc?.company || employee.data?.company || "")
const roleLine = computed(() => {
	const doc = employeeDoc.doc || employee.data || {}
	const where = [doc.department, doc.branch].filter(Boolean).join(" · ")
	return [doc.designation, where].filter(Boolean).join(" · ")
})
// Today's shift as Home reads it (an assignment, else the default), so the two
// screens never disagree: You said "None" beside Home's "Morning Shift" for
// anyone on an assignment with no default (UX review 21 Oct 2026, F3).
const shiftName = computed(
	() => nowResource.data?.shift?.shift || employeeDoc.doc?.default_shift || null
)
// reload, not fetch-if-empty: the cache may hold another day's shift
nowResource.reload()?.catch?.((e) => console.warn("[You] today's shift unavailable", e))

const reportsToName = createResource({
	url: "hrms.api.get_reports_to_employee_name",
})

watch(
	() => employeeDoc.doc?.reports_to,
	(reports_to) => {
		if (reports_to) {
			reportsToName.submit({ employee: reports_to })
		}
	}
)

const managerName = computed(() => (employeeDoc.doc?.reports_to ? reportsToName.data : null))
//: Until the record says who, and then until the name is read.
const managerLoading = computed(
	() =>
		!employeeDoc.doc ||
		Boolean(employeeDoc.doc.reports_to && !reportsToName.data && !reportsToName.error)
)

const getFieldValue = (fieldname) => {
	const doc = employeeDoc.doc
	if (!doc) return ""
	if (fieldname === "employee_number" && !doc[fieldname]) {
		return doc["name"]
	}
	return doc[fieldname]
}

//: Only rows with a value: an empty field is left out, not shown as "-".
const detailRows = computed(() =>
	DETAILS.map(([fieldname, label, fieldtype]) => ({
		fieldname,
		label,
		fieldtype,
		value: getFieldValue(fieldname),
	})).filter((row) => row.value !== null && row.value !== undefined && row.value !== "")
)

const logout = async () => {
	try {
		await session.logout.submit()
	} catch (e) {
		console.error("[Profile] log out failed", e)
		// The app's own banner (alpha.13): Ionic's alert loaded 45 KB for
		// everyone to show this one message.
		gToast({
			title: __("Could not log out"),
			text: __("Check your connection and try again."),
			variant: "error",
		})
	}
}

// Realtime: reload this employee's own doc on its updates. Via useListUpdate so
// the handler detaches by reference — the old socket.off("list_update") with no
// handler ref tore down every OTHER component's list_update listener too — and
// rejoins on reconnect.
useListUpdate(socket, DOCTYPE, (name) => {
	if (name === employee.data?.name) employeeDoc.reload()
})

//: Photo upload UI state and actions
const photoActionsOpen = ref(false)
const photoCropOpen = ref(false)
const photoUploadBusy = ref(false)
const photoError = ref("")
const photoRetry = ref("")
const removeConfirmOpen = ref(false)
const selectedPhotoFile = ref(null)
const fileInputChoose = ref(null)
const fileInputCapture = ref(null)

const photoActions = computed(() => {
	const actions = [
		{
			key: "choose",
			label: __("Choose photo"),
			icon: ImageIcon,
		},
		{
			key: "take",
			label: __("Take photo"),
			icon: Camera,
		},
	]
	if (user.data?.user_image) {
		actions.push({
			key: "remove",
			label: __("Remove photo"),
			icon: Trash2,
			destructive: true,
		})
	}
	return actions
})

function openPhotoActions() {
	if (photoUploadBusy.value) return
	photoError.value = ""
	photoActionsOpen.value = true
}

function onPhotoAction(key) {
	if (key === "choose") {
		fileInputChoose.value?.click()
	} else if (key === "take") {
		fileInputCapture.value?.click()
	} else if (key === "remove") {
		photoActionsOpen.value = false
		removeConfirmOpen.value = true
	}
}

function onFileSelect(e) {
	const file = e.target.files?.[0]
	e.target.value = ""

	if (!file) return

	photoActionsOpen.value = false
	photoError.value = ""
	photoRetry.value = ""

	// Check file size and type
	const err = checkPick(file)
	if (err === "too_big") {
		photoError.value = __("This photo is over 5 MB. Pick a smaller one.")
		console.info("[profile] photo too_big")
		return
	} else if (err === "not_image") {
		photoError.value = __("That file isn't a photo. Pick a JPEG or PNG.")
		console.info("[profile] photo not_image")
		return
	}

	// Open crop sheet
	selectedPhotoFile.value = file
	photoCropOpen.value = true
	console.info("[profile] photo selected, opening crop")
}

function onPhotoUndecodable() {
	photoCropOpen.value = false
	photoError.value = __("That file isn't a photo. Pick a JPEG or PNG.")
	console.info("[profile] photo undecodable")
}

const setPhotoResource = createResource({
	url: "hrms.api.profile_photo.set_photo",
})

async function onPhotoUse(dataUrl) {
	photoUploadBusy.value = true
	photoError.value = ""
	photoRetry.value = dataUrl

	try {
		await setPhotoResource.submit({ image: dataUrl })
		gToast({
			title: __("Photo updated"),
			variant: "success",
		})
		console.info("[profile] photo uploaded")
		photoRetry.value = ""
		photoCropOpen.value = false
		userResource.reload()
	} catch (error) {
		console.error("[profile] photo upload failed:", error)
		photoCropOpen.value = false
		photoError.value = __("Couldn't save your photo. Try again.")
	} finally {
		photoUploadBusy.value = false
	}
}

function retryPhoto() {
	if (photoRetry.value) onPhotoUse(photoRetry.value)
}

const removePhotoResource = createResource({
	url: "hrms.api.profile_photo.remove_photo",
})

async function removePhoto() {
	photoUploadBusy.value = true
	photoError.value = ""
	photoRetry.value = ""

	try {
		await removePhotoResource.submit({})
		gToast({
			title: __("Photo removed"),
			variant: "success",
		})
		console.info("[profile] photo removed")
		removeConfirmOpen.value = false
		userResource.reload()
	} catch (error) {
		console.error("[profile] photo remove failed:", error)
		removeConfirmOpen.value = false
		photoError.value = __("Couldn't remove your photo. Try again.")
	} finally {
		photoUploadBusy.value = false
	}
}
</script>

<style scoped>
.g-account__avatar-btn {
	position: relative;
	flex: none;
	width: 60px;
	height: 60px;
	padding: 0;
	border: 0;
	border-radius: 50%;
	background: transparent;
	cursor: pointer;
}
.g-account__avatar-btn.busy {
	opacity: 0.5;
}
.g-account__badge {
	position: absolute;
	right: -2px;
	bottom: -2px;
	width: 22px;
	height: 22px;
	border-radius: 50%;
	display: grid;
	place-items: center;
	background: var(--g-ink);
	color: var(--g-bg);
}
.g-account__spinner {
	position: absolute;
	inset: 18px;
	border: 2px solid var(--g-ink2);
	border-top-color: transparent;
	border-radius: 50%;
	animation: g-photo-spin 0.8s linear infinite;
}
@media (prefers-reduced-motion: reduce) {
	.g-account__spinner {
		animation: none;
	}
}
.g-account__retry {
	border: 0;
	background: transparent;
	padding: 0 4px;
	min-height: 44px;
	color: inherit;
	font: inherit;
	text-decoration: underline;
	cursor: pointer;
}
@keyframes g-photo-spin {
	to {
		transform: rotate(360deg);
	}
}
.g-account__error {
	font-size: 0.8125rem;
	line-height: 1.125rem;
	color: var(--g-danger-ink);
}
.g-form-row__link {
	display: inline-flex;
	align-items: center;
	gap: 2px;
	color: inherit;
	text-decoration: none;
}
</style>
