import { chromium } from 'playwright'; import fs from 'fs'
import { F, states } from './lib.mjs'
const AX=fs.readFileSync('node_modules/axe-core/axe.min.js','utf8')
const T={runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}}
const b=await chromium.launch()
const rows=[]
for(const theme of ['light','dark']){
  const p=await b.newPage({viewport:{width:390,height:844}})
  await p.goto(F); await p.waitForTimeout(250)
  if(theme==='dark') await p.evaluate(()=>window.setTheme('dark'))
  await p.addScriptTag({content:AX})
  for(const st of states()){
    await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(80)
    await st.go(p); await p.waitForTimeout(260)
    const r=await p.evaluate(async t=>{
      const res=await axe.run(document.getElementById('app'),t)
      const V=res.violations.map(v=>v.id+' x'+v.nodes.length+' :: '+v.nodes.slice(0,2).map(n=>n.target.join(' ')+' | '+(n.failureSummary||'').split('\n').filter(x=>x.includes('contrast')||x.includes('Element')).slice(0,1).join('')).join(' ;; '))
      const I=res.incomplete.filter(x=>x.id==='color-contrast').map(x=>'INCOMPLETE contrast x'+x.nodes.length+' :: '+x.nodes.slice(0,3).map(n=>n.target.join(' ')).join(' ;; '))
      // text that is cut off or overflows its box
      const cut=[]
      document.querySelectorAll('#app *').forEach(el=>{
        if(!el.offsetParent) return
        const cs=getComputedStyle(el)
        if(el.scrollWidth>el.clientWidth+1 && cs.overflowX!=='auto' && cs.overflowX!=='scroll'
           && cs.textOverflow!=='ellipsis' && el.children.length===0 && el.textContent.trim())
          cut.push('OVERFLOW '+(el.className||el.tagName)+' '+el.scrollWidth+'>'+el.clientWidth+' "'+el.textContent.trim().slice(0,34)+'"')
      })
      return {V,I,cut:[...new Set(cut)]}
    },T)
    if(r.V.length||r.I.length||r.cut.length) rows.push(theme+'/'+st.id+'\n   '+[...r.V,...r.I,...r.cut].join('\n   '))
  }
  await p.close()
}
console.log(rows.length?rows.join('\n'):'CLEAN')
await b.close()
