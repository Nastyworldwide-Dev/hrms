<template>
	<BaseLayout :pageTitle="__('Approvals')">
		<template #body>
			<!-- Everything waiting on YOUR decision (audit-flows 4B; owner ruling
			     23 Sep: approvals appear only where they can be done), GROUPED so a
			     long queue reads at a glance (owner-approved design, 23 Sep): Yours
			     first, then Other teams you may act for; department, then kind; one
			     line per person; five lines, then "See all"; never an endless list
			     (NN/g infinite scrolling; Baymard "load more"). Every request still
			     opens the same sheet that decides it. -->
			<GPullRefresh @refresh="refresh" />
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:p-7"
			>
				<ResourceError :resource="waiting" what="your approvals" />

				<GListPanel v-if="waiting.loading && !waiting.data" loading :rows="1" />

				<template v-else-if="!waiting.error">
					<p v-if="rows.length" class="g-form-footer">
						{{ summary }}
					</p>
					<!-- The same 51 pt row as the skeleton above (alpha.8 r3: three
					     skeleton rows collapsing to one grey line moved the page
					     132 pt; alpha.9 D5: nothing loose). -->
					<GListPanel v-else>
						<GListRow :label='__("Nothing is waiting on you.")' :tint="TILE.neutral" :tappable="false">
							<template #icon>
								<CircleCheckBig class="g-row-icon" />
							</template>
						</GListRow>
					</GListPanel>

					<!-- YOURS: sent to you to decide -->
					<section v-if="groups.yours.count" class="flex flex-col gap-3">
						<h2 class="g-eyebrow">{{ __("Yours") }} · {{ groups.yours.count }}</h2>
						<!-- ONE panel for the section, groups separated by captions (§15.2:
						     a grouped list is flattened into one surface, as the balance
						     grid and issue list are). -->
						<GListPanel>
							<template v-for="dept in groups.yours.departments" :key="dept.key">
								<p class="g-approvals__dept text-caption text-ink-600">
									{{ dept.name || __("No department") }} · {{ dept.count }}
								</p>
								<template v-for="kind in dept.kinds" :key="`${dept.key}:${kind.key}`">
									<p class="g-approvals__kind text-caption text-ink-600">
										{{ __(kind.kind) }} · {{ kind.count }}
									</p>
									<GListRow
										v-for="person in shown(`${dept.key}:${kind.key}`, kind.people).rows"
										:key="person.key"
										:label="personLine(person, __)"
										:sublabel="personWhen(person)"
										@click="openPerson(person)"
									/>
									<GroupMore
										:page="shown(`${dept.key}:${kind.key}`, kind.people)"
										@all="expand(`${dept.key}:${kind.key}`)"
										@more="more(`${dept.key}:${kind.key}`)"
									/>
								</template>
							</template>
						</GListPanel>
					</section>

					<!-- OTHER TEAMS: someone else approves; you may step in -->
					<section v-if="groups.other.count" class="flex flex-col gap-3">
						<!-- A heading like "Yours", so heading navigation finds it; the
						     button inside it is the disclosure (WAI-ARIA APG). -->
						<h2 class="m-0">
							<button
								type="button"
								class="g-focusable g-approvals__toggle"
								:aria-expanded="String(otherOpen)"
								aria-controls="approvals-other-teams"
								@click="otherOpen = !otherOpen"
							>
								<span class="g-eyebrow">{{ __("Other teams") }} · {{ groups.other.count }}</span>
								<span class="text-caption text-ink-600">{{
									otherOpen ? __("Hide") : __("Show")
								}}</span>
							</button>
						</h2>
						<div v-show="otherOpen" id="approvals-other-teams" class="flex flex-col gap-3">
							<GListPanel>
								<template v-for="team in groups.other.teams" :key="team.key">
									<p class="g-approvals__kind text-caption text-ink-600">
										{{
											[
												team.name || __("No department"),
												team.approverName ? __("{0}'s team", [team.approverName]) : "",
												team.count,
											]
												.filter(Boolean)
												.join(" · ")
										}}
									</p>
									<GListRow
										v-for="person in shown(team.key, team.people).rows"
										:key="person.key"
										:label="personLine(person, __)"
										:sublabel="`${__(person.kind)} · ${personWhen(person)}`"
										@click="openPerson(person)"
									/>
									<GroupMore
										:page="shown(team.key, team.people)"
										@all="expand(team.key)"
										@more="more(team.key)"
									/>
								</template>
							</GListPanel>
						</div>
					</section>

					<p v-if="waiting.data?.capped" class="text-caption text-ink-600">
						{{ __("Showing the oldest first. More are waiting.") }}
					</p>
				</template>

				<!-- Ruling 2 (23 Sep): what you already answered stays reachable,
				     worded for what is behind it: requests on the Requests page,
				     check-ins in a sheet here. -->
				<GListPanel v-if="isApprover.data">
					<GListRow :label="requestsAnsweredLabel" @click="openAnsweredRequests" />
					<GListRow :label="answeredLabel" @click="openAnswered" />
				</GListPanel>
			</div>

			<!-- One person's requests of one kind: each opens the deciding sheet. -->
			<GModal :is-open="!!personOpen" :title="personOpen?.who" @did-dismiss="personOpen = null">
				<GListPanel v-if="personOpen">
					<GListRow
						v-for="row in personOpen.rows"
						:key="`${row.doctype}:${row.name}`"
						:label="`${__(row.kind)} · ${row.who}`"
						:sublabel="rowLine(row)"
						@click="open(row)"
					/>
				</GListPanel>
			</GModal>

			<GModal
				:is-open="answeredOpen"
				:title="answeredLabel"
				@did-dismiss="answeredOpen = false"
			>
				<div class="flex flex-col gap-3 px-4 pb-8">
					<GListPanel v-if="decided.loading && !decided.data" loading />
					<ResourceError v-else-if="decided.error" :resource="decided" what="your answers" />
					<GListPanel v-else-if="decided.data?.length">
						<GListRow
							v-for="req in decided.data"
							:key="req.name"
							:label="`${req.employee_name || req.employee} · ${__(req.status)}`"
							:sublabel="answeredLine(req)"
						/>
					</GListPanel>
					<p v-else class="text-caption text-ink-600">{{ __("Nothing answered yet.") }}</p>
				</div>
			</GModal>

			<GModal :is-open="!!selected" @did-dismiss="close">
				<CheckinDecisionSheet
					v-if="selected?.doctype === 'Remote Checkin Request'"
					:row="selected.row"
					@decided="close"
				/>
				<RequestActionSheet
					v-else-if="selected"
					:fields="REQUEST_SUMMARY_FIELDS[selected.doctype]"
					v-model="selected"
				/>
			</GModal>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, h, inject, reactive, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { createResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import CheckinDecisionSheet from "@/components/CheckinDecisionSheet.vue"
import RequestActionSheet from "@/components/RequestActionSheet.vue"
import ResourceError from "@/components/ResourceError.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"
import GPullRefresh from "@/components/glass/GPullRefresh.vue"
import { CircleCheckBig } from "lucide-vue-next"
import { TILE } from "@/utils/iconTile"
import { personalCacheKey } from "@/utils/personalCache"
import { REQUEST_SUMMARY_FIELDS } from "@/data/config/requestSummaryFields"
import { decidedForApproverResource } from "@/data/remoteCheckin"
import { isApprover } from "@/data/team"
import { groupApprovals, pageOf, personLine } from "@/utils/approvalGroups"

const __ = inject("$translate")
const router = useRouter()
const $dayjs = inject("$dayjs")

// The server decides who sees what, and which section each row is in: only
// requests routed to the caller, by the same check approval.decide uses
// (hrms/api/approvals_list.py). This page only groups them.
const waiting = createResource({
	url: "hrms.api.approvals_list.get_waiting_for_me",
	// Personal, like every approver-scoped read: without a cache every visit
	// drew three skeleton rows, then collapsed to one line (alpha.8 r3).
	cache: personalCacheKey("nsty:approvals-waiting"),
	auto: true,
})
const rows = computed(() => waiting.data?.rows || [])
const groups = computed(() => groupApprovals(rows.value))

//: "3 waiting · oldest since 20 Sep" (mockup 4's summary line).
const summary = computed(() => {
	const oldest = [...rows.value].sort((a, b) => (a.modified < b.modified ? -1 : 1))[0]?.modified
	const count = __("{0} waiting", [rows.value.length])
	return oldest ? `${count} · ${__("oldest since {0}", [$dayjs(oldest).format("D MMM")])}` : count
})

// Other teams starts folded when it is long, so your own work stays on top.
const otherOpen = ref(true)
watch(
	() => groups.value.other.startCollapsed,
	(collapsed) => (otherOpen.value = !collapsed),
	{ immediate: true }
)

// Per group: five lines, then "See all"; expanded, twenty per page.
const expanded = reactive({})
function shown(key, lines) {
	return pageOf(lines, { expanded: Boolean(expanded[key]), pages: expanded[key] || 1 })
}
function expand(key) {
	console.info("[Approvals] see all", key)
	expanded[key] = 1
}
function more(key) {
	expanded[key] = (expanded[key] || 1) + 1
}

//: The "See all" / "Show more (N left)" button under a group.
const GroupMore = (props, { emit }) => {
	const page = props.page
	if (page.seeAll) {
		return h(
			"button",
			{ type: "button", class: "g-focusable g-list-more", onClick: () => emit("all") },
			__("See all")
		)
	}
	if (page.left > 0) {
		return h(
			"button",
			{ type: "button", class: "g-focusable g-list-more", onClick: () => emit("more") },
			__("Show more ({0} left)", [page.left])
		)
	}
	return null
}
GroupMore.props = ["page"]
GroupMore.emits = ["all", "more"]

function personWhen(person) {
	return person.oldest ? __("since {0}", [$dayjs(person.oldest).format("D MMM")]) : ""
}

function rowLine(row) {
	return [row.when, row.detail].filter(Boolean).join(" · ")
}

const decided = decidedForApproverResource
const answeredLabel = __("Check-ins you've already answered")
//: Ruling 2 wording: says what is behind it.
const requestsAnsweredLabel = __("Requests you've already answered")
function openAnsweredRequests() {
	console.info("[Approvals] opening answered requests")
	router.push({ name: "Requests", query: { tab: "answered" } })
}
const answeredOpen = ref(false)
function openAnswered() {
	console.info("[Approvals] opening answered check-ins")
	answeredOpen.value = true
	decided.reload()
}
function answeredLine(req) {
	const when = $dayjs(req.checkin_time).format("D MMM, h:mm a")
	return [when, req.approver_remarks].filter(Boolean).join(" · ")
}

// A person line opens their requests of that kind; one request opens straight away.
const personOpen = ref(null)
function openPerson(person) {
	console.info("[Approvals] opening person", person.doctype, person.count)
	if (person.rows.length === 1) return open(person.rows[0])
	personOpen.value = person
}

const selected = ref(null)
function open(row) {
	console.info("[Approvals] opening", row.doctype)
	personOpen.value = null
	// A check-in carries its photo and reason on the row; the request sheet
	// loads its own document.
	selected.value = { doctype: row.doctype, name: row.name, row }
}
function close() {
	selected.value = null
	// A decision made in the sheet changes the queue.
	waiting.reload()
}

async function refresh(event) {
	console.info("[Approvals] pull-to-refresh")
	await waiting.reload()
	event.target?.complete?.()
}
</script>

<style scoped>
.g-approvals__dept {
	padding: 12px 16px 0;
	font-weight: 600;
}
.g-approvals__kind {
	padding: 8px 16px 0;
}
.g-approvals__toggle {
	display: flex;
	width: 100%;
	align-items: center;
	justify-content: space-between;
	min-height: var(--g-touch-target-min);
	background: transparent;
	border: 0;
	padding: 0;
	cursor: pointer;
}
</style>
