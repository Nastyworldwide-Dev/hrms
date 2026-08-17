# End-to-end tests

Everything else guarding this app is static or unit-level. Those prove *shapes*
are right — that an endpoint declares the argument its caller sends, that a
mirrored row never fires `on_submit`. None of them can answer **"does an employee
see their leave balance?"**

Until these existed, the only thing answering that was a person opening the app
and taking a screenshot. That is why faults survived for a week: verification was
manual, so confidence decayed the moment anyone stopped looking.

## Running them

```bash
cd frontend
yarn install
npx playwright install chromium        # once — downloads the browser

HRMS_E2E_URL=https://verifica-live.s.frappe.cloud \
HRMS_E2E_USER=you@nastyworldwide.com \
HRMS_E2E_PASSWORD='...' \
yarn test:e2e
```

`HRMS_E2E_URL` defaults to `http://localhost:8000`. Without credentials the two
tests that need a session skip and the other two still run — so the suite is
useful against any site, signed in or not.

## What each test is for

Every one corresponds to an incident this project actually had.

| Test | The failure it would have caught |
|---|---|
| login offers email + password | reported as "SSO-only login" |
| forgot password is not rejected | 400 `CSRFTokenError` — recovery route dead |
| a failed balance says so | 18 screens rendered nothing on error |
| the leave balance renders | 486 Leave Allocations were never mirrored |

The third needs no data and no credentials: it **forces** a 500 and asserts the
app admits it. A test that needs a broken server is usually a bad test — here the
broken server is the subject.

## Adding to this

Add a test when something breaks in a way a user could see, not for every
endpoint. The value of this suite is that each case is a real scar; a suite of
speculative cases costs the same to run and teaches nobody anything.
