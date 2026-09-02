<template>
	<BaseLayout :pageTitle="__('Team Roster')">
		<template #body>
			<div class="flex flex-col gap-5 w-full max-w-content-column-lg mx-auto px-4 pt-[18px] pb-24 lg:p-7">
				<!-- HR-only team selector: HR has no direct reports, so without this
				     the roster is empty. Same pattern as TeamDashboard. -->
				<div v-if="teamManagers.data?.length" class="flex flex-row items-center gap-2">
					<span class="g-eyebrow flex-none">{{ __("Team of") }}</span>
					<Autocomplete
						class="flex-1 min-w-0"
						:options="managerOptions"
						:modelValue="selectedOption"
						:placeholder="__('Select a team')"
						@update:modelValue="onManagerPicked"
					/>
				</div>

				<!-- week navigation -->
				<div class="flex flex-row items-center justify-between">
					<GIconButton :label="__('Previous week')" @click="changeWeek(-1)">
						<FeatherIcon name="chevron-left" class="h-4 w-4" />
					</GIconButton>
					<span class="g-datenav__label" data-visual-mask>{{ weekLabel }}</span>
					<GIconButton :label="__('Next week')" @click="changeWeek(1)">
						<FeatherIcon name="chevron-right" class="h-4 w-4" />
					</GIconButton>
				</div>

				<ResourceError :resource="teamRoster" what="your team's roster" />

				<!-- one section per member: identity + a 7-day shift strip -->
				<template v-if="teamRoster.data?.members?.length">
					<div v-for="member in teamRoster.data.members" :key="member.name" class="flex flex-col gap-2.5">
						<div class="flex items-start justify-between gap-2">
							<div class="flex flex-col min-w-0">
								<span class="text-panel-title text-inkbase truncate">{{ member.employee_name }}</span>
								<span v-if="member.branch || member.department" class="text-kra-label text-ink-600 truncate">
									{{ member.branch || member.department }}
								</span>
							</div>
							<button class="g-seclink g-focusable text-kra-label text-accent-ink underline underline-offset-link flex-none" @click="openAssign(member)">
								{{ __("Assign") }}
							</button>
						</div>
						<!-- day strip; scrolls horizontally on a narrow phone -->
						<div class="flex gap-1.5 overflow-x-auto pb-1">
							<div
								v-for="day in weekDays"
								:key="day.iso"
								class="flex flex-col items-center justify-center flex-none w-[44px] py-1.5 rounded-well border border-divider"
								:class="shiftOn(member, day) ? 'bg-surface' : ''"
							>
								<span class="text-caption text-ink-600 uppercase">{{ day.dow }}</span>
								<span class="text-button-label font-semibold" :class="shiftOn(member, day) ? 'text-inkbase' : 'text-ink-500'">
									{{ shiftCode(member, day) }}
								</span>
							</div>
						</div>
					</div>
				</template>

				<div v-else-if="!teamRoster.loading" class="text-caption text-ink-600 text-center py-8">
					{{ __("No team members to roster. You only see people who report to you.") }}
				</div>
				<div v-if="teamRoster.loading" class="flex mt-2 items-center justify-center">
					<LoadingIndicator class="w-6 h-6 text-ink-500" />
				</div>
			</div>

			<!-- Assign sheet: the fence lives on the server; this only collects input -->
			<GModal :isOpen="assignOpen" :title="__('Assign shift')" @did-dismiss="assignOpen = false">
				<template #actionSheet>
					<div class="flex flex-col gap-4 pt-1">
						<div class="text-kra-label text-ink-600">{{ assignTarget?.employee_name }}</div>
						<label class="flex flex-col gap-1.5">
							<span class="g-eyebrow">{{ __("Shift type") }}</span>
							<Link doctype="Shift Type" v-model="form.shift_type" />
						</label>
						<label class="flex flex-col gap-1.5">
							<span class="g-eyebrow">{{ __("Location") }}</span>
							<Link doctype="Shift Location" v-model="form.shift_location" />
						</label>
						<div class="flex gap-3">
							<label class="flex flex-col gap-1.5 flex-1">
								<span class="g-eyebrow">{{ __("From") }}</span>
								<input type="date" v-model="form.start_date" class="g-touch bg-surface border border-divider rounded-input p-2.5 text-inkbase" />
							</label>
							<label class="flex flex-col gap-1.5 flex-1">
								<span class="g-eyebrow">{{ __("To") }}</span>
								<input type="date" v-model="form.end_date" class="g-touch bg-surface border border-divider rounded-input p-2.5 text-inkbase" />
							</label>
						</div>
						<GButton :disabled="!canSubmit" :pending="assignShift.loading" @click="submitAssign">
							{{ __("Assign shift") }}
						</GButton>
					</div>
				</template>
			</GModal>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, reactive, ref, onMounted } from "vue"
import { Autocomplete, FeatherIcon, LoadingIndicator, toast } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import GModal from "@/components/glass/GModal.vue"
import GButton from "@/components/glass/GButton.vue"
import Link from "@/components/Link.vue"
import ResourceError from "@/components/ResourceError.vue"
import { teamRoster, assignShift, teamManagers } from "@/data/team"
import { buildManagerOptions } from "@/utils/team"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

// HR-only "Team of" selector — HR has no direct reports, so they must pick a
// manager to see/roster that team. Non-HR receive [] and the selector hides.
const selectedManager = ref("")
const selectedOption = ref(null)
const managerOptions = computed(() => buildManagerOptions(teamManagers.data || [], __("Select a team")))
function onManagerPicked(option) {
	selectedOption.value = option
	selectedManager.value = option?.value || ""
	load()
}

// Monday-anchored week the grid is showing
const weekStart = ref(dayjs().startOf("week").add(1, "day"))

const weekDays = computed(() =>
	Array.from({ length: 7 }, (_, i) => {
		const d = weekStart.value.add(i, "day")
		return { iso: d.format("YYYY-MM-DD"), dow: d.format("dd").slice(0, 2) }
	})
)
const weekLabel = computed(
	() => `${weekStart.value.format("D MMM")} – ${weekStart.value.add(6, "day").format("D MMM")}`
)

function load() {
	teamRoster.submit({
		start_date: weekStart.value.format("YYYY-MM-DD"),
		end_date: weekStart.value.add(6, "day").format("YYYY-MM-DD"),
		manager: selectedManager.value || undefined,
	})
}
function changeWeek(n) {
	weekStart.value = weekStart.value.add(n * 7, "day")
	load()
}
onMounted(load)

// a shift covers a day when start_date <= day <= end_date (open-ended = ongoing)
function shiftOn(member, day) {
	return (member.shifts || []).find(
		(s) =>
			!dayjs(day.iso).isBefore(dayjs(s.start_date)) &&
			(!s.end_date || !dayjs(day.iso).isAfter(dayjs(s.end_date)))
	)
}
function shiftCode(member, day) {
	const s = shiftOn(member, day)
	if (!s) return "—"
	// short, legible code from the shift type name (e.g. "Night" -> "N")
	return String(s.shift_type || "?")
		.replace(/[^A-Za-z0-9]/g, "")
		.slice(0, 1)
		.toUpperCase()
}

// --- assign ---
const assignOpen = ref(false)
const assignTarget = ref(null)
const form = reactive({ shift_type: "", shift_location: "", start_date: "", end_date: "" })

function openAssign(member) {
	assignTarget.value = member
	form.shift_type = ""
	form.shift_location = ""
	form.start_date = weekStart.value.format("YYYY-MM-DD")
	form.end_date = weekStart.value.add(6, "day").format("YYYY-MM-DD")
	assignOpen.value = true
}
const canSubmit = computed(() => form.shift_type && form.start_date)
function submitAssign() {
	if (!canSubmit.value) return
	assignShift.submit(
		{
			employee: assignTarget.value.name,
			company: assignTarget.value.company,
			shift_type: form.shift_type,
			start_date: form.start_date,
			end_date: form.end_date || null,
			status: "Active",
			shift_location: form.shift_location || null,
		},
		{
			onSuccess: () => {
				assignOpen.value = false
				toast.success(__("Shift assigned"))
				load()
			},
			onError: (e) => toast.error(e?.messages?.[0] || __("Could not assign shift")),
		}
	)
}
</script>
