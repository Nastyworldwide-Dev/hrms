<template>
	<BaseLayout :pageTitle="__('Approvals')">
		<template #body>
			<!-- Everything waiting on YOUR decision (audit-flows 4B; owner ruling
			     23 Sep: approvals appear only where they can be done), GROUPED so a
			     long queue reads at a glance (owner-approved design, 23 Sep): department,
			     then kind; five lines, then "See all"; never an endless list (NN/g
			     infinite scrolling; Baymard "load more"). Owner rulings 8 Oct 2026: only
			     the requests sent to YOU (Other teams is gone), ticks always shown (no
			     Select button), Approve and Reject many at once, up to 100. Every request
			     still opens the same sheet that decides it. -->
			<GPullRefresh @refresh="refresh" />
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:py-7"
				:class="{ 'g-approvals__page--barred': ticked.size }"
			>
				<ResourceError :resource="waiting" what="your approvals" />

				<!-- As tall as the page it becomes when requests wait (the banner, the
				     summary line, the chips row, a group heading and its first row), so
				     the queue arriving does not push "already answered" down
				     (scroll-and-shift audit, 29 Sep 2026: the approval line now routes
				     more to approvers; 8 Oct: the deadline banner and the chips row
				     were missing, 136 pt). The ghost banner is the real banner box
				     with its real second line, hidden, so it is 60 pt wide enough and
				     76 pt where that line wraps (320 wide): no fixed number fits both.
				     ceiling: a person row whose label wraps (320-326 wide, a long name) is
				     taller than its skeleton row, 22 pt, cold only; upgrade: keep the last
				     row count and height in the cache if an owner report names it. -->
				<template v-if="waiting.loading && !waiting.data">
					<GBanner variant="warning" class="g-approvals__ghost-banner" aria-hidden="true">
						<p class="m-0 font-semibold">&nbsp;</p>
						<p class="m-0 text-caption text-ink-600">
							{{ __("Staff attendance and pay wait on your decision.") }}
						</p>
					</GBanner>
					<p class="g-form-footer" aria-hidden="true">&nbsp;</p>
					<div class="g-approvals__ghost-chips" aria-hidden="true" />
					<!-- the "Yours" section it becomes: 144 pt, measured 29 Sep 2026 -->
					<div class="g-approvals__placeholder">
						<GListPanel loading :rows="2" />
					</div>
				</template>

				<template v-else-if="!waiting.error">
					<!-- The approver's own deadline, said plainly (HR, 4 Oct 2026: "make sure the
					     approver notices and does their job"). A banner only: it blocks nothing
					     and forces nothing (owner, 5 Oct). -->
					<GBanner v-if="headline" variant="warning" data-testid="approvals-banner">
						<p class="m-0 font-semibold">
							{{
								__("{0} waiting. Oldest since {1}.", [
									headline.count,
									$dayjs(headline.oldest).format("D MMM"),
								])
							}}
						</p>
						<p class="m-0 text-caption text-ink-600">
							{{ __("Staff attendance and pay wait on your decision.") }}
						</p>
					</GBanner>
					<p v-if="rows.length" class="g-form-footer">
						{{ summary }}
					</p>
					<div v-if="rows.length" class="flex items-center justify-between gap-3">
						<div class="g-approvals__chips" role="group" :aria-label="__('Filter by type')">
							<button
								v-for="chip in chips"
								:key="chip.key"
								type="button"
								class="g-focusable g-approvals__chip"
								:class="{ 'g-approvals__chip--on': kindFilter === chip.key }"
								:aria-pressed="String(kindFilter === chip.key)"
								@click="kindFilter = chip.key"
							>
								{{ chipLabel(chip, __) }}
							</button>
						</div>
						<!-- department, employee and dates live in one sheet; the count says how many are on -->
						<div class="flex flex-none items-center gap-1">
							<button
								v-if="filterCount"
								type="button"
								class="g-focusable g-approvals__clear"
								@click="clearFilters"
							>
								{{ __("Clear") }}
							</button>
							<button
								type="button"
								class="g-focusable g-approvals__chip"
								:class="{ 'g-approvals__chip--on': filterCount }"
								aria-haspopup="dialog"
								@click="filterOpen = true"
							>
								<ListFilter class="g-row-icon" aria-hidden="true" />
								{{ filterCount ? __("Filter ({0})", [filterCount]) : __("Filter") }}
							</button>
						</div>
					</div>
					<p v-if="nothingTickable(visibleRows)" class="text-caption text-ink-600 m-0">
						{{ __("These are approved one by one. Tap one to open it.") }}
					</p>
					<div v-if="pickable.length" class="flex items-center">
						<GCheckbox
							:model-value="allState === 'all'"
							:label="__('Select all {0}', [pickable.length])"
							@update:model-value="ticked = toggleAll(ticked, visibleRows)"
						/>
					</div>
					<!-- The same 51 pt row as the skeleton above (alpha.8 r3: three
					     skeleton rows collapsing to one grey line moved the page
					     132 pt; alpha.9 D5: nothing loose). -->
					<GListPanel v-if="!rows.length">
						<GListRow
							:label="__('Nothing is waiting on you.')"
							:tint="TILE.neutral"
							:tappable="false"
							wrap
						>
							<template #icon>
								<CircleCheckBig class="g-row-icon" />
							</template>
						</GListRow>
					</GListPanel>

					<!-- the filters hide everything: say so (Clear sits beside the Filter button) -->
					<GListPanel v-if="rows.length && !visibleRows.length">
						<GListRow :label="__('Nothing matches these filters.')" :tappable="false" wrap />
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
									<!-- A decided person leaves and the list closes the gap,
									     instead of the rows jumping when the queue reloads
									     (alpha.13). -->
									<TransitionGroup name="g-leave">
										<template
											v-for="person in shown(`${dept.key}:${kind.key}`, kind.people).rows"
											:key="person.key"
										>
											<!-- one row per request, so the approver ticks what they mean (a person can
											     have three requests of one kind). The tick is a 44 pt control of its own
											     and the text opens the request: with no Select mode a tap on the row can no
											     longer mean "tick", and a request must stay readable (reason, file) before
											     it is decided (owner ruling 8 Oct 2026). -->
											<template v-if="person.rows.some(canBulk)">
												<div
													v-for="req in person.rows.filter(canBulk)"
													:key="rowKey(req)"
													class="g-approvals__req"
												>
													<button
														type="button"
														role="checkbox"
														class="g-focusable g-approvals__tickbtn"
														:aria-checked="String(ticked.has(rowKey(req)))"
														:aria-label="reqLabel(req)"
														@click="ticked = toggle(ticked, req)"
													>
														<span
															class="g-approvals__tick"
															:class="{ 'g-approvals__tick--on': ticked.has(rowKey(req)) }"
															aria-hidden="true"
														>
															<Check v-if="ticked.has(rowKey(req))" class="g-row-icon" />
														</span>
													</button>
													<GListRow
														class="g-approvals__reqbody"
														:label="reqLabel(req)"
														wrap
														:sublabel="rowDetails(req, __)"
														@click="open(req)"
													>
														<template #badge>
															<span
																class="g-approvals__age"
																:class="`g-approvals__age--${tone(req)}`"
																>{{ ageWords(req) }}</span
															>
														</template>
													</GListRow>
												</div>
											</template>
											<GListRow
												v-else
												:label="personLine(person, __)"
												wrap
												:sublabel="personWhen(person)"
												@click="openPerson(person)"
											>
												<template #badge>
													<span
														class="g-approvals__age"
														:class="`g-approvals__age--${tone(person.rows[0])}`"
														>{{ ageWords(person.rows[0]) }}</span
													>
												</template>
											</GListRow>
										</template>
									</TransitionGroup>
									<GroupMore
										:page="shown(`${dept.key}:${kind.key}`, kind.people)"
										@all="expand(`${dept.key}:${kind.key}`)"
										@more="more(`${dept.key}:${kind.key}`)"
									/>
								</template>
							</template>
						</GListPanel>
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

			<GModal :is-open="answeredOpen" :title="answeredLabel" @did-dismiss="answeredOpen = false">
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

			<!-- The bar the approver acts from: how many are ticked, and what to do with them. -->
			<div
				v-if="ticked.size"
				class="g-approvals__bar"
				role="region"
				:aria-label="__('Ticked requests')"
			>
				<div class="g-approvals__bar-head">
					<div class="min-w-0 flex-1">
						<p class="m-0 font-semibold">{{ __("{0} selected", [ticked.size]) }}</p>
						<p class="m-0 text-caption text-ink-600">
							{{ __("Each one is checked before it is approved.") }}
						</p>
					</div>
					<button type="button" class="g-focusable g-approvals__clear" @click="ticked = new Set()">
						{{ __("Clear") }}
					</button>
				</div>
				<div class="g-approvals__bar-actions">
					<GButton class="flex-1" danger :label="__('Reject')" @click="startReject" />
					<GButton class="flex-1" :label="__('Approve')" @click="startApprove" />
				</div>
			</div>

			<GModal :is-open="filterOpen" :title="__('Filter')" @did-dismiss="filterOpen = false">
				<div class="flex flex-col gap-4">
					<GSelect
						v-if="departmentChoices.length > 1 || filters.department"
						v-model="filters.department"
						:label="__('Department')"
						:placeholder="__('All departments')"
						:options="departmentChoices"
					/>
					<GSelect
						v-if="employeeChoices.length > 1 || filters.employee"
						v-model="filters.employee"
						:label="__('Employee')"
						:placeholder="__('Everyone')"
						:options="employeeChoices"
					/>
					<div class="flex flex-col gap-3" role="group" aria-labelledby="approvals-dates">
						<p id="approvals-dates" class="g-eyebrow m-0">{{ __("Dates") }}</p>
						<GDatePicker v-model="filters.from" :label="__('From')" :max-date="filters.to" />
						<GDatePicker v-model="filters.to" :label="__('To')" :min-date="filters.from" />
						<p class="g-form-footer">
							{{ __("Shows requests that fall on any of these days.") }}
						</p>
					</div>
					<div class="flex gap-3">
						<GGhostButton
							class="flex-1"
							:label="__('Clear')"
							:disabled="!filterCount"
							@click="clearFilters"
						/>
						<GButton
							class="flex-1"
							:label="__('Show {0}', [visibleRows.length])"
							@click="filterOpen = false"
						/>
					</div>
				</div>
			</GModal>

			<GModal
				:is-open="!!sheet"
				:title="sheetTitle"
				:dismissible="sheet?.phase !== 'working'"
				@did-dismiss="closeSheet"
			>
				<div v-if="sheet" class="flex flex-col gap-3">
					<!-- how far the work is, read out politely as it goes (checking, approving or rejecting).
					     Always in the sheet, so the live region exists before its words change. Empty it
					     takes no room. -->
					<p class="m-0 text-caption text-ink-600" role="status" aria-live="polite">
						{{ progressText }}
					</p>
					<!-- A failed check stays here, with the ticks kept and a way to try again: a toast
					     disappears on its own and leaves nothing to press. -->
					<div v-if="sheet.phase === 'failed'" class="flex flex-col gap-3" role="alert">
						<p class="m-0 font-semibold">{{ __("Nothing was approved.") }}</p>
						<p class="m-0 text-caption text-ink-600">
							{{ __("Your ticks are kept. Check your connection and try again.") }}
						</p>
						<GButton :label="__('Try again')" @click="startApprove" />
					</div>
					<!-- A failed APPROVE (or REJECT) may have got some through before the connection dropped,
					     so it must not claim that nothing happened (review, 5 Oct 2026). A chunk that fails
					     stops the rest, and what the earlier chunks wrote is unknown until the list is read. -->
					<div
						v-else-if="sheet.phase === 'failed-approve'"
						class="flex flex-col gap-3"
						role="alert"
					>
						<p class="m-0 font-semibold">{{ __("We could not confirm what was approved.") }}</p>
						<p class="m-0 text-caption text-ink-600">
							{{ __("The list is reloading. Check what is left before you try again.") }}
						</p>
						<GButton :label="__('Close')" @click="closeSheet" />
					</div>
					<div
						v-else-if="sheet.phase === 'failed-reject'"
						class="flex flex-col gap-3"
						role="alert"
					>
						<p class="m-0 font-semibold">{{ __("We could not confirm what was rejected.") }}</p>
						<p class="m-0 text-caption text-ink-600">
							{{ __("The list is reloading. Check what is left before you try again.") }}
						</p>
						<GButton :label="__('Close')" @click="closeSheet" />
					</div>
					<!-- Some were refused: the sheet stays open and names each one with its reason. They stay
					     ticked and pending in the list. -->
					<template v-else-if="sheet.phase === 'result'">
						<p class="m-0 font-semibold">{{ resultWords }}</p>
						<section class="flex flex-col gap-2">
							<h3 class="g-eyebrow">
								{{
									sheet.mode === "reject"
										? __("{0} not rejected", [sheet.refused.length])
										: __("{0} not approved", [sheet.refused.length])
								}}
							</h3>
							<GListPanel>
								<GListRow
									v-for="req in sheet.refused"
									:key="rowKey(req)"
									:label="rowLabel(req)"
									:sublabel="req.reason"
									wrap
									:chevron="false"
									:tappable="false"
								/>
							</GListPanel>
							<p class="text-caption text-ink-600">
								{{ __("Refused ones stay in your list. Open one to see what to fix.") }}
							</p>
						</section>
						<GButton :label="__('Close')" @click="closeSheet" />
					</template>
					<!-- REJECT: one reason for all, editable per request; the button waits for every reason -->
					<template v-else-if="sheet.mode === 'reject'">
						<p class="m-0 text-caption text-ink-600">{{ sheet.summary }}</p>
						<GTextarea
							v-model="rejectShared"
							:label="__('Why not? (required)')"
							:disabled="sheet.phase === 'working'"
						/>
						<p class="m-0 text-caption text-ink-600">
							{{ __("Each person sees this reason on their request.") }}
						</p>
						<GListPanel>
							<div v-for="(req, at) in sheet.items" :key="rowKey(req)">
								<GListRow
									:label="rowLabel(req)"
									:sublabel="
										effectiveReason(rejectOwn[rowKey(req)], rejectShared) || __('Needs a reason')
									"
									wrap
									:chevron="false"
									:tappable="false"
								>
									<template #badge>
										<button
											type="button"
											class="g-focusable g-approvals__clear"
											:aria-expanded="String(Boolean(rejectEditing[rowKey(req)]))"
											:aria-controls="`approvals-reason-${at}`"
											:disabled="sheet.phase === 'working'"
											@click="rejectEditing[rowKey(req)] = !rejectEditing[rowKey(req)]"
										>
											{{ __("Edit reason") }}
										</button>
									</template>
								</GListRow>
								<!-- kept in the page when closed, so aria-controls always points at something -->
								<div
									:id="`approvals-reason-${at}`"
									class="g-approvals__reason"
									:hidden="!rejectEditing[rowKey(req)]"
								>
									<GTextarea
										v-if="rejectEditing[rowKey(req)]"
										:model-value="rejectOwn[rowKey(req)] || ''"
										:label="__('Reason for {0}', [req.who])"
										:placeholder="__('Leave empty to use the reason above')"
										:disabled="sheet.phase === 'working'"
										@update:model-value="rejectOwn[rowKey(req)] = $event"
									/>
								</div>
							</div>
						</GListPanel>
						<GButton
							danger
							:label="__('Reject {0}', [sheet.items.length])"
							:pending="sheet.phase === 'working'"
							:pending-label="__('Rejecting…')"
							:disabled="!rejectReady"
							@click="confirmReject"
						/>
					</template>
					<!-- APPROVE: what the check said (nothing to show while it is still checking) -->
					<template v-else-if="sheet.phase === 'ready' || sheet.phase === 'working'">
						<p class="m-0 text-caption text-ink-600">{{ sheet.summary }}</p>
						<section v-if="sheet.ready.length" class="flex flex-col gap-2">
							<h3 class="g-eyebrow">{{ __("{0} ready", [sheet.ready.length]) }}</h3>
							<GListPanel>
								<GListRow
									v-for="req in sheet.ready"
									:key="rowKey(req)"
									:label="rowLabel(req)"
									:chevron="false"
									:tappable="false"
								/>
							</GListPanel>
						</section>
						<section v-if="sheet.refused.length" class="flex flex-col gap-2">
							<h3 class="g-eyebrow">{{ __("{0} will be refused", [sheet.refused.length]) }}</h3>
							<GListPanel>
								<GListRow
									v-for="req in sheet.refused"
									:key="rowKey(req)"
									:label="rowLabel(req)"
									:sublabel="req.reason"
									:chevron="false"
									:tappable="false"
								/>
							</GListPanel>
							<p class="text-caption text-ink-600">
								{{ __("Refused ones stay in your list. Open one to see what to fix.") }}
							</p>
						</section>
						<GButton
							:label="
								sheet.ready.length
									? __('Approve {0}', [sheet.ready.length])
									: __('Nothing to approve')
							"
							:pending="sheet.phase === 'working'"
							:pending-label="__('Approving…')"
							:disabled="!sheet.ready.length"
							@click="confirmApprove"
						/>
					</template>
				</div>
			</GModal>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, defineAsyncComponent, h, inject, reactive, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { createResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import CheckinDecisionSheet from "@/components/CheckinDecisionSheet.vue"
import RequestActionSheet from "@/components/RequestActionSheet.vue"
import ResourceError from "@/components/ResourceError.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"
import GDatePicker from "@/components/glass/GDatePicker.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GSelect from "@/components/glass/GSelect.vue"
import GTextarea from "@/components/glass/GTextarea.vue"
//: Loaded on first use, not in the first download (alpha.13: Ionic's
//: refresher is 41 KB, and nobody pulls before the page has drawn).
const GPullRefresh = defineAsyncComponent(() => import("@/components/glass/GPullRefresh.vue"))
import { Check, CircleCheckBig, ListFilter } from "lucide-vue-next"
import { TILE } from "@/utils/iconTile"
import { personalCacheKey } from "@/utils/personalCache"
import { REQUEST_SUMMARY_FIELDS } from "@/data/config/requestSummaryFields"
import { decidedForApproverResource } from "@/data/remoteCheckin"
import { isApprover } from "@/data/team"
import { groupApprovals, pageOf, personLine } from "@/utils/approvalGroups"
import {
	BULK_CAP,
	activeFilters,
	afterApprove,
	ageTone,
	allState as allStateOf,
	banner,
	canBulk,
	canReject,
	chipLabel,
	daysWaiting,
	departmentOptions,
	effectiveReason,
	employeeOptions,
	filterRows,
	itemsFor,
	keepVisible,
	kindSummary,
	nothingTickable,
	onlyYours,
	overCap,
	prune,
	pruneFilters,
	rejectItems,
	rowDetails,
	rowKey,
	sendInChunks,
	sharedFor,
	siteToday,
	toggle,
	toggleAll,
	typeChips,
} from "@/utils/approvalBulk"
import GBanner from "@/components/glass/GBanner.vue"
import GButton from "@/components/glass/GButton.vue"
import GCheckbox from "@/components/glass/GCheckbox.vue"
import { gToast } from "@/components/glass/toast"
import { siteTimeZone } from "@/utils/siteTime"

const __ = inject("$translate")
const router = useRouter()
const $dayjs = inject("$dayjs")

// The server decides who sees what: only requests routed to the caller, by the same check
// approval.decide uses (hrms/api/approvals_list.py). Owner ruling 8 Oct 2026: no Other teams;
// onlyYours also drops such a row from a personal cache written before the server stopped
// sending them. This page only groups what is left.
const waiting = createResource({
	url: "hrms.api.approvals_list.get_waiting_for_me",
	// Personal, like every approver-scoped read: without a cache every visit
	// drew three skeleton rows, then collapsed to one line (alpha.8 r3).
	cache: personalCacheKey("nsty:approvals-waiting"),
	auto: true,
})
const rows = computed(() => onlyYours(waiting.data?.rows || []))

// Filter by type (HR, 4 Oct 2026), then by department, employee and dates (owner, 8 Oct 2026).
// The chips count what is waiting; the filters narrow what the groups below show, so "See all",
// the group counts and select-all all follow them.
const ticked = ref(new Set())
const kindFilter = ref("")
const chips = computed(() => typeChips(rows.value))
const filters = reactive({ department: "", employee: "", from: "", to: "" })
const filterOpen = ref(false)
const filterCount = computed(() => activeFilters(filters))
const visibleRows = computed(() => filterRows(rows.value, { kind: kindFilter.value, ...filters }))
// the choices come from the rows that are loaded; the employee list follows the department
const departmentChoices = computed(() => departmentOptions(rows.value))
const employeeChoices = computed(() =>
	employeeOptions(filterRows(rows.value, { department: filters.department }))
)
function clearFilters() {
	console.info("[Approvals] filters cleared")
	Object.assign(filters, { department: "", employee: "", from: "", to: "" })
}
const groups = computed(() => groupApprovals(visibleRows.value))
// A tick that is no longer shown (another chip) is dropped: the bar never counts, and Approve
// never sends, a request the approver cannot see ticked (design + code review, 5 Oct 2026).
watch(visibleRows, (list) => (ticked.value = keepVisible(ticked.value, list)))
watch(chips, (list) => {
	// a filter whose last request was decided is gone: fall back to All
	if (kindFilter.value && !list.some((chip) => chip.key === kindFilter.value))
		kindFilter.value = ""
})
// a department or employee whose last request was decided is gone too: the page never sits empty
// behind a filter nobody can see
watch(rows, (list) => Object.assign(filters, pruneFilters(filters, list)))
// the employee chosen must belong to the department chosen next
watch(
	() => filters.department,
	() => Object.assign(filters, pruneFilters(filters, rows.value))
)

// The site's today (Asia/Kuala_Lumpur), declared before its first reader.
const today = () => siteToday(new Date(), siteTimeZone())
const headline = computed(() => banner(rows.value, today()))

// Ticks are always shown (owner ruling 8 Oct 2026: chip, Select all, Approve, Confirm = 4 taps).
// Check-ins stay one by one (approvalBulk.ONE_BY_ONE).
const pickable = computed(() => visibleRows.value.filter(canBulk))
const allState = computed(() => allStateOf(ticked.value, visibleRows.value))
// a request that left the list (decided elsewhere, or approved here) is no longer ticked
watch(rows, (list) => (ticked.value = prune(ticked.value, list)))

//: "3 waiting · oldest since 20 Sep" (mockup 4's summary line).
const summary = computed(() => {
	const oldest = [...rows.value].sort((a, b) => (a.modified < b.modified ? -1 : 1))[0]?.modified
	const count = __("{0} waiting", [rows.value.length])
	return oldest ? `${count} · ${__("oldest since {0}", [$dayjs(oldest).format("D MMM")])}` : count
})

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

// A request in the list and in the sheets, named the way the list names it: who, then the days.
// The details (type, hours, amount, shift) ride on the second line.
const byKey = computed(() => new Map(rows.value.map((row) => [rowKey(row), row])))
const reqLabel = (row) => [row.who, row.when].filter(Boolean).join(" · ")
function rowLabel(req) {
	const row = byKey.value.get(rowKey(req))
	return row ? `${reqLabel(row)}${row.kind ? ` · ${__(row.kind)}` : ""}` : req.name
}

// How long a request has waited, in words and as a tone (amber from 7 days, red from 14).
const waited = (row) => daysWaiting(row.modified, today())
const tone = (row) => ageTone(waited(row))
const ageWords = (row) => {
	const days = waited(row)
	return days < 1 ? __("Today") : days === 1 ? __("1 day") : __("{0} days", [days])
}

// Decide many: ask the server which would go through, show it, then decide those. Up to 100 at once,
// sent ten at a time (approvalBulk.CHUNK_SIZE: the server takes 50 per call and a long call risks a
// timeout). The server adds no rule of its own: each request goes through the same decide() as one by one.
// sheet: null | { mode: "approve" | "reject", phase: "check" | "ready" | "working" | "result" | "failed"
//   | "failed-approve" | "failed-reject", ready, refused, items, summary, done, progress }
const sheet = ref(null)
const checkMany = createResource({ url: "hrms.api.approval.check_many" })
const decideMany = createResource({ url: "hrms.api.approval.decide_many" })
const rejectMany = createResource({ url: "hrms.api.approval.reject_many" })

// The count is the one the sheet was opened with: a partial result leaves fewer ticked, but the
// sheet is still about the request the approver started.
const sheetTitle = computed(() => {
	const current = sheet.value
	if (!current) return ""
	const n = current.count
	if (current.phase === "result")
		return current.mode === "reject" ? __("Rejected") : __("Approved")
	if (current.mode === "reject")
		return n === 1 ? __("Reject 1 request?") : __("Reject {0} requests?", [n])
	return n === 1 ? __("Approve 1 request?") : __("Approve {0} requests?", [n])
})
// "Checking 20 of 100…" / "Approving 30 of 100…" / "Rejecting 30 of 100…", read out politely
const progressText = computed(() => {
	const current = sheet.value
	if (!current?.progress) return ""
	const [sent, total] = current.progress
	if (current.phase === "check") return __("Checking {0} of {1}…", [sent, total])
	if (current.phase !== "working") return ""
	return current.mode === "reject"
		? __("Rejecting {0} of {1}…", [sent, total])
		: __("Approving {0} of {1}…", [sent, total])
})
const resultWords = computed(() => {
	const current = sheet.value
	if (!current) return ""
	const n = current.done
	return current.mode === "reject"
		? __("{0} rejected", [n])
		: n === 1
		? __("1 approved")
		: __("{0} approved", [n])
})

function closeSheet() {
	sheet.value = null
}

function overCapToast() {
	gToast({
		title: __("Pick up to {0} at a time", [BULK_CAP]),
		text: __("Untick some and try again."),
		variant: "warning",
	})
}

async function startApprove() {
	if (overCap(ticked.value)) return overCapToast()
	const items = itemsFor(ticked.value, visibleRows.value)
	console.info("[Approvals] checking", items.length)
	sheet.value = {
		mode: "approve",
		phase: "check",
		count: items.length,
		ready: [],
		refused: [],
		progress: [0, items.length],
	}
	try {
		const checked = await sendInChunks(
			items,
			(part) => checkMany.submit({ items: part }),
			"ready",
			(sent, total) => {
				if (sheet.value?.phase === "check")
					sheet.value = { ...sheet.value, progress: [sent, total] }
			}
		)
		const ready = checked.done
		sheet.value = {
			mode: "approve",
			phase: "ready",
			count: items.length,
			ready,
			refused: checked.refused,
			summary: kindSummary(ready.map((req) => byKey.value.get(rowKey(req))).filter(Boolean), __),
		}
	} catch (error) {
		console.warn("[Approvals] the check failed", error)
		// stay in the sheet with a way to try again; the ticks are kept
		sheet.value = { mode: "approve", phase: "failed", count: items.length, ready: [], refused: [] }
	}
}

async function confirmApprove() {
	const current = sheet.value
	if (!current || current.mode !== "approve" || current.phase !== "ready" || !current.ready.length)
		return
	console.info("[Approvals] approving", current.ready.length)
	sheet.value = { ...current, phase: "working", progress: [0, current.ready.length] }
	try {
		// only the ones the check said would go through, with the revision the approver saw
		const result = await sendInChunks(
			current.ready,
			(part) => decideMany.submit({ items: part }),
			"approved",
			(sent, total) => (sheet.value = { ...sheet.value, progress: [sent, total] })
		)
		await finish("approve", result, current.count)
	} catch (error) {
		console.warn("[Approvals] bulk approve failed", error)
		// what went through is unknown until the list is read again; say so, keep the ticks
		await failedWrite("failed-approve", current.count)
	}
}

// Reject many: one shared reason, editable per request; empty own reason = use the shared one.
const rejectShared = ref("")
const rejectOwn = reactive({}) // rowKey -> the request's own reason
const rejectEditing = reactive({}) // rowKey -> its "Edit reason" box is open
const rejectReady = computed(
	() =>
		sheet.value?.mode === "reject" &&
		sheet.value.phase === "ready" &&
		canReject(sheet.value.items, rejectShared.value, rejectOwn)
)

function startReject() {
	if (overCap(ticked.value)) return overCapToast()
	const items = itemsFor(ticked.value, visibleRows.value)
	console.info("[Approvals] rejecting sheet", items.length)
	rejectShared.value = ""
	for (const key of Object.keys(rejectOwn)) delete rejectOwn[key]
	for (const key of Object.keys(rejectEditing)) delete rejectEditing[key]
	sheet.value = {
		mode: "reject",
		phase: "ready",
		count: items.length,
		items,
		refused: [],
		summary: kindSummary(items.map((req) => byKey.value.get(rowKey(req))).filter(Boolean), __),
	}
}

async function confirmReject() {
	const current = sheet.value
	if (!current || current.mode !== "reject" || current.phase !== "ready" || !rejectReady.value)
		return
	const items = rejectItems(current.items, rejectShared.value, rejectOwn)
	console.info("[Approvals] rejecting", items.length)
	sheet.value = { ...current, phase: "working", progress: [0, items.length] }
	try {
		const result = await sendInChunks(
			items,
			(part) => rejectMany.submit({ items: part, reason: sharedFor(part, rejectShared.value) }),
			"rejected",
			(sent, total) => (sheet.value = { ...sheet.value, progress: [sent, total] })
		)
		await finish("reject", result, current.count)
	} catch (error) {
		console.warn("[Approvals] bulk reject failed", error)
		await failedWrite("failed-reject", current.count)
	}
}

// After the last chunk: what went through leaves the ticks; refused ones stay ticked and pending and,
// when there are any, the sheet stays open and names each with its reason.
async function finish(mode, result, count) {
	const done = afterApprove(ticked.value, { approved: result.done, refused: result.refused })
	ticked.value = done.selected
	gToast({
		title:
			mode === "reject"
				? __("{0} rejected", [done.approved])
				: done.approved === 1
				? __("1 approved")
				: __("{0} approved", [done.approved]),
		text: done.refused.length ? __("{0} stayed in your list.", [done.refused.length]) : "",
		variant: done.refused.length ? "warning" : "success",
	})
	sheet.value = done.refused.length
		? { mode, phase: "result", count, ready: [], refused: done.refused, done: done.approved }
		: null
	await waiting.reload()
}

// A chunk threw: the ones before it may have been written, so the page cannot say what went through.
async function failedWrite(phase, count) {
	sheet.value = {
		mode: phase === "failed-reject" ? "reject" : "approve",
		phase,
		count,
		ready: [],
		refused: [],
	}
	try {
		await waiting.reload()
	} catch (reloadError) {
		console.warn("[Approvals] reload after a failed bulk write failed", reloadError)
	}
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
/* first load only: the banner and the chips row the answer brings, kept in
   their places (visibility keeps the box, so the wrap at 320 wide is real) */
.g-approvals__ghost-banner {
	visibility: hidden;
}
.g-approvals__ghost-chips {
	min-height: var(--g-touch-target-min);
}
.g-approvals__chips {
	display: flex;
	min-width: 0;
	gap: 8px;
	overflow-x: auto;
	scrollbar-width: none;
}
.g-approvals__chip,
.g-approvals__clear {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	min-height: var(--g-touch-target-min);
	padding: 0 12px;
	border: 1px solid var(--g-hair);
	border-radius: 999px;
	background: transparent;
	color: var(--g-ink);
	white-space: nowrap;
	cursor: pointer;
}
.g-approvals__chip--on {
	background: var(--g-ink);
	color: var(--g-bg);
}
.g-approvals__clear {
	border-color: transparent;
	color: var(--g-accent-ink);
}
/* one request: its own 44 pt tick, then the row that opens it. The wrapper draws the divider the
   theme draws between sibling rows (.g-row + .g-row), which a wrapped row no longer has. */
.g-approvals__req {
	position: relative;
	display: flex;
	align-items: center;
	padding-left: 4px;
}
.g-approvals__req + .g-approvals__req::before {
	content: "";
	position: absolute;
	top: 0;
	left: 16px;
	right: 16px;
	height: 1px;
	background: var(--g-hair);
}
.g-approvals__tickbtn {
	display: grid;
	place-items: center;
	flex: none;
	min-width: var(--g-touch-target-min);
	min-height: var(--g-touch-target-min);
	border: 0;
	background: transparent;
	cursor: pointer;
}
.g-approvals__reqbody {
	flex: 1;
	min-width: 0;
	padding-left: 0;
}
.g-approvals__reason {
	padding: 0 16px 12px;
}
.g-approvals__tick {
	display: grid;
	place-items: center;
	width: 22px;
	height: 22px;
	border: 2px solid var(--g-ink2);
	border-radius: 999px;
}
.g-approvals__tick--on {
	background: var(--g-brand);
	border-color: var(--g-brand);
	color: var(--g-on-brand);
}
/* a number AND a word: colour is never the only signal (WCAG 1.4.1) */
.g-approvals__age {
	font-size: 12px;
	font-weight: 600;
	padding: 2px 8px;
	border-radius: 999px;
	white-space: nowrap;
}
.g-approvals__age--calm {
	color: var(--g-ink2);
}
.g-approvals__age--amber {
	color: var(--g-warn-ink);
}
.g-approvals__age--red {
	color: var(--g-danger-ink);
}
.g-approvals__page--barred {
	padding-bottom: 136px;
}
.g-approvals__bar {
	position: sticky;
	/* sticky sticks to the scrollport edge, which the floating tab bar overlays. ion-content keeps
	   a reservation for that bar in --padding-bottom (theme/glass-components.css); the bar sits
	   above it, and never lower than the home indicator on a page with no tab bar */
	bottom: max(var(--padding-bottom, 0px), env(safe-area-inset-bottom, 0px));
	z-index: 3;
	display: flex;
	flex-direction: column;
	gap: 8px;
	padding: 12px 16px;
	border-top: 1px solid var(--g-hair);
	background: var(--g-sheet-bg);
}
.g-approvals__bar-head,
.g-approvals__bar-actions {
	display: flex;
	align-items: center;
	gap: 12px;
}
</style>
