<template>
	<div>
		<span class="block text-xs leading-5 text-gray-600">
			{{ props.label }}
		</span>
		<Autocomplete
			ref="autocompleteRef"
			size="sm"
			v-model="value"
			:options="shownOptions"
			:class="disabled ? 'pointer-events-none' : ''"
			:disabled="disabled"
			@update:query="handleQueryUpdate"
		>
			<!-- the chosen shift shows a tick in a long list (frappe-ui draws one only when this slot exists) -->
			<template #item-prefix="{ option }">
				<FeatherIcon v-if="option.value === props.modelValue" name="check" class="h-4 w-4 text-ink-gray-7" />
				<div v-else class="h-4 w-4" />
			</template>
		</Autocomplete>
		<span v-if="props.description" class="block text-xs leading-5 text-gray-600 mt-1">
			{{ props.description }}
		</span>
	</div>
</template>

<script setup>
import { createResource, Autocomplete, FeatherIcon, debounce } from "frappe-ui";
import { ref, computed, watch, onMounted } from "vue";

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
		default: {},
	},
	disabled: {
		type: Boolean,
		default: false,
	},
	label: {
		type: String,
		default: "",
	},
	description: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["update:modelValue"]);

const autocompleteRef = ref(null);
// search_link defaults to 10; a roster has more shift types than that. 49, not 50: the picker shows at
// most 50 rows and the chosen record may be put on top of the list, so 49 keeps the last real row visible.
const PAGE_LENGTH = 49;
const searchText = ref("");

const value = computed({
	get: () => props.modelValue,
	set: (val) => {
		if (typeof val === "string") {
			emit("update:modelValue", val);
		} else {
			emit("update:modelValue", val?.value || "");
		}
	},
});

// one option from a search_link row: the title and the id, as before
const toOption = (doc) => {
	let title = null;
	if (doc.label && doc.label !== doc.value) {
		title = doc.label;
	} else if (doc.description) {
		title = doc.description.split(",")[0];
	}
	return {
		label: title ? `${title} : ${doc.value}` : doc.value,
		value: doc.value,
	};
};

// The chosen record's own label, looked up only when it is NOT in the list that opened (a long list,
// the person chosen sits past the first 50): without it the box would show the bare id, not "Name : ID".
const chosen = createResource({
	url: "frappe.desk.search.search_link",
	method: "POST",
	transform: (data) => data.map(toOption),
});

// The list shown: the chosen record ALWAYS stays in it, with its real label. frappe-ui draws the closed
// box's text from this list, so a chosen record dropped while someone types would leave the box blank
// (design review of 3a860c31e). It is the old behaviour too: the chosen record was always injected.
const shownOptions = computed(() => {
	const list = options.data || [];
	if (!props.modelValue || list.some((o) => o.value === props.modelValue)) return list;
	const label = (chosen.data || []).find((o) => o.value === props.modelValue)?.label;
	return [{ label: label || props.modelValue, value: props.modelValue }, ...list];
});

const options = createResource({
	url: "frappe.desk.search.search_link",
	params: {
		doctype: props.doctype,
		txt: searchText.value,
		filters: props.filters,
		page_length: PAGE_LENGTH,
	},
	method: "POST",
	transform: (data) => data.map(toOption),
	// the chosen record fell outside this page: ask for its own label once
	onSuccess: (data) => {
		const known = (chosen.data || []).some((o) => o.value === props.modelValue);
		if (props.modelValue && !known && !data.some((o) => o.value === props.modelValue)) {
			chosen.update({ params: { doctype: props.doctype, txt: props.modelValue, page_length: 5 } });
			chosen.reload();
		}
	},
});

const reloadOptions = (searchTextVal) => {
	options.update({
		params: {
			txt: searchTextVal,
			doctype: props.doctype,
			filters: props.filters,
			page_length: PAGE_LENGTH,
		},
	});
	options.reload();
};

const handleQueryUpdate = debounce((newQuery) => {
	const val = newQuery || "";
	if (searchText.value === val) return;
	searchText.value = val;
	reloadOptions(val);
}, 300);

// Open on the FULL list, never on a search for the chosen value: a person on "Security A" saw only the
// shifts with "Security" in the name, and every other shift vanished from the picker (HR, 5 Oct 2026).
// The chosen record is kept in the list by the transform above.
onMounted(() => {
	reloadOptions("");
});

watch(
	() => props.doctype,
	() => {
		if (!props.doctype || props.doctype === options.doctype) return;
		reloadOptions("");
	},
);

watch(
	() => props.filters,
	() => reloadOptions(""),
);
</script>
