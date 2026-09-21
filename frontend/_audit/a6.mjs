/* Why does the sheet snap instead of sliding? Watch the class and the
   transform on the same frames, from the real tap. */
import { chromium } from 'playwright'
import { F } from './lib.mjs'
const b=await chromium.launch()
const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:1})
await p.goto(F); await p.waitForTimeout(300)
await p.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit();window.go('cal')})
await p.waitForTimeout(400)
console.log(await p.evaluate(async ()=>{
  const s=document.getElementById('sheet-day'); const out=[]
  let stop=false
  const tick=()=>{ if(stop) return
    const cs=getComputedStyle(s)
    out.push(`${s.classList.contains('on')?'on':'--'} ${cs.transform.replace(/matrix\(|\)/g,'').split(',').pop().trim()} hidden=${s.hidden}`)
    requestAnimationFrame(tick) }
  // tap the real button, like a finger
  const btn=[...document.getElementById('calgrid').querySelectorAll('button')].find(x=>x.textContent.trim()==='16')
  requestAnimationFrame(tick); btn.click()
  await new Promise(r=>setTimeout(r,500)); stop=true
  return out.slice(0,16).join('\n')
}))
await b.close()
