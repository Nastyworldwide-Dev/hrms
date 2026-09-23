// The title on a request form: the person's word for the request, the same
// word Requests and Approvals use (utils/requestKind.js). A doctype name is a
// table, not something people say, and "New Leave Application" was the first
// thing an employee read on the form (ruling L4: doctype names and IDs never
// reach users). New and existing forms share the word: the screen itself
// already shows whether it is being filled in or read.
import { REQUEST_KIND } from "./requestKind.js"

//: Forms that are not requests, so REQUEST_KIND does not name them.
const OTHER_FORMS = {
	"Employee Issue": "Issue",
	"Shift Assignment": "Shift",
}

export function formTitle(doctype, isNew) {
	const word = REQUEST_KIND[doctype] || OTHER_FORMS[doctype]
	if (!word) console.warn("[formTitle] no plain word for", doctype, isNew ? "(new)" : "")
	return word || "Request"
}
