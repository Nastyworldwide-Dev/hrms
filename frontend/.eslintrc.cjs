module.exports = {
	root: true,
	env: {
		es2021: true,
		node: true,
	},
	globals: {
		// Replaced at build time by vite.config.js's `define`, so it exists in
		// the bundle and nowhere in the source. Declared readonly: writing to
		// it would be writing to a literal.
		__APP_BUILD__: "readonly",
		__APP_VERSION__: "readonly",
	},
	extends: [
		"eslint:recommended",
		"plugin:vue/vue3-essential",
		"plugin:prettier/recommended",
	],
	parserOptions: {
		// 2022 for top-level await — the *.test.js files use it to await a
		// mock.module() import before the test body runs (node:test convention
		// used throughout frontend/src/**/__tests__). 2020 parsed those as a
		// syntax error, which is why ESLint never actually ran clean here.
		ecmaVersion: 2022,
		sourceType: "module",
	},
	rules: {
		"no-console": process.env.NODE_ENV === "production" ? "warn" : "off",
		"no-debugger": process.env.NODE_ENV === "production" ? "warn" : "off",
		"vue/no-deprecated-slot-attribute": "off",
		"vue/multi-word-component-names": "off",
		// Matches the convention already in use throughout src/ (e.g.
		// `onSuccess(_data)`, `(_value) => {...}`) for a required callback
		// parameter the handler genuinely never reads — codifying it here
		// instead of deleting each call site to a bare `()`.
		"no-unused-vars": ["error", { args: "after-used", argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
	},
	plugins: ["vue", "prettier"],
}
