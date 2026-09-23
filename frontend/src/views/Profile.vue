<template>
	<GPage>
		<!-- The one header (alpha.5), in place of a hand-drawn hairline bar. -->
		<ShellHeader :title="__('You')" />
		<ion-content class="ion-padding g-page__content">
			<div class="flex flex-col min-h-full w-full">
				<div class="w-full max-w-content-column-lg mx-auto lg:mx-0">
					<div class="flex flex-col gap-5 p-4">
						<!-- Who I am (audit-pages §4 "You"): name, role, and where. -->
						<div class="flex flex-row items-center gap-4">
							<div class="shrink-0">
								<GAvatar
									:image="user.data?.user_image"
									:label="user.data?.first_name"
									:size="72"
								/>
							</div>
							<div class="flex flex-col gap-1 min-w-0">
								<span
									class="font-sans font-extrabold text-screen-title tracking-tight text-inkbase break-words"
									>{{ employee?.data?.employee_name }}</span
								>
								<span v-if="roleLine" class="text-caption text-ink-600">{{ roleLine }}</span>
							</div>
						</div>

						<!-- On the page, not in two sheets (PAGE-23); the shift pattern
						     by owner ruling 3 (23 Sep). Each line only when known. -->
						<div v-if="managerName || shiftName" class="flex flex-col gap-1">
							<p v-if="managerName" class="text-card-title font-normal text-ink">
								{{ __("Your manager is {0}", [managerName]) }}
							</p>
							<p v-if="shiftName" class="text-card-title font-normal text-ink">
								{{ __("Your shift: {0}", [shiftName]) }}
							</p>
						</div>

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

						<!-- How the app behaves: inline, the Settings page is cut (S-DUP). -->
						<div class="flex flex-col gap-2">
							<span class="text-card-title text-ink">{{ __("Theme") }}</span>
							<GSegmented
								:buttons="THEME_BUTTONS"
								:model-value="theme.mode"
								:label="__('Theme')"
								@update:model-value="setTheme"
							/>
						</div>

						<!-- Only where the site can push: a switch that cannot work is
						     not offered (audit-pages §4, "actionable only"). -->
						<div v-if="canPush" class="g-switch-row">
							<Switch
								size="md"
								:label="__('Notifications')"
								:description="__('On this phone')"
								:model-value="pushOn"
								:disabled="pushBusy"
								@update:model-value="togglePush"
							/>
						</div>

						<!-- Owner ruling, 23 Sep 2026: check-in / check-out reminders,
						     the person's own on/off, ON by default. -->
						<div class="g-switch-row">
							<Switch
								size="md"
								:label="__('Shift reminders')"
								:description="__('A nudge if you forget to check in or out')"
								:model-value="remindersOn"
								:disabled="setReminders.loading"
								@update:model-value="toggleReminders"
							/>
						</div>

						<button
							@click="logout"
							class="g-focusable flex items-center justify-center gap-2 w-full bg-transparent border border-divider rounded-action text-inkbase px-4 py-3.5 font-sans font-extrabold text-card-title hover:bg-icon-bg"
						>
							<!-- neutral, not accent (8.14): the way out is not the
							     loudest thing on the page. -->
							<LogOut class="w-4 h-4" />
							{{ __("Log out") }}
						</button>

						<p class="text-caption text-ink-600 text-center">
							{{ __("Version {0} · {1}", [versionString, buildString]) }}
						</p>
					</div>
				</div>
			</div>

			<GModal :is-open="detailsOpen" :title="__('Your details')" @did-dismiss="detailsOpen = false">
				<ProfileInfoModal v-if="detailsOpen" :data="detailRows" />
			</GModal>
		</ion-content>
	</GPage>
</template>

<script setup>
import { KeyRound, LogOut, SquareCheck, User } from "lucide-vue-next"
import GPage from "@/components/glass/GPage.vue"
import { computed, inject, ref, watch, onMounted, onBeforeUnmount } from "vue"
import { useListUpdate } from "@/composables/realtime"
import { useRouter } from "vue-router"
import { IonContent } from "@ionic/vue"
import GModal from "@/components/glass/GModal.vue"
import { Switch, createDocumentResource, createResource, toast } from "frappe-ui"
import ShellHeader from "@/components/ShellHeader.vue"
import GAvatar from "@/components/glass/GAvatar.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GSegmented from "@/components/glass/GSegmented.vue"

import { showErrorAlert } from "@/utils/dialogs"
import { formatCurrency } from "@/utils/formatters"

import ProfileInfoModal from "@/components/ProfileInfoModal.vue"

import { pendingCountResource } from "@/data/remoteCheckin"
import { isApprover } from "@/data/team"
import { theme, setTheme, THEME_MODES } from "@/data/theme"
import {
	arePushNotificationsEnabled,
	enablePushNotifications as requestPushEnable,
} from "@/data/notifications"

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

const pendingApprovalsCount = computed(() => Number(pendingCountResource.data) || 0)

//: "Version 2.0.0-alpha.2 · 2026-09-23 14:02" — answers "which version are
//: you on" in the report a person sends.
const buildString = typeof __APP_BUILD__ === "string" ? __APP_BUILD__ : "dev"
const versionString = typeof __APP_VERSION__ === "string" ? __APP_VERSION__ : "dev"

//: Role-gated rows keep the server as the authority — `isApprover` is a
//: RESOURCE answered by the backend, not a role string read here.
const rows = computed(() => [
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
	...(isApprover.data
		? [
				{
					key: "approvals",
					icon: SquareCheck,
					label: __("Approvals"),
					sublabel: null,
					badge: pendingApprovalsCount.value > 0 ? String(pendingApprovalsCount.value) : null,
					go: () => router.push({ name: "Approvals" }),
				},
		  ]
		: []),
	{
		key: "password",
		icon: KeyRound,
		label: __("Change password"),
		sublabel: null,
		go: () => router.push({ name: "ChangePassword" }),
	},
])

// __("Light"), __("Dark"), __("System")
const THEME_LABELS = { light: "Light", dark: "Dark", system: "System" }
const THEME_BUTTONS = THEME_MODES.map((mode) => ({ key: mode, label: __(THEME_LABELS[mode]) }))

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
				toast({
					title: __("Notifications are blocked"),
					text: __("Allow them for this site in your browser settings."),
					icon: "alert-circle",
					position: "bottom-center",
				})
		} else {
			await window.frappePushNotification.disableNotification()
			pushOn.value = false
			// Parity with the Settings page this replaced (review of 518a541e7).
			toast({
				title: __("Notifications are off"),
				text: __("This phone won't be sent any."),
				icon: "check-circle",
				position: "bottom-center",
			})
		}
		console.info("[You] notifications", pushOn.value ? "on" : "off")
	} catch (error) {
		// Browser Notification API errors, not server refusals: calm copy.
		console.error("[You] notification toggle failed:", error)
		toast({
			title: __("Notifications didn't change"),
			text: __("Try again in a moment."),
			icon: "alert-circle",
			position: "bottom-center",
		})
		pushOn.value = !on
	} finally {
		pushBusy.value = false
	}
}

const remindersOn = ref(true)
createResource({
	url: "hrms.utils.shift_reminders.get_shift_reminders",
	auto: true,
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
		toast({
			title: __("Reminders didn't change"),
			text: __("Try again in a moment."),
			icon: "alert-circle",
			position: "bottom-center",
		})
	},
})

function toggleReminders(on) {
	remindersOn.value = on
	setReminders.submit({ enabled: on ? 1 : 0 })
}

const employeeDoc = createDocumentResource({
	doctype: DOCTYPE,
	name: employee.data.name,
	fields: "*",
	auto: true,
	transform: (data) => {
		data.ctc = formatCurrency(data.ctc, data.salary_currency)
		return data
	},
})

const roleLine = computed(() => {
	const doc = employeeDoc.doc || employee.data || {}
	const where = [doc.department, doc.branch].filter(Boolean).join(" · ")
	return [doc.designation, where].filter(Boolean).join(" · ")
})
const shiftName = computed(() => employeeDoc.doc?.default_shift || null)

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
		const msg = "An error occurred while attempting to log out!"
		console.error(msg, e)
		showErrorAlert(msg)
	}
}

const onRemoteCheckinEvent = () => {
	pendingCountResource.reload()
}

// Realtime: reload this employee's own doc on its updates. Via useListUpdate so
// the handler detaches by reference — the old socket.off("list_update") with no
// handler ref tore down every OTHER component's list_update listener too — and
// rejoins on reconnect.
useListUpdate(socket, DOCTYPE, (name) => {
	if (name === employee.data.name) employeeDoc.reload()
})

onMounted(() => {
	socket.on("hrms:remote_checkin_request", onRemoteCheckinEvent)
	pendingCountResource.fetch()
})

onBeforeUnmount(() => {
	socket.off("hrms:remote_checkin_request", onRemoteCheckinEvent)
})
</script>
