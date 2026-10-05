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
			<!-- The closed box draws its OWN text. frappe-ui reads the box text from the list it has already
			     filtered by the typed words, so a chosen record that does not match what is typed would
			     blank the box behind the open popover (design review of d94faafcd). Same look as its own button. -->
			<template #target="{ togglePopover }">
				<div class="w-full">
					<!-- frappe-ui's Autocomplete has no disabled state of its own (pointer-events-none only stops the
					     mouse), so this button carries it: Tab then Enter cannot open a disabled picker, and it looks
					     disabled. The name is the label plus the chosen value, so a screen reader hears both. -->
					<button
						type="button"
						:disabled="disabled"
						:aria-label="label ? (chosenLabel ? `${label}: ${chosenLabel}` : label) : undefined"
						aria-haspopup="listbox"
						class="flex h-7 w-full items-center justify-between gap-2 rounded bg-surface-gray-2 px-2 py-1 transition-colors hover:bg-surface-gray-3 border border-transparent focus:border-outline-gray-4 focus:outline-none focus:ring-2 focus:ring-outline-gray-3 disabled:opacity-50 disabled:cursor-not-allowed"
						@click="() => togglePopover()"
					>
						<span class="truncate text-base leading-5 text-ink-gray-8" v-if="chosenLabel">{{ chosenLabel }}</span>
						<span class="text-base leading-5 text-ink-gray-4" v-else></span>
						<FeatherIcon name="chevron-down" class="h-4 w-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
					</button>
				</div>
			</template>
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

// The text the closed box shows: the chosen record's label, whatever is typed in the search.
const chosenLabel = computed(() => {
	if (!props.modelValue) return "";
	return shownOptions.value.find((o) => o.value === props.modelValue)?.label || props.modelValue;
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
