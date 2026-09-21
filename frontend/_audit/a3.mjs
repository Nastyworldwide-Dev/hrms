/* Three defect families the contrast probe cannot see.
   B — clipped text. Must catch it whether or not text-overflow:ellipsis is set:
       an ellipsis on a one-line label is a design choice, an ellipsis (or a
       hard cut) on a sentence the reader needs is a defect. Measured by
       scrollWidth/scrollHeight against clientWidth/clientHeight.
   C — screen depth. How many viewports each screen costs, and whether a card
       is cut by the fold rather than ending before it.
   D — sheet stability. Whether opening the same sheet for different days
       moves the sheet's top edge, and whether the page behind it scrolls. */
import { chromium } from 'playwright'
import { F, states } from './lib.mjs'
const b=await chromium.launch()
const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:1})
await p.goto(F); await p.waitForTimeout(300)
await p.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit()})

console.log('=== B: CLIPPED TEXT ===')
const clip=[]
for(const st of states()){
  await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(70)
  await st.go(p); await p.waitForTimeout(350)
  const r=await p.evaluate(()=>{
    const o=[]
    document.querySelectorAll('#app *').forEach(el=>{
      /* A collapsed <details> keeps its offsetParent and reports a real height,
           so every probe that trusted offsetParent measured text no one can see.
           checkVisibility() is the only API that answers the actual question. */
      if(!el.checkVisibility({contentVisibilityAuto:true,opacityProperty:true,visibilityProperty:true})) return
      if(el.classList.contains('sr-only')||el.closest('.sr-only')) return
      const cs=getComputedStyle(el)
      if(cs.visibility==='hidden') return
      const txt=[...el.childNodes].filter(n=>n.nodeType===3&&n.textContent.trim())
        .map(n=>n.textContent.trim()).join(' ')
      if(!txt) return
      // Two ways text gets cut, and the mockup has both.
      //
      // 1. INERT ELLIPSIS. text-overflow:ellipsis only applies to a block
      //    container. On display:inline it does nothing: the span lays out at
      //    its full natural width, overflows its parent, and is hard-cut by
      //    whatever ancestor clips — with no "…" to tell the reader that a
      //    word is missing. This is the defect in the owner's screenshot.
      // 2. Real clipping by an ancestor box.
      const box=el.getBoundingClientRect()
      const inertEllipsis = cs.textOverflow==='ellipsis'
        && /^inline$|^ruby/.test(cs.display)
      // nearest ANCESTOR that actually clips (self does not clip itself)
      // hidden|clip LOSES the text. auto|scroll only moves it — the reader can
      // still reach it, so an ancestor scroller is not a clipping defect and
      // everything below the fold must not be reported as cut.
      let clipEl=null, cc=el.parentElement
      while(cc && cc.id!=='app'){
        const s2=getComputedStyle(cc)
        if(/auto|scroll/.test(s2.overflowX)||/auto|scroll/.test(s2.overflowY)) break
        if(/hidden|clip/.test(s2.overflowX)||/hidden|clip/.test(s2.overflowY)){ clipEl=cc; break }
        cc=cc.parentElement
      }
      const selfClips = /hidden|clip/.test(cs.overflowX) && !/^inline$|^ruby/.test(cs.display)
      const selfCutW = selfClips ? el.scrollWidth-el.clientWidth : 0
      const selfCutH = (/hidden|clip/.test(cs.overflowY)||(cs.webkitLineClamp&&cs.webkitLineClamp!=='none'))
        ? el.scrollHeight-el.clientHeight : 0
      let cutW=selfCutW, cutH=selfCutH, where='self',
          how=cs.textOverflow==='ellipsis'&&!inertEllipsis?'ellipsis':'HARD CUT'
      if(clipEl){
        const cr=clipEl.getBoundingClientRect()
        const aw=Math.round(Math.max(box.right-cr.right, cr.left-box.left))
        const ah=Math.round(Math.max(box.bottom-cr.bottom, cr.top-box.top))
        if(aw>cutW){ cutW=aw; where='.'+String(clipEl.className||clipEl.tagName).split(' ')[0]
          how=inertEllipsis?'HARD CUT (ellipsis inert on display:inline)':'HARD CUT' }
        if(ah>cutH){ cutH=ah; where='.'+String(clipEl.className||clipEl.tagName).split(' ')[0]; how='HARD CUT' }
      }
      // 4px is layout rounding, not a defect
      if(cutW>4) o.push(['W',el.className||el.tagName,txt,cutW,how+' by '+where])
      else if(cutH>4) o.push(['H',el.className||el.tagName,txt,cutH,how+' by '+where])
      else if(inertEllipsis&&box.width>el.parentElement.getBoundingClientRect().width+4)
        o.push(['W',el.className||el.tagName,txt,Math.round(box.width-el.parentElement.getBoundingClientRect().width),'ellipsis INERT on display:inline'])
    })
    return o
  })
  for(const [ax,cls,txt,over,how] of r)
    clip.push(`${st.id}  ${ax}+${over}px ${how}  .${String(cls).split(' ')[0]}  "${txt.slice(0,58)}"`)
}
console.log(clip.length?[...new Set(clip)].join('\n'):'no clipped text')

console.log('\n=== C: SCREEN DEPTH (390x844) ===')
for(const st of states()){
  await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(70)
  await st.go(p); await p.waitForTimeout(320)
  const d=await p.evaluate(()=>{
    const e=document.getElementById('scrollbody'); if(!e) return null
    e.scrollTop=0
    const vh=e.clientHeight, sh=e.scrollHeight
    // a block cut by the first fold: starts above it, ends below it
    const fold=e.getBoundingClientRect().top+vh
    // A card crossing the fold is only a defect when it is the LAST one: then
    // the screen ends mid-card and looks broken. A card with more cards under
    // it is a scroll affordance — the standard cue that a list continues, and
    // removing it would make a scrollable screen look complete. So the flag is
    // reported for information and only judged against what follows it.
    let cut=null
    e.querySelectorAll('.screen.on .card,.screen.on .panel,.screen.on .row,.screen.on .ann').forEach(c=>{
      const r=c.getBoundingClientRect()
      if(r.top<fold-8&&r.bottom>fold+8&&!cut){
        const isLast=r.bottom>=sh+e.getBoundingClientRect().top-24
        cut=(c.className.split(' ')[0])+' "'+c.textContent.trim().slice(0,32).replace(/\s+/g,' ')+'"'
          +(isLast?'   <-- LAST CARD: screen ends mid-card':'   (affordance: more below)')}
    })
    return {vh,sh,screens:+(sh/vh).toFixed(2),cut}
  })
  if(d) console.log(`${st.id.padEnd(18)} ${d.screens} viewports (${d.sh}px / ${d.vh}px)${d.cut?'   CUT BY FOLD: '+d.cut:''}`)
}

console.log('\n=== D: SHEET STABILITY ===')
for(const day of [2,8,16,24]){
  await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(250)
  const before=await p.evaluate(()=>{const e=document.getElementById('scrollbody');return {top:e.scrollTop}})
  await p.evaluate(()=>window.go('cal')); await p.waitForTimeout(250)
  const t0=Date.now()
  await p.evaluate(d=>window.openDay(d),day)
  const frames=[]
  for(let i=0;i<10;i++){
    await p.waitForTimeout(45)
    frames.push(await p.evaluate(()=>{
      const s=document.getElementById('sheet-day'); const r=s.getBoundingClientRect()
      return [Math.round(r.top),Math.round(r.height),document.getElementById('scrollbody').scrollTop]
    }))
  }
  await p.waitForTimeout(400)
  const fin=await p.evaluate(()=>{
    const s=document.getElementById('sheet-day'); const r=s.getBoundingClientRect()
    return {top:Math.round(r.top),h:Math.round(r.height),
      body:document.getElementById('scrollbody').scrollTop,
      sheetScroll:s.scrollHeight-s.clientHeight}
  })
  console.log(`day ${String(day).padStart(2)}  settles top=${fin.top} h=${fin.h}  innerScroll=${fin.sheetScroll}px  bodyScroll ${before.top}->${fin.body}`)
}
await b.close()
