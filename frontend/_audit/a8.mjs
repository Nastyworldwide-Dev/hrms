/* G — ragged column edge.
   Every probe passed a home screen whose two action rows were 259px and 295px
   wide in a 338px column, because no probe ever compared siblings to each
   other. Only the screenshot caught it. A <button> shrink-wraps where a <div>
   fills, so the same class measured two different widths depending on which
   element it was built from. This asserts that surfaces stacked in one column
   share one left edge and one width, in every state. */
import { chromium } from 'playwright'
import { F, states } from './lib.mjs'
const b=await chromium.launch()
const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:1})
await p.goto(F); await p.waitForTimeout(300)
await p.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit()})
const bad=[]
for(const st of states()){
  await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(70)
  await st.go(p); await p.waitForTimeout(320)
  const r=await p.evaluate(()=>{
    const o=[]
    const scopes=[...document.querySelectorAll('.screen.on, .sheet.on')]
    for(const sc of scopes){
      const kids=[...sc.children].filter(el=>{
        if(!el.offsetParent) return false
        const cs=getComputedStyle(el)
        if(cs.position==='absolute'||cs.position==='fixed') return false
        // only full-width SURFACES; a heading row or an inline control is free
        return /panel|card|ann|cta|ghost|seg|tgrid|grid2|stickycta/.test(el.className)
      })
      if(kids.length<2) continue
      const w=kids.map(el=>Math.round(el.getBoundingClientRect().width))
      const x=kids.map(el=>Math.round(el.getBoundingClientRect().left))
      const wide=Math.max(...w), narrow=Math.min(...w)
      if(wide-narrow>2||Math.max(...x)-Math.min(...x)>2){
        kids.forEach((el,i)=>{ if(w[i]<wide-2||x[i]>Math.min(...x)+2)
          o.push([el.className.split(' ')[0]||el.tagName,w[i],wide,
            (el.textContent||'').trim().replace(/\s+/g,' ').slice(0,30)]) })
      }
    }
    return o
  })
  for(const [c,w,wide,t] of r) bad.push(`${st.id}  .${c} is ${w}px in a ${wide}px column  "${t}"`)
}
console.log(bad.length?[...new Set(bad)].join('\n'):'COLUMN EDGE CLEAN')

/* G2 — ragged INNER edge.
   The same defect one level down. A leading pill shrink-wraps its label, so a
   list of dates ("Thu 18", "Fri 19", "Mon 22") gave every title a different
   left edge — a 12px spread that reads as three misaligned rows rather than one
   column. A8 above compares the OUTER edge of stacked surfaces; this compares
   the text start of stacked rows inside one surface. The screenshot found it;
   neither existing probe could. */
{
  const { chromium: _c } = await import('playwright')
  const bad=[]
  for(const theme of ['light','dark']){
    const p2=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:1})
    await p2.goto(F); await p2.waitForTimeout(250)
    await p2.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit()})
    if(theme==='dark') await p2.evaluate(()=>window.setTheme('dark'))
    for(const st of states()){
      await p2.evaluate(()=>window.closeSheets&&window.closeSheets()); await p2.waitForTimeout(80)
      await st.go(p2); await p2.waitForTimeout(350)
      for(const r of await p2.evaluate(()=>{
        const o=[]
        document.querySelectorAll('.screen.on .panel,.sheet.on .panel,.screen.on .card,.sheet.on .card').forEach(pn=>{
          const rows=[...pn.querySelectorAll(':scope > .row')]
          if(rows.length<2) return
          // Skip rows that are not painted. A role-gated row (.hide) still
          // answers querySelectorAll and reports left=0, which looked like a
          // 95px misalignment against its visible siblings.
          const vis=el=>el.checkVisibility({contentVisibilityAuto:true,opacityProperty:true,visibilityProperty:true})
          const lefts=rows.filter(vis).map(r=>{const g=r.querySelector('.grow')
            return (g&&vis(g))?Math.round(g.getBoundingClientRect().left):null}).filter(x=>x!=null)
          if(lefts.length<2) return
          const spread=Math.max(...lefts)-Math.min(...lefts)
          if(spread>2) o.push({spread,txt:pn.textContent.trim().slice(0,30).replace(/\s+/g,' ')})
        })
        return o
      })) bad.push(`${theme}/${st.id}  ${r.spread}px spread  "${r.txt}"`)
    }
    await p2.close()
  }
  console.log(bad.length?[...new Set(bad)].join('\n'):'INNER EDGE CLEAN')
}

await b.close()
