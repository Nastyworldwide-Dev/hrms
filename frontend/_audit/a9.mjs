/* H — text that comes to rest under chrome.
   The fade at the foot of the screen is honest for text on its way past: you
   scroll, it dissolves, you scroll further and it is gone. It is dishonest for
   text that STOPS there, because there is no further to scroll — the reader is
   left with a half-dissolved line and no way to finish it. The contrast probe
   cannot see this: it now (correctly) excludes faded pixels as intentional, so
   the defect became invisible the moment the fade was added. This asserts the
   floor instead: at maximum scroll, no text box may overlap the fade or the
   tab bar. */
import { chromium } from 'playwright'
import { F, states } from './lib.mjs'
const b=await chromium.launch()
const bad=[]
for(const theme of ['light','dark']){
  const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:1})
  await p.goto(F); await p.waitForTimeout(250)
  await p.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit()})
  if(theme==='dark') await p.evaluate(()=>window.setTheme('dark'))
  for(const st of states()){
    await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(80)
    await st.go(p); await p.waitForTimeout(380)
    await p.evaluate(()=>{const e=document.getElementById('scrollbody');if(e)e.scrollTop=e.scrollHeight})
    await p.waitForTimeout(200)
    for(const r of await p.evaluate(()=>{
      const app=document.querySelector('.app'); if(!app) return []
      const ar=app.getBoundingClientRect()
      const fade=parseFloat(getComputedStyle(app,'::after').height)||0
      const ceiling=ar.bottom-fade            // nothing readable may cross this
      const o=[]
      document.querySelectorAll('.screen.on *').forEach(el=>{
        /* A collapsed <details> keeps its offsetParent and reports a real height,
             so every probe that trusted offsetParent measured text no one can see.
             checkVisibility() is the only API that answers the actual question. */
        if(!el.checkVisibility({contentVisibilityAuto:true,opacityProperty:true,visibilityProperty:true})) return
        if(el.closest('.sr-only')||el.closest('.tabs')||el.closest('.stickycta')) return
        const cs=getComputedStyle(el)
        if(cs.position==='fixed'||cs.position==='absolute') return
        if(cs.visibility==='hidden'||parseFloat(cs.opacity)<0.2) return
        const txt=[...el.childNodes].filter(n=>n.nodeType===3&&n.textContent.trim())
          .map(n=>n.textContent.trim()).join(' ')
        if(!txt) return
        const r=el.getBoundingClientRect()
        if(r.height<4||r.bottom<=ceiling+1) return
        o.push({cls:String(el.className||el.tagName).split(' ')[0],txt:txt.slice(0,34),
          over:Math.round(r.bottom-ceiling)})
      })
      return o
    })) bad.push(`${theme}/${st.id}  +${r.over}px into the fade  .${r.cls}  "${r.txt}"`)
  }
  await p.close()
}
console.log(bad.length?[...new Set(bad)].join('\n'):'NO TEXT RESTS UNDER CHROME')
await b.close()
