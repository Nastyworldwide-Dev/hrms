/* Responsive + interaction. Measured in CSS pixels (offsetWidth/Height), never
   getBoundingClientRect: the mockup renders inside #fit's transform:scale, so
   a compliant 44px control reads as 32px through a rect. */
import { chromium } from 'playwright'
import { F, states } from './lib.mjs'
const b=await chromium.launch()
const WIDTHS=[[320,568],[360,740],[390,844],[414,896],[768,1024],[1024,768],[1280,900],[1440,900]]
console.log('=== E: LAYOUT AT EVERY SUPPORTED WIDTH ===')
for(const [w,h] of WIDTHS){
  const p=await b.newPage({viewport:{width:w,height:h},deviceScaleFactor:1})
  await p.goto(F); await p.waitForTimeout(350)
  await p.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit()})
  const bad=[]
  for(const st of states()){
    await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(50)
    await st.go(p); await p.waitForTimeout(220)
    const r=await p.evaluate(()=>{
      const o=[]
      const app=document.getElementById('app'), ar=app.getBoundingClientRect()
      const tb=document.querySelector('.tabbar')
      if(tb&&getComputedStyle(tb).display!=='none'){
        const t=tb.getBoundingClientRect()
        if(t.bottom>ar.bottom+2) o.push(`tabbar ${Math.round(t.bottom-ar.bottom)}px below frame`)
        if(t.top>ar.bottom) o.push('tabbar entirely off-screen')
      }
      // horizontal overflow of the app frame
      document.querySelectorAll('#app *').forEach(el=>{
        if(!el.offsetParent) return
        // A box that pokes out of an overflow:hidden ancestor is clipped, not
        // overflowing the page — the decorative .field blobs live this way.
        let cc=el.parentElement, clipped=false
        while(cc&&cc.id!=='app'){ const s2=getComputedStyle(cc)
          if(/hidden|clip|auto|scroll/.test(s2.overflowX)){clipped=true;break} cc=cc.parentElement }
        if(clipped) return
        const r=el.getBoundingClientRect()
        if(r.width>2&&(r.right>ar.right+2||r.left<ar.left-2))
          o.push(`x-overflow .${String(el.className||el.tagName).split(' ')[0]} ${Math.round(Math.max(r.right-ar.right,ar.left-r.left))}px`)
      })
      return [...new Set(o)]
    })
    for(const x of r) bad.push(`${st.id}: ${x}`)
  }
  console.log(`${w}x${h}: ${bad.length?[...new Set(bad)].slice(0,6).join(' | '):'clean'}`)
  await p.close()
}

console.log('\n=== F: TAP TARGETS (CSS px) + FOCUS VISIBILITY ===')
const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:1})
await p.goto(F); await p.waitForTimeout(300)
await p.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit()})
const small=[], nofocus=[]
for(const st of states()){
  await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(60)
  await st.go(p); await p.waitForTimeout(260)
  const r=await p.evaluate(()=>{
    const s=[],nf=[]
    document.querySelectorAll('#app button,#app a,#app input,#app select,#app textarea,#app summary,#app [tabindex]').forEach(el=>{
      if(!el.offsetParent) return
      if(el.classList.contains('sr-only')||el.closest('.sr-only')) return
      const w=el.offsetWidth, h=el.offsetHeight
      const lbl=(el.getAttribute('aria-label')||el.textContent.trim()||el.tagName).slice(0,26)
      // a pseudo-element can extend the hit area; check for one before judging
      const be=getComputedStyle(el,'::before'), ae=getComputedStyle(el,'::after')
      const ext=[be,ae].some(x=>x.content!=='none'&&(parseFloat(x.inset)<0||/-/.test(x.inset||'')))
      if((w<44||h<44)&&!ext) s.push(`.${String(el.className||el.tagName).split(' ')[0]} ${w}x${h} "${lbl}"`)
      el.focus()
      const f=getComputedStyle(el)
      const hasRing=(f.outlineStyle!=='none'&&parseFloat(f.outlineWidth)>0)||f.boxShadow!=='none'
      if(!hasRing) nf.push(`.${String(el.className||el.tagName).split(' ')[0]} "${lbl}"`)
      el.blur()
    })
    return {s:[...new Set(s)],nf:[...new Set(nf)]}
  })
  r.s.forEach(x=>small.push(x)); r.nf.forEach(x=>nofocus.push(x))
}
console.log('under 44px:', [...new Set(small)].length ? '\n  '+[...new Set(small)].join('\n  ') : 'none')
console.log('no focus ring:', [...new Set(nofocus)].length ? '\n  '+[...new Set(nofocus)].join('\n  ') : 'none')
await b.close()
