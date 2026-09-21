import { pathToFileURL } from 'node:url'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { existsSync } from 'node:fs'

// Resolved from this file, not from a machine. The previous value was an
// absolute path under one home directory, so every probe was unrunnable by
// anyone else — including the reader the HANDOFF's verify line is written for.
// The mockup is gitignored (.gitignore:40), so a fresh checkout has the probes
// but not their target; say so rather than failing with a module-shaped error.
const REPO = dirname(dirname(dirname(fileURLToPath(import.meta.url))))
const MOCKUP = join(REPO, 'Nadi PWA UI UX 2.0', 'nadi-2.0-mockup-4.html')
if (!existsSync(MOCKUP)) {
  console.error('mockup not found at ' + MOCKUP + '\n' +
    '"Nadi PWA UI UX 2.0" is gitignored, so it is not in a fresh checkout.\n' +
    'These probes measure that file; without it there is nothing to measure.')
  process.exit(2)
}
export const F = pathToFileURL(MOCKUP).href
export const SCREENS=['home','cal','req','score','more','appr','profile','anns','help','notif','leaveform']
export const SHEETS=['sheet-new','sheet-ann','sheet-day','sheet-fix','sheet-rej']
// every state worth auditing, as a function applied to a fresh page
export function states(){
  const out=[]
  for(const s of SCREENS) out.push({id:'s:'+s, go:async p=>{await p.evaluate(n=>window.go(n),s)}})
  out.push({id:'sheet:new', go:async p=>{await p.evaluate(()=>{window.go('req');window.openSheet('sheet-new')})}})
  out.push({id:'sheet:ann', go:async p=>{await p.evaluate(()=>{window.go('home');window.openSheet('sheet-ann')})}})
  out.push({id:'sheet:day-empty', go:async p=>{await p.evaluate(()=>{window.go('cal');window.openDay(24)})}})
  out.push({id:'sheet:day-fix',   go:async p=>{await p.evaluate(()=>{window.go('cal');window.openDay(8)})}})
  out.push({id:'sheet:day-claim', go:async p=>{await p.evaluate(()=>{window.go('cal');window.openDay(2)})}})
  out.push({id:'sheet:day-work',  go:async p=>{await p.evaluate(()=>{window.go('cal');window.openDay(16)})}})
  out.push({id:'sheet:fix', go:async p=>{await p.evaluate(()=>{window.go('cal');window.openSheet('sheet-fix')})}})
  out.push({id:'sheet:rej', go:async p=>{await p.evaluate(()=>{window.setRole('approver');window.go('appr');window.openSheet('sheet-rej')})}})
  out.push({id:'cal:claim', go:async p=>{await p.evaluate(()=>{window.go('cal');window.segCal('claim')})}})
  out.push({id:'cal:roster',go:async p=>{await p.evaluate(()=>{window.go('cal');window.segCal('roster')})}})
  for(const st of ['load','empty','err']) out.push({id:'req:'+st, go:async p=>{await p.evaluate(k=>window.setState(k),st)}})
  out.push({id:'appr:staffview', go:async p=>{await p.evaluate(()=>{window.setRole('approver');window.go('home')})}})
  out.push({id:'clock:out', go:async p=>{await p.evaluate(()=>{window.go('home');window.toggleClock()})}})
  return out
}
