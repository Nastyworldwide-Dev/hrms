<template>
	<div class="relative bg-divider">
		<div
			ref="scroller"
			role="group"
			:aria-label="__('PDF preview, page {0} of {1}', [currentPage, pageCount || 1])"
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
				<span class="text-card-title text-ink-700">
					{{ __("This PDF could not be displayed here.") }}
				</span>
				<span v-if="errorDetail" class="text-caption text-ink-500 break-all">
					{{ errorDetail }}
				</span>
				<a
					:href="props.fileUrl"
					target="_blank"
					rel="noopener"
					class="border border-accent text-accent px-3 py-2 text-micro-label font-extrabold uppercase no-underline"
				>
					{{ __("Download") }}
				</a>
			</div>
		</div>

		<div
			v-if="pageCount"
			class="absolute right-2.5 bottom-2.5 px-2 py-1 text-caption font-extrabold text-white pointer-events-none"
			style="background: rgba(15, 40, 40, 0.85)"
		>
			{{ currentPage }} / {{ pageCount }}
		</div>
	</div>
</template>

<script setup>
// legacy build: no Promise.withResolvers requirement (older Android
// WebViews) and installs under the FC bench image's Node 18
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs"
// ?worker: Vite bundles the worker into its own .js chunk — a raw ?url .mjs
// asset 404s on Frappe Cloud's asset serving and pdf.js dies workerless
import PdfWorker from "pdfjs-dist/legacy/build/pdf.worker.min.mjs?worker"
import { inject, nextTick, onBeforeUnmount, ref, watch } from "vue"

// each viewer owns its worker: pdf.js destroys the worker with the document,
// so a shared GlobalWorkerOptions.workerPort dies on the first unmount and
// every later getDocument hangs on the dead port (page "never loads")
let workerThread = null
let pdfWorker = null

const destroyPdf = () => {
	try {
		pdfDoc?.destroy()
	} catch (err) {
		console.warn("[SOP] pdf doc destroy failed:", err)
	}
	try {
		pdfWorker?.destroy()
	} catch (err) {
		console.warn("[SOP] pdf worker destroy failed:", err)
	}
	try {
		workerThread?.terminate()
	} catch (err) {
		console.warn("[SOP] worker thread terminate failed:", err)
	}
	pdfDoc = null
	pdfWorker = null
	workerThread = null
}

const __ = inject("$translate")

const props = defineProps({
	fileUrl: { type: String, required: true },
})

const scroller = ref(null)
const loading = ref(true)
const error = ref(false)
const errorDetail = ref("")
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
		destroyPdf()
		workerThread = new PdfWorker()
		pdfWorker = new pdfjsLib.PDFWorker({ port: workerThread })
		// same-origin request — the session cookie covers private files
		pdfDoc = await pdfjsLib.getDocument({
			url: props.fileUrl,
			worker: pdfWorker,
		}).promise
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
		errorDetail.value = err?.message || String(err)
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

onBeforeUnmount(destroyPdf)
</script>
