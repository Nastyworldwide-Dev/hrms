<!--
  Link — pick one record of a doctype (Frappe Link fields).

  Glass searchable picker: the field is an input-skinned button showing the
  chosen value; tapping it opens a GModal sheet with a search box and the
  matching records as 44px rows. It replaced frappe-ui's Autocomplete, whose
  grey trigger and white popover were the "Select Leave Type" box on the
  owner's screenshot. The DATA side is unchanged: same search_link resource,
  same transform, same debounce and reload rules.

  Props / emits unchanged: doctype, modelValue, filters, disabled;
  update:modelValue (the record name, or "" when cleared).
-->
<template>
	<div class="g-linkpick">
		<button
			type="button"
			class="g-input g-linkpick__trigger g-focusable"
			:class="{ 'g-linkpick__trigger--empty': !modelValue }"
			:disabled="disabled"
			:aria-label="ariaLabel || undefined"
			aria-haspopup="dialog"
			:aria-expanded="open ? 'true' : 'false'"
			@click="openSheet"
		>
			<span class="g-linkpick__value">{{ selectedLabel }}</span>
			<ChevronDown class="g-linkpick__chevron" aria-hidden="true" />
		</button>

		<GModal :is-open="open" :title="__(doctype)" @did-dismiss="open = false">
			<div class="g-linkpick__sheet">
				<GSearchBar
					:model-value="query"
					:placeholder="__('Search')"
					@update:model-value="onQuery"
					@clear="onQuery('')"
				/>
				<ul class="g-linkpick__list" role="listbox" :aria-label="__(doctype)">
					<li
						v-for="option in options.data || []"
						:key="option.value"
						role="option"
						:aria-selected="option.value === modelValue ? 'true' : 'false'"
						class="g-row g-row--tappable g-linkpick__option"
						:class="{ 'g-linkpick__option--on': option.value === modelValue }"
						tabindex="0"
						@click="choose(option.value)"
						@keydown.enter.prevent="choose(option.value)"
						@keydown.space.prevent="choose(option.value)"
					>
						<span class="g-row__label">{{ option.label }}</span>
						<Check
							v-if="option.value === modelValue"
							class="g-linkpick__tick"
							aria-hidden="true"
						/>
					</li>
				</ul>
				<p v-if="options.loading" class="g-linkpick__note" role="status">
					{{ __("Loading…") }}
				</p>
				<p v-else-if="!(options.data || []).length" class="g-linkpick__note" role="status">
					{{ __("Nothing found") }}
				</p>
				<button
					v-if="modelValue"
					type="button"
					class="g-row g-row--tappable g-linkpick__clear g-focusable"
					@click="choose('')"
				>
					{{ __("Clear") }}
				</button>
			</div>
		</GModal>
	</div>
</template>

<script setup>
import { createResource, debounce } from "frappe-ui"
import { Check, ChevronDown } from "lucide-vue-next"
import { ref, computed, watch } from "vue"

import GModal from "@/components/glass/GModal.vue"
import GSearchBar from "@/components/glass/GSearchBar.vue"

const props = defineProps({
	doctype: {
		type: String,
		required: true,
	},
	modelValue: {
		type: String,
		required: false,
		default: "",
	},
	filters: {
		type: Object,
		// Vue requires a factory here — a literal default is the SAME object
		// shared by every <Link> that doesn't pass its own filters, which is
		// also why this warned on every render in dev console before now.
		default: () => ({}),
	},
	disabled: {
		type: Boolean,
		default: false,
	},
	// accessible name when the visible label is a sibling, not a <label for>
	ariaLabel: {
		type: String,
		default: "",
	},
})

const emit = defineEmits(["update:modelValue"])

const searchText = ref("")
// what the search box shows now; searchText is what the server last searched
const query = ref("")
const open = ref(false)

// initial rows shown before the user types; search_link's own default is 10
const PAGE_LENGTH = 20

function openSheet() {
	if (props.disabled) return
	console.info("[Link] opening picker", props.doctype)
	open.value = true
}

function choose(value) {
	console.info("[Link] picked", props.doctype, value || "(cleared)")
	emit("update:modelValue", value || "")
	open.value = false
}

function onQuery(text) {
	query.value = text || ""
	handleQueryUpdate(query.value)
}

const options = createResource({
	url: "frappe.desk.search.search_link",
	params: {
		doctype: props.doctype,
		txt: searchText.value,
		filters: props.filters,
		// search_link defaults to 10 — too few for masters like Department (300+)
		// or Cost Center, which then look "partially displayed". Show a fuller
		// first page; typing still narrows via txt for anything past it.
		page_length: PAGE_LENGTH,
	},
	method: "POST",
	transform: (data) => {
		const mapped = data.map((doc) => {
			let title = null
			if (doc.label && doc.label !== doc.value) {
				title = doc.label
			} else if (doc.description) {
				title = doc.description.split(",")[0]
			}
			return {
				// The title alone (K3 / ruling L4): "W0 approver", not
				// "W0 approver : nadi.w0.approver@…". The id stays the value.
				label: title || doc.value,
				value: doc.value,
			}
		})

		if (props.modelValue && !mapped.find((o) => o.value === props.modelValue)) {
			mapped.unshift({ label: props.modelValue, value: props.modelValue })
		}
		return mapped
	},
})

// the trigger shows the option's title when it is loaded
const selectedLabel = computed(() => {
	if (!props.modelValue) return ""
	const hit = (options.data || []).find((o) => o.value === props.modelValue)
	return hit?.label || props.modelValue
})

const reloadOptions = (searchTextVal) => {
	options.update({
		params: {
			txt: searchTextVal,
			doctype: props.doctype,
			filters: props.filters,
			page_length: PAGE_LENGTH,
		},
	})
	options.reload()
}

const handleQueryUpdate = debounce((newQuery) => {
	const val = newQuery || ""
	if (searchText.value === val) return
	searchText.value = val
	reloadOptions(val)
}, 300)

watch(
	() => props.doctype,
	() => {
		if (!props.doctype || props.doctype === options.doctype) return
		reloadOptions("")
	},
	{ immediate: true }
)

watch(
	() => props.filters,
	() => reloadOptions("")
)

watch(
	() => props.modelValue,
	(newVal, oldVal) => {
		if (!newVal && oldVal) {
			// value cleared — reload so the list shows the full default page
			searchText.value = ""
			query.value = ""
			reloadOptions("")
		} else if (newVal && newVal !== oldVal) {
			// reload so transform can inject it if it's outside the default page
			const inOptions = (options.data || []).find((o) => o.value === newVal)
			if (options.data && !inOptions) reloadOptions("")
		}
	}
)
</script>
