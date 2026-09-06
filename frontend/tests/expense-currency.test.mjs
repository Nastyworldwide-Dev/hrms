import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

const source = readFileSync(
	fileURLToPath(
		new URL("../src/views/expense_claim/Form.vue", import.meta.url),
	),
	"utf8",
);

// The employee expense flow files a claim in the COMPANY currency at rate 1 and
// hides the Currency / Exchange Rate inputs. A regression (found in the astra
// review) took the currency from the employee's SALARY currency instead: a
// USD-salaried employee filing against an MYR company stored currency=USD while
// exchange_rate stayed 1, so the backend treated 1 USD as 1 MYR — wrong base
// totals. These pin the currency source to the company and keep the salary path
// from creeping back.

test("currency is taken from the company, not the employee's salary", () => {
	assert.match(
		source,
		/expenseClaim\.value\.currency\s*=\s*companyCurrency\.value/,
	);
});

test("the salary-currency path is gone", () => {
	assert.doesNotMatch(source, /get_salary_currency/);
	assert.doesNotMatch(source, /employeeCurrency/);
});

test("existing claims keep their saved currency (new claims only are stamped)", () => {
	// the currency watcher must bail on an existing doc so a loaded claim's
	// currency / exchange_rate are never clobbered on the client
	assert.match(
		source,
		/companyCurrency\.value,\s*expenseClaim\.value\.company[\s\S]{0,160}if \(props\.id\) return/,
	);
});
