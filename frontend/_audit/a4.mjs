/* "Calendar has glitchy on click dates. jumpy."
   Two candidates: the grid itself reflowing under the tap, or the sheet that
   the tap opens. Measure both, frame by frame, while tapping several days. */
import { chromium } from 'playwright'
import { F } from './lib.mjs'
const b=await chromium.launch()
const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:1})
await p.goto(F); await p.waitForTimeout(300)
await p.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit();window.go('cal')})
await p.waitForTimeout(400)

console.log('=== GRID GEOMETRY UNDER TAP ===')
const base=await p.evaluate(()=>{
  const g=document.getElementById('calgrid'); const r=g.getBoundingClientRect()
  const cells=[...g.children].slice(0,7).map(c=>{const b=c.getBoundingClientRect();return [Math.round(b.width),Math.round(b.height)]})
  return {grid:[Math.round(r.width),Math.round(r.height)],cells,scr:document.getElementById('scrollbody').scrollTop}
})
console.log('before tap:',JSON.stringify(base))
for(const d of [2,8,16,24]){
  await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(300)
  await p.evaluate(dd=>{const g=document.getElementById('calgrid');const b=[...g.querySelectorAll('button')].find(x=>x.textContent.trim()===String(dd)); b&&b.click()},d)
  await p.waitForTimeout(420)
  const a=await p.evaluate(()=>{
    const g=document.getElementById('calgrid'); const r=g.getBoundingClientRect()
    const cells=[...g.children].slice(0,7).map(c=>{const b=c.getBoundingClientRect();return [Math.round(b.width),Math.round(b.height)]})
    return {grid:[Math.round(r.width),Math.round(r.height)],cells,scr:document.getElementById('scrollbody').scrollTop}
  })
  const same=JSON.stringify(a.grid)===JSON.stringify(base.grid)&&JSON.stringify(a.cells)===JSON.stringify(base.cells)
  console.log(`day ${String(d).padStart(2)}: grid ${same?'STABLE':'MOVED '+JSON.stringify(a)}  bodyScroll ${base.scr}->${a.scr}`)
}

console.log('\n=== SHEET OPEN, FRAME BY FRAME (top edge px) ===')
for(const d of [2,8,16,24]){
  await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(420)
  await p.evaluate(dd=>window.openDay(dd),d)
  const seq=[]
  for(let i=0;i<14;i++){
    seq.push(await p.evaluate(()=>{
      const s=document.getElementById('sheet-day'); const r=s.getBoundingClientRect()
      return Math.round(r.top)+'/'+Math.round(r.height)
    }))
    await p.waitForTimeout(40)
  }
  console.log(`day ${String(d).padStart(2)}: ${seq.join(' ')}`)
}

console.log('\n=== CONTENT WRITTEN BEFORE OR AFTER THE OPEN? ===')
console.log(await p.evaluate(()=>{
  const src=window.openDay.toString()
  const iOpen=src.indexOf('openSheet')
  const writes=[...src.matchAll(/innerHTML|classList\.(add|remove|toggle)|textContent/g)].map(m=>m.index)
  return `openSheet at char ${iOpen}; ${writes.filter(i=>i<iOpen).length} DOM writes before it, ${writes.filter(i=>i>iOpen).length} after`
}))
await b.close()
