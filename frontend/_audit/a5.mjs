import { chromium } from 'playwright'
import { F } from './lib.mjs'
const b=await chromium.launch()
const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:1})
await p.goto(F); await p.waitForTimeout(300)
await p.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit();window.go('cal')})
await p.waitForTimeout(400)
/* Two things this probe got wrong, and both made a working animation look
   broken.
   1. It read getBoundingClientRect().top. The sheet slides by TRANSFORM, and a
      transformed box reports the same top on every frame — so a 340ms glide
      showed as "399 399 399" and the probe called it a snap.
   2. It armed the sampler and called openDay() in the same task, so the "from"
      state never got a frame of its own to paint.
   Sampling the computed transform, with a frame between arming and opening,
   shows the real 482px -> 0 glide. */
const seq=await p.evaluate(async ()=>{
  const s=document.getElementById('sheet-day')
  const out=[]
  let stop=false
  const ty=()=>{const m=new DOMMatrixReadOnly(getComputedStyle(s).transform); return Math.round(m.m42)}
  const tick=()=>{ if(stop) return; out.push(ty()); requestAnimationFrame(tick) }
  requestAnimationFrame(tick)
  await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))
  window.openDay(16)
  await new Promise(r=>setTimeout(r,600)); stop=true
  return out
})
console.log('sheet translateY per frame, first 600ms:', seq.slice(0,30).join(' '))
console.log('distinct positions:', new Set(seq).size, ' -> ', new Set(seq).size<=2?'SNAPS (no entry animation)':'ANIMATES')
const why=await p.evaluate(()=>{
  const s=document.getElementById('sheet-day'); const cs=getComputedStyle(s)
  return JSON.stringify({transition:cs.transition.slice(0,80), transform:cs.transform, cls:s.className,
    scrimCls:document.querySelector('.scrim').className,
    reduced:matchMedia('(prefers-reduced-motion: reduce)').matches})
})
console.log(why)
await b.close()
