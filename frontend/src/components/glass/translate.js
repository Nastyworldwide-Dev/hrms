import { getCurrentInstance } from "vue"

// The app registers `__` as a global property (translationsPlugin), which is
// why TabButtons.vue can call it bare in a template. A Glass component that
// does the same THROWS wherever the plugin is absent — the specimen route
// mounted standalone, a unit test, an SSR render. Resolve it defensively and
// fall back to the untranslated string, which is what `__` returns anyway when
// no translation exists.
export function useTranslate() {
	const translate = getCurrentInstance()?.appContext.config.globalProperties.__
	return typeof translate === "function" ? translate : (text) => text
}
