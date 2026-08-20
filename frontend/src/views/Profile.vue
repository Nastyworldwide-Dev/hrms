<template>
	<GPage>
		<ion-content class="ion-padding">
			<div class="flex flex-col h-screen w-screen bg-ground">
				<div class="w-full max-w-[620px] mx-auto">
					<header
						class="flex flex-row bg-ground py-3.5 px-4 items-center justify-between border-b-2 border-divider sticky top-0 z-10"
					>
						<div class="flex flex-row items-center gap-2.5">
							<Button variant="ghost" class="!pl-0 hover:bg-transparent" @click="router.back()">
								<FeatherIcon name="arrow-left" class="h-5 w-5" />
							</Button>
							<h2 class="font-sans font-extrabold text-lg tracking-tight text-inkbase">
								{{ __("Profile") }}
							</h2>
						</div>
					</header>

					<div class="flex flex-col p-4">
						<!-- Identity block -->
						<div class="flex flex-row items-center gap-4 pb-5 border-b-2 border-divider">
							<div class="shrink-0">
								<img
									v-if="user.data.user_image"
									class="h-[72px] w-[72px] object-cover grayscale"
									:src="user.data.user_image"
									:alt="user.data.first_name"
								/>
								<div
									v-else
									class="flex items-center justify-center bg-ink-300 uppercase font-sans font-extrabold text-ink-700 h-[72px] w-[72px] text-2xl"
								>
									{{ user.data.first_name[0] }}
								</div>
							</div>
							<div class="flex flex-col gap-1 min-w-0">
								<span
									v-if="employee"
									class="font-sans font-extrabold text-screen-title tracking-tight text-inkbase truncate"
									>{{ employee?.data?.employee_name }}</span
								>
								<span
									v-if="employee"
									class="text-micro-label uppercase text-ink-600 truncate"
									>{{ employee?.data?.designation }}</span
								>
							</div>
						</div>

						<!-- Profile Links -->
						<div class="flex flex-col mt-2">
							<div
								class="flex flex-row cursor-pointer p-4 pl-0.5 items-center justify-between border-b border-divider hover:bg-inkbase/[0.04]"
								v-for="link in profileLinks"
								:key="link.title"
								@click="openInfoModal(link)"
							>
								<div class="flex flex-row items-center gap-3 grow">
									<FeatherIcon :name="link.icon" class="h-[18px] w-[18px] text-inkbase" />
									<div class="text-button-label text-inkbase">
										{{ link.title }}
									</div>
								</div>
								<FeatherIcon name="chevron-right" class="h-[18px] w-[18px] text-ink-600" />
							</div>

							<!-- HR Contacts -->
							<router-link
								:to="{ name: 'HRContacts' }"
								class="flex flex-row cursor-pointer p-4 pl-0.5 items-center justify-between border-b border-divider hover:bg-inkbase/[0.04]"
							>
								<div class="flex flex-row items-center gap-3 grow">
									<FeatherIcon name="users" class="h-[18px] w-[18px] text-inkbase" />
									<div class="text-button-label text-inkbase">
										{{ __("HR Contacts") }}
									</div>
								</div>
								<FeatherIcon name="chevron-right" class="h-[18px] w-[18px] text-ink-600" />
							</router-link>

							<!-- Remote Approvals. Shown to APPROVERS (isApprover — HR,
							     managers, named approvers), never gated on the pending
							     COUNT: count-gating once made the entry vanish the moment
							     the queue emptied, stranding an approver away from their
							     decision History. A normal employee, whom no approval work
							     can ever reach, sees no approvals surface at all. -->
							<router-link
								v-if="isApprover.data"
								:to="{ name: 'RemoteApprovals' }"
								class="flex flex-row cursor-pointer p-4 pl-0.5 items-center justify-between border-b border-divider hover:bg-inkbase/[0.04]"
							>
								<div class="flex flex-row items-center gap-3 grow">
									<FeatherIcon name="check-square" class="h-[18px] w-[18px] text-inkbase" />
									<div class="text-button-label text-inkbase">
										{{ __("Remote Approvals") }}
									</div>
								</div>
								<div class="flex flex-row items-center gap-2">
									<span
										v-if="pendingApprovalsCount > 0"
										class="inline-flex bg-accent text-ground text-caption font-sans font-extrabold px-1.5 py-0.5"
									>
										{{ pendingApprovalsCount }}
									</span>
									<FeatherIcon name="chevron-right" class="h-[18px] w-[18px] text-ink-600" />
								</div>
							</router-link>

							<!-- Settings. Never gated: this screen also holds the theme switcher
							     and the only path to Change Password, so hiding it behind the
							     push-relay check (the old v-if) locked every user out of both
							     on sites with no push relay configured. AppSettings itself
							     degrades the push toggle when the relay is absent. -->
							<router-link
								:to="{ name: 'Settings' }"
								class="flex flex-row cursor-pointer p-4 pl-0.5 items-center justify-between border-b border-divider hover:bg-inkbase/[0.04]"
							>
								<div class="flex flex-row items-center gap-3 grow">
									<FeatherIcon name="settings" class="h-[18px] w-[18px] text-inkbase" />
									<div class="text-button-label text-inkbase">
										{{ __("Settings") }}
									</div>
								</div>
								<FeatherIcon name="chevron-right" class="h-[18px] w-[18px] text-ink-600" />
							</router-link>
						</div>

						<button
							@click="logout"
							class="flex items-center gap-2 w-full bg-transparent border border-accent text-accent-700 px-4 py-3.5 font-sans font-extrabold text-card-title mt-7 hover:bg-accent-100"
						>
							<FeatherIcon name="log-out" class="w-4 h-4" />
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
								value: employeeDoc.doc[field],
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
import GPage from "@/components/glass/GPage.vue"
import { computed, inject, ref, watch, onMounted, onBeforeUnmount } from "vue"
import { useRouter } from "vue-router"
import { IonContent } from "@ionic/vue"
import { FeatherIcon, createDocumentResource, createResource, toast } from "frappe-ui"

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
		icon: "user",
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
		icon: "file",
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
		icon: "book",
		title: __("Contact Information"),
		kind: "contact",
		fields: ["cell_number", "personal_email", "company_email", "preferred_email"],
	},
]

const isInfoModalOpen = ref(false)
const selectedItem = ref(null)

const pendingApprovalsCount = computed(() => Number(pendingCountResource.data) || 0)

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
	const field = employeeDocType.data.find((field) => field.fieldname === fieldname)
	return [__(field?.label, null, "Employee"), field?.fieldtype]
}

const getFieldValue = (fieldname) => {
	if (fieldname === "employee_number" && !employeeDoc.doc[fieldname]) {
		return employeeDoc.doc["name"]
	}
	if (fieldname === "reports_to") {
		return reportsToName.data || employeeDoc.doc[fieldname]
	}
	return employeeDoc.doc[fieldname]
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

onMounted(() => {
	socket.emit("doctype_subscribe", DOCTYPE)
	socket.on("list_update", (data) => {
		if (data.doctype === DOCTYPE && data.name === employee.data.name) {
			employeeDoc.reload()
		}
	})
	socket.on("hrms:remote_checkin_request", onRemoteCheckinEvent)
	pendingCountResource.fetch()
})

onBeforeUnmount(() => {
	socket.emit("doctype_unsubscribe", DOCTYPE)
	socket.off("list_update")
	socket.off("hrms:remote_checkin_request", onRemoteCheckinEvent)
})
</script>
