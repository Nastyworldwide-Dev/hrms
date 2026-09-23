<template>
	<GPage>
		<ion-content class="ion-padding">
			<div class="flex flex-col min-h-full w-full">
				<div class="w-full max-w-content-column-lg mx-auto">
					<header
						class="flex flex-row py-3.5 px-4 items-center justify-between border-b-2 border-divider sticky top-0 z-sticky bg-ground"
					>
						<div class="flex flex-row items-center gap-2.5">
							<GIconButton :label="__('Back')" flush @click="goBackOrHome(router)">
								<ChevronLeft class="h-5 w-5" />
							</GIconButton>
							<h2 class="font-sans font-extrabold text-lg tracking-tight text-inkbase">
								{{ __("Profile") }}
							</h2>
						</div>
					</header>

					<div class="flex flex-col p-4">
						<!-- Identity block -->
						<div class="flex flex-row items-center gap-4 pb-5 border-b-2 border-divider">
							<div class="shrink-0">
								<GAvatar
									:image="user.data?.user_image"
									:label="user.data?.first_name"
									:size="72"
								/>
							</div>
							<div class="flex flex-col gap-1 min-w-0">
								<span
									v-if="employee"
									class="font-sans font-extrabold text-screen-title tracking-tight text-inkbase truncate"
									>{{ employee?.data?.employee_name }}</span
								>
								<span v-if="employee" class="g-eyebrow truncate">{{
									employee?.data?.designation
								}}</span>
							</div>
						</div>

						<!-- FOUR GROUPS, not one list (revamp §7).
						     Profile was a single undifferentiated column of nine
						     rows, each hand-built with its own padding, border and
						     hover — 17 of the app's 103 stray pixel values lived
						     here. A person looking for "change my password" had to
						     read all nine.

						     The groups answer four different questions: who am I,
						     where do I work, how does the app behave, and how do I
						     get out. Nothing was removed; the order is now an
						     argument rather than an accident.

						     GListPanel/GListRow, so the padding, the dividers and
						     the 44px targets come from the system and cannot drift
						     again. -->
						<div class="flex flex-col gap-5 mt-2">
							<template v-for="group in groups" :key="group.key">
								<div v-if="group.rows.length" class="flex flex-col gap-2">
									<span class="g-eyebrow">{{ group.title }}</span>
									<GListPanel>
										<GListRow
											v-for="row in group.rows"
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
								</div>
							</template>
						</div>

						<button
							@click="logout"
							class="flex items-center justify-center gap-2 w-full bg-transparent border border-divider rounded-action text-inkbase px-4 py-3.5 font-sans font-extrabold text-card-title mt-7 hover:bg-icon-bg"
						>
							<!-- neutral, not accent (8.14): sign-out wore the same chartreuse the
						     system reserves for the ONE primary action on a screen, and it
						     was the only accented element on Profile — so the loudest thing
						     on the page was the way out of the app. -->
							<LogOut class="w-4 h-4" />
							{{ __("Log Out") }}
						</button>
					</div>
				</div>
			</div>

			<ion-modal
				ref="modal"
				:is-open="isInfoModalOpen"
				@didDismiss="closeInfoModal"
				:initial-breakpoint="1"
				:breakpoints="[0, 1]"
			>
				<ContactInfoSheet
					v-if="selectedItem?.kind === 'contact'"
					:self-data="
						selectedItem.fields.map((field) => {
							const [label, fieldtype] = getFieldInfo(field)
							return {
								fieldname: field,
								value: getFieldValue(field),
								label: label,
								fieldtype: fieldtype,
							}
						})
					"
				/>
				<ProfileInfoModal
					v-else-if="selectedItem"
					:title="selectedItem.title"
					:data="
						selectedItem.fields.map((field) => {
							const [label, fieldtype] = getFieldInfo(field)
							return {
								fieldname: field,
								value: getFieldValue(field),
								label: label,
								fieldtype: fieldtype,
							}
						})
					"
				/>
			</ion-modal>
		</ion-content>
	</GPage>
</template>

<script setup>
import {
	Book,
	ChevronLeft,
	File,
	Info,
	KeyRound,
	LogOut,
	Settings,
	SquareCheck,
	User,
	Users,
} from "lucide-vue-next"
import GPage from "@/components/glass/GPage.vue"
import { computed, inject, ref, watch, onMounted, onBeforeUnmount } from "vue"
import { useListUpdate } from "@/composables/realtime"
import { useRouter } from "vue-router"
import { goBackOrHome } from "@/utils/navigation"
import { IonContent, IonModal } from "@ionic/vue"
import { createDocumentResource, createResource } from "frappe-ui"
import GIconButton from "@/components/glass/GIconButton.vue"
import GAvatar from "@/components/glass/GAvatar.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"

import { showErrorAlert } from "@/utils/dialogs"
import { formatCurrency } from "@/utils/formatters"

import ProfileInfoModal from "@/components/ProfileInfoModal.vue"
import ContactInfoSheet from "@/components/ContactInfoSheet.vue"

import { pendingCountResource } from "@/data/remoteCheckin"
import { isApprover } from "@/data/team"

const DOCTYPE = "Employee"

const socket = inject("$socket")
const session = inject("$session")
const user = inject("$user")
const employee = inject("$employee")
const __ = inject("$translate")

const router = useRouter()

const profileLinks = [
	{
		icon: User,
		title: __("Employee Details"),
		fields: [
			"employee_name",
			"employee_number",
			"gender",
			"date_of_birth",
			"date_of_joining",
			"blood_group",
		],
	},
	{
		icon: File,
		title: __("Company Information"),
		fields: [
			"company",
			"department",
			"designation",
			"branch",
			"grade",
			"reports_to",
			"employment_type",
		],
	},
	{
		icon: Book,
		title: __("Contact Information"),
		kind: "contact",
		fields: ["cell_number", "personal_email", "company_email", "preferred_email"],
	},
]

//: DECLARED BEFORE `groups`, on purpose. A computed's getter does not run at
//: setup, but the script-setup order gate refuses a read above its
//: declaration anyway — and it is right to: the moment somebody makes one of
//: these eager, the screen throws "before initialization" and Ionic is left
//: holding a view with no element. The KPI dashboard learned this the hard
//: way and so did two check-in dialogs this morning.
const pendingApprovalsCount = computed(() => Number(pendingCountResource.data) || 0)

//: Stamped at compile time by vite (`__APP_BUILD__`), the same constant the
//: diagnostics report carries — so the version a person reads off the screen
//: is the version in the report they send.
const buildString = typeof __APP_BUILD__ === "string" ? __APP_BUILD__ : "dev"
//: The PWA version (package.json, SemVer), stamped by vite. "Version
//: 2.0.0-alpha.2 · 2026-09-23 14:02" answers "which version are you on".
const versionString = typeof __APP_VERSION__ === "string" ? __APP_VERSION__ : "dev"

//: FOUR GROUPS. Each answers a different question, which is what makes them
//: groups rather than a divided list: who am I, where do I work, how does the
//: app behave, and how do I get out.
//:
//: Role-gated rows keep the server as the authority — `isApprover` is a
//: RESOURCE, answered by the backend, not a role string read here.
const groups = computed(() => [
	{
		key: "you",
		title: __("You"),
		rows: [
			...profileLinks.map((link) => ({
				key: link.title,
				icon: link.icon,
				label: link.title,
				sublabel: null,
				go: () => openInfoModal(link),
			})),
		],
	},
	{
		key: "work",
		title: __("Work"),
		rows: [
			{
				key: "hr-contacts",
				icon: Users,
				label: __("HR Contacts"),
				sublabel: __("Who to ask, and how to reach them"),
				go: () => router.push({ name: "HRContacts" }),
			},
			// Shown to APPROVERS, never gated on the pending COUNT: count-gating
			// once made this vanish the moment the queue emptied, stranding an
			// approver away from their own decision history.
			...(isApprover.data
				? [
						{
							key: "approvals",
							icon: SquareCheck,
							label: __("Remote Approvals"),
							sublabel: null,
							badge: pendingApprovalsCount.value > 0 ? String(pendingApprovalsCount.value) : null,
							go: () => router.push({ name: "RemoteApprovals" }),
						},
				  ]
				: []),
		],
	},
	{
		key: "app",
		title: __("App"),
		rows: [
			{
				key: "settings",
				icon: Settings,
				// Never gated: this is the only path to the theme switcher and
				// to Change Password, and hiding it behind the push-relay check
				// once locked users out of both.
				label: __("Settings"),
				sublabel: __("Theme, notifications, language"),
				go: () => router.push({ name: "Settings" }),
			},
		],
	},
	{
		key: "account",
		title: __("Account"),
		rows: [
			{
				key: "password",
				icon: KeyRound,
				label: __("Change password"),
				sublabel: null,
				go: () => router.push({ name: "ChangePassword" }),
			},
			{
				key: "about",
				icon: Info,
				// EVERY phone-side defect this month began with "which version
				// are you on". The answer is now on the screen people are
				// already looking at when they report one.
				label: __("About this app"),
				sublabel: __("Version {0} · {1}", [versionString, buildString]),
				go: () => {},
			},
		],
	},
])

const isInfoModalOpen = ref(false)
const selectedItem = ref(null)

const openInfoModal = async (request) => {
	selectedItem.value = request
	isInfoModalOpen.value = true
}

const closeInfoModal = async (_request) => {
	isInfoModalOpen.value = false
	selectedItem.value = null
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

const employeeDocType = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: DOCTYPE },
	auto: true,
})

const getFieldInfo = (fieldname) => {
	// Both resources load async; opening the detail sheet before they resolve
	// used to run .find on null (and deref a null doc below), rendering an
	// error instead of a sheet. Default to safe values until they arrive.
	const field = (employeeDocType.data || []).find((field) => field.fieldname === fieldname)
	return [__(field?.label, null, "Employee"), field?.fieldtype]
}

const getFieldValue = (fieldname) => {
	const doc = employeeDoc.doc
	if (!doc) return ""
	if (fieldname === "employee_number" && !doc[fieldname]) {
		return doc["name"]
	}
	if (fieldname === "reports_to") {
		return reportsToName.data || doc[fieldname]
	}
	return doc[fieldname]
}

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
