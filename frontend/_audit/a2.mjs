/* Real-pixel contrast for the Nadi 2.0 mockup.
   Why this exists: axe-core returns INCOMPLETE, never a verdict, wherever a
   backdrop-filter or a scrim is involved — which is exactly where the sheets
   live. "0 violations" was therefore a false clean bill of health.

   Three rules this probe learned the hard way, each one after it produced a
   physically impossible number:
     1. Measure the background with the GLYPHS REMOVED, so a sample can never
        land on a letter stroke.
     2. Take geometry and pixels from the SAME layout — collect after the ink
        is hidden, screenshot immediately after, never re-query in between.
     3. A bounding box is not a painted pixel. Hit-test every sample point:
        it counts only if the element itself (or something it paints inside)
        is what the compositor actually put there. An ancestor does not count —
        a row scrolled out of the phone frame hit-tests to .stage, which
        contains everything, and would sample the page backdrop.
   A self-test on a known-flat lime button gates the whole run. */
import { chromium } from 'playwright'
import { F, states } from './lib.mjs'

const lum=(r,g,b)=>{const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(r)+.7152*f(g)+.0722*f(b)}
const ratio=(a,b)=>{const L=Math.max(a,b),l=Math.min(a,b);return (L+.05)/(l+.05)}
const NOINK='#app *{color:transparent!important;-webkit-text-fill-color:transparent!important;text-shadow:none!important}'

// Runs with the ink already hidden. Returns geometry + verified sample points.
const COLLECT=`(()=>{
  const vw=innerWidth, vh=innerHeight, res=[]
  const m0=getComputedStyle(document.getElementById('fit')).transform
  const scale=m0==='none'?1:(parseFloat(m0.split('(')[1])||1)
  // Overlays that PAINT over content without taking hit-tests: the toast has
  // pointer-events:none, so elementFromPoint walks straight through it and
  // reports the row underneath while the screenshot shows the toast. Any
  // stacked layer is collected here and its area excluded for everything
  // outside it. Text under a scrim or a sheet is dimmed on purpose; it is not
  // a contrast defect, and neither is text behind a toast.
  // An element's paint depth is the highest z-index on its own chain: a row
  // inside the sheet inherits the sheet's 41 and is NOT covered by the scrim's
  // 40, even though the scrim overlaps every pixel of it.
  const depth=el=>{let d=0,e=el
    while(e&&e.id!=='app'){const c=getComputedStyle(e);const z=parseInt(c.zIndex,10)
      if(c.position!=='static'&&!isNaN(z)) d=Math.max(d,z); e=e.parentElement}
    return d}
  const overlays=[]
  document.querySelectorAll('#app *').forEach(el=>{
    const cs=getComputedStyle(el)
    if(cs.position==='static') return
    const z=parseInt(cs.zIndex,10)
    if(!(z>=10)) return
    if(cs.visibility==='hidden'||parseFloat(cs.opacity)<0.05) return
    const r=el.getBoundingClientRect()
    if(r.width<2||r.height<2) return
    overlays.push({el,r,z})
  })
  // The bottom fade is a PSEUDO-element (.app::after), so querySelectorAll can
  // never return it and the loop above cannot see it. It paints over content
  // exactly like the tab bar does, so it is registered by hand from the same
  // geometry the stylesheet uses. Without this the probe reads a row halfway
  // through the gradient and calls an intentional cue a contrast defect.
  const appEl=document.querySelector('.app')
  if(appEl&&getComputedStyle(document.body).getPropertyValue('--x')!=='skip'){
    const ar=appEl.getBoundingClientRect()
    const fh=parseFloat(getComputedStyle(appEl,'::after').height)||0
    if(fh>2) overlays.push({el:appEl,r:{left:ar.left,right:ar.right,
      top:ar.bottom-fh,bottom:ar.bottom},z:29,pseudo:true})
  }
  document.querySelectorAll('#app *').forEach(el=>{
    /* A collapsed <details> keeps its offsetParent and reports a real height,
         so every probe that trusted offsetParent measured text no one can see.
         checkVisibility() is the only API that answers the actual question. */
    if(!el.checkVisibility({contentVisibilityAuto:true,opacityProperty:true,visibilityProperty:true})) return
    const cs=getComputedStyle(el)
    if(cs.visibility==='hidden'||parseFloat(cs.opacity)<0.2) return
    if(el.classList.contains('sr-only')||el.closest('.sr-only')) return
    const txt=[...el.childNodes].filter(n=>n.nodeType===3&&n.textContent.trim())
      .map(n=>n.textContent.trim()).join(' ')
    if(!txt) return
    const r=el.getBoundingClientRect()
    if(r.width<4||r.height<4) return
    const myDepth=depth(el)
    const pts=[]
    for(let k=0;k<5;k++) for(const fy of [0.42,0.5,0.58]){
      const x=r.x+r.width*(0.2+0.15*k), y=r.y+r.height*fy
      if(x<1||y<1||x>vw-1||y>vh-1) continue
      const hit=document.elementFromPoint(x,y)
      if(!hit) continue
      if(hit!==el && !el.contains(hit)) continue
      // 2px of slack on every edge. A rect says the toast starts at y=716; the
      // compositor, with a 0.7px transform offset and a 999px radius, already
      // painted 60% of it into row 715. Sampling that row read a blend of ink
      // and toast and reported 3.6:1 against a surface nobody can see.
      const M=2
      if(overlays.some(o=>o.z>myDepth&&(o.pseudo||(!o.el.contains(el)&&o.el!==el))
        &&x>=o.r.left-M&&x<=o.r.right+M&&y>=o.r.top-M&&y<=o.r.bottom+M)) continue
      pts.push([Math.round(x),Math.round(y)])
    }
    if(!pts.length) return
    const m=(el.dataset.inkColor||'').match(/[\\d.]+/g)
    if(!m) return
    res.push({t:txt.slice(0,34), c:[+m[0],+m[1],+m[2]], pts,
      size:parseFloat(cs.fontSize)/scale, weight:+cs.fontWeight,
      sel:(typeof el.className==='string'&&el.className?'.'+el.className.trim().split(/\\s+/)[0]:el.tagName)})
  })
  return res
})()`

// The ink colour has to be captured BEFORE it is hidden, and parked on the node.
const STAMP=`document.querySelectorAll('#app *').forEach(el=>{el.dataset.inkColor=getComputedStyle(el).color})`

async function measure(p){
  await p.evaluate(STAMP)
  const tag=await p.addStyleTag({content:NOINK})
  await p.waitForTimeout(140)
  const items=await p.evaluate(COLLECT)
  const buf=await p.screenshot()
  await p.evaluate(()=>{const s=[...document.querySelectorAll('style')].pop();s&&s.remove()})
  if(!items.length) return []
  const bgs=await p.evaluate(async ({src,items})=>{
    const img=new Image(); img.src=src; await img.decode()
    const c=document.createElement('canvas'); c.width=img.width; c.height=img.height
    const g=c.getContext('2d',{willReadFrequently:true}); g.drawImage(img,0,0)
    return items.map(it=>it.pts.map(([x,y])=>{
      const d=g.getImageData(x,y,1,1).data; return [d[0],d[1],d[2],x,y]
    }))
  },{src:'data:image/png;base64,'+buf.toString('base64'),items})
  return items.map((it,i)=>({it,bg:bgs[i]}))
}

const b=await chromium.launch()
const out=[]; let checked=0
for(const theme of ['light','dark']){
 const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:1})
 await p.goto(F); await p.waitForTimeout(250)
 await p.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit()})
 if(theme==='dark') await p.evaluate(()=>window.setTheme('dark'))

 // Gate: a flat lime primary is ~14:1 on every pixel of its face. If the probe
 // reads it unevenly or low, it is not sampling the button and nothing below
 // this line can be trusted.
 await p.evaluate(()=>window.go('home')); await p.waitForTimeout(350)
 {
  const m=(await measure(p)).find(x=>x.it.sel==='.cta')
  const rs=m.bg.map(s=>ratio(lum(...m.it.c),lum(s[0],s[1],s[2])))
  const lo=Math.min(...rs), hi=Math.max(...rs)
  if((hi-lo)/hi>0.08||lo<10){ console.error(`SELF-TEST FAIL (${theme}): flat button read ${lo.toFixed(2)}..${hi.toFixed(2)}`); process.exit(1) }
  console.error(`self-test ${theme}: .cta "${m.it.t}" = ${lo.toFixed(2)}:1 over ${rs.length} verified points`)
 }

 for(const st of states()){
  await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(80)
  await st.go(p); await p.waitForTimeout(380)
  const maxScroll=await p.evaluate(()=>{const e=document.getElementById('scrollbody');return e?e.scrollHeight-e.clientHeight:0})
  // Always finish at maxScroll. Stepping by 700 from the top left every short
  // screen measured ONLY at scrollTop 0 — the one position where its last row
  // is still below the fold. The position that actually matters is where the
  // content comes to REST, and that is the bottom.
  const offsets=[]
  for(let i=0;i*700<maxScroll&&i<7;i++) offsets.push(i*700)
  if(!offsets.length||offsets[offsets.length-1]!==maxScroll) offsets.push(maxScroll)
  for(const off of offsets){
    await p.evaluate(y=>{const e=document.getElementById('scrollbody');if(e)e.scrollTop=y},off)
    await p.waitForTimeout(150)
    for(const {it,bg} of await measure(p)){
      if(!bg.length) continue
      checked++
      const fg=lum(...it.c)
      let worst=99, wpx=null
      for(const sp of bg){ const r=ratio(fg,lum(sp[0],sp[1],sp[2])); if(r<worst){worst=r;wpx=sp} }
      const big=it.size>=24||(it.size>=18.66&&it.weight>=700)
      const need=big?3:4.5
      if(worst<need-0.05)
        out.push(`${theme}/${st.id}  ${worst.toFixed(2)}:1 (need ${need})  ${it.sel} ${it.size.toFixed(1)}px/${it.weight} "${it.t}"  fg=rgb(${it.c}) bg=rgb(${wpx.slice(0,3)}) @${wpx[3]},${wpx[4]}`)
    }
  }
 }
 await p.close()
}
console.error(`sampled ${checked} verified on-screen text boxes`)
console.log(out.length?[...new Set(out)].join('\n'):'NO LOW-CONTRAST TEXT')
await b.close()
