<template>
	<div class="relative bg-divider">
		<div
			ref="scroller"
			class="relative flex flex-col gap-2.5 p-2.5 max-h-[70vh] overflow-y-auto"
			@scroll="onScroll"
		>
			<!-- pages are appended here as canvases by pdf.js -->
			<div
				v-if="loading"
				class="flex flex-col gap-2 bg-white p-4 aspect-[210/260] animate-pulse"
			>
				<div class="h-2.5 w-3/5 bg-ink-300"></div>
				<div v-for="line in 8" :key="line" class="h-1.5 bg-ink-200"></div>
			</div>
			<div
				v-if="error"
				class="flex flex-col items-center gap-2 bg-surface p-5 text-center"
			>
				<span class="text-[12.5px] text-ink-700">
					{{ __("This PDF could not be displayed here.") }}
				</span>
				<a
					:href="props.fileUrl"
					target="_blank"
					rel="noopener"
					class="border border-accent text-accent px-3 py-2 text-[10px] font-extrabold uppercase tracking-[0.06em] no-underline"
				>
					{{ __("Download") }}
				</a>
			</div>
		</div>

		<div
			v-if="pageCount"
			class="absolute right-2.5 bottom-2.5 px-2 py-1 text-[9.5px] font-extrabold tracking-[0.08em] text-white pointer-events-none"
			style="background: rgba(15, 40, 40, 0.85)"
		>
			{{ currentPage }} / {{ pageCount }}
		</div>
	</div>
</template>

<script setup>
import * as pdfjsLib from "pdfjs-dist"
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url"
import { inject, nextTick, onBeforeUnmount, ref, watch } from "vue"

// Vite-native worker wiring: the URL import is emitted as a real asset, so no
// CDN and no separate worker bundle config is needed.
pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl

const __ = inject("$translate")

const props = defineProps({
	fileUrl: { type: String, required: true },
})

const scroller = ref(null)
const loading = ref(true)
const error = ref(false)
const pageCount = ref(0)
const currentPage = ref(1)

let pdfDoc = null

const clearPages = () => {
	if (!scroller.value) return
	for (const canvas of [...scroller.value.querySelectorAll("canvas")])
		canvas.remove()
}

const render = async () => {
	if (!props.fileUrl) return
	loading.value = true
	error.value = false
	pageCount.value = 0
	currentPage.value = 1

	try {
		await nextTick()
		clearPages()
		// same-origin request — the session cookie covers private files
		pdfDoc = await pdfjsLib.getDocument(props.fileUrl).promise
		pageCount.value = pdfDoc.numPages

		// fit-to-screen: CSS width == container width, backing store multiplied
		// by the device pixel ratio (capped at 2) so text stays crisp
		const containerWidth = Math.max(
			(scroller.value?.clientWidth || 320) - 20,
			240
		)
		const ratio = Math.min(window.devicePixelRatio || 1, 2)

		for (let pageNumber = 1; pageNumber <= pdfDoc.numPages; pageNumber++) {
			const page = await pdfDoc.getPage(pageNumber)
			const scale = containerWidth / page.getViewport({ scale: 1 }).width
			const viewport = page.getViewport({ scale: scale * ratio })

			const canvas = document.createElement("canvas")
			canvas.width = Math.floor(viewport.width)
			canvas.height = Math.floor(viewport.height)
			canvas.style.width = "100%"
			canvas.style.height = "auto"
			canvas.className = "block flex-none bg-white shadow-sm"
			scroller.value?.appendChild(canvas)

			await page.render({
				canvasContext: canvas.getContext("2d"),
				viewport,
			}).promise
		}
		console.info("[SOP] Rendered PDF pages:", pdfDoc.numPages)
	} catch (err) {
		console.warn("[SOP] Failed to render PDF:", err)
		error.value = true
		pageCount.value = 0
	} finally {
		loading.value = false
	}
}

const onScroll = () => {
	const el = scroller.value
	if (!el || !pageCount.value) return
	const canvases = [...el.querySelectorAll("canvas")]
	// the page occupying the upper third of the viewport is "current"
	const marker = el.scrollTop + el.clientHeight * 0.35
	let page = 1
	canvases.forEach((canvas, index) => {
		if (canvas.offsetTop <= marker) page = index + 1
	})
	currentPage.value = page
}

watch(() => props.fileUrl, render, { immediate: true })

onBeforeUnmount(() => {
	pdfDoc?.destroy?.()
	pdfDoc = null
})
</script>
