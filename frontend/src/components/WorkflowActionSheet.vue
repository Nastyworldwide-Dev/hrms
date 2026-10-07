<template>
	<div
		v-if="actions.length > 0"
		:class="[
			props.view === 'form'
				? 'px-4 pt-4 pb-4 standalone:pb-safe-bottom bg-ground sticky bottom-0 w-full z-40 border-t border-divider'
				: 'flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t border-divider bg-sheet-bg z-overlay p-4',
		]"
	>
		<div :class="props.view === 'form' ? 'w-full max-w-content-column-lg mx-auto' : 'contents'">
			<GButton
				v-if="props.view === 'form' || actions.length > 2"
				:label="__('Actions')"
				@click="showTransitions()"
			>
				<template #trailing><ChevronUp class="w-4" /></template>
			</GButton>

			<template v-else>
				<!-- Destructive transitions (reject, cancel) take the danger fill;
				     approve is the primary; anything else is a ghost. -->
				<component
					:is="action.role === 'destructive' || action.variant === 'solid' ? GButton : GGhostButton"
					v-for="action in actions"
					:key="action.text"
					:label="__(action.text, null, props.doc?.doctype)"
					:danger="action.role === 'destructive' || undefined"
					@click="applyWorkflow({ workflowAction: action.data.action })"
				/>
			</template>
		</div>
	</div>

	<!-- The app's own action sheet, as every other menu (alpha.13): Ionic's
	     loaded 26 KB for everyone to serve this one screen. Close is the
	     sheet's own X; no "Dismiss" row is needed. -->
	<GActionSheet
		:is-open="showActionSheet"
		:title="__('Actions')"
		:actions="sheetActions"
		@select="(key) => applyWorkflow({ workflowAction: key })"
		@did-dismiss="showActionSheet = false"
	/>
</template>

<script setup>
import { Check, ChevronUp, X } from "lucide-vue-next"
import GButton from "@/components/glass/GButton.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import { modalController } from "@ionic/vue"
import { computed, ref, onMounted, inject } from "vue"
import GActionSheet from "@/components/glass/GActionSheet.vue"

const props = defineProps({
	doc: {
		type: Object,
		required: true,
	},
	workflow: {
		type: Object,
		required: false,
	},
	view: {
		type: String,
		default: "form",
		validator: (value) => ["form", "actionSheet"].includes(value),
	},
})

const emit = defineEmits(["workflow-applied"])

let showActionSheet = ref(false)
let actions = ref([])

const __ = inject("$translate")

const getTransitions = async () => {
	const transitions = await props.workflow.getTransitions(props.doc)
	actions.value = transitions.map((transition) => {
		let role = ""
		let theme = "gray"
		let variant = "subtle"
		let icon = null
		let actionLabel = transition.toLowerCase()

		if (actionLabel.includes("reject") || actionLabel.includes("cancel")) {
			role = "destructive"
			theme = "red"
			variant = "subtle"
			icon = X
		} else if (actionLabel.includes("approve")) {
			theme = "green"
			variant = "solid"
			icon = Check
		}

		return {
			text: __(transition, null, props.doc?.doctype),
			role: role,
			theme: theme,
			variant: variant,
			icon,
			data: {
				action: transition,
			},
		}
	})
}

//: The transitions as sheet rows; the key is the workflow action itself.
const sheetActions = computed(() =>
	actions.value.map((a) => ({
		key: a.data.action,
		label: a.text,
		destructive: a.role === "destructive",
	}))
)

const showTransitions = () => {
	showActionSheet.value = true
}

const applyWorkflow = async ({ workflowAction = "" }) => {
	const action = workflowAction
	if (action) {
		await props.workflow.applyWorkflow(props.doc, action)
		modalController.dismiss()
		emit("workflow-applied")
	}

	showActionSheet.value = false
}

onMounted(() => getTransitions())
</script>

