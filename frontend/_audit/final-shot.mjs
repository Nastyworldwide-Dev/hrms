import { chromium } from 'playwright'
import { F } from './lib.mjs'
const b=await chromium.launch()
for(const theme of ['light','dark']){
  const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:2})
  await p.goto(F); await p.waitForTimeout(350)
  await p.evaluate(()=>{document.querySelector('.mk-bar').style.display='none';window.fit&&window.fit()})
  if(theme==='dark') await p.evaluate(()=>window.setTheme('dark'))
  const shots={home:()=>window.go('home'), req:()=>window.go('req'),
    day:()=>{window.go('cal');window.openDay(8)}, appr:()=>{window.setRole('approver');window.go('appr')}}
  for(const [k,fn] of Object.entries(shots)){
    await p.evaluate(()=>window.closeSheets&&window.closeSheets()); await p.waitForTimeout(100)
    await p.evaluate(fn); await p.waitForTimeout(600)
    await p.screenshot({path:`/tmp/fin-${theme}-${k}.png`})
  }
  // bottom of home, scrolled to rest — the CLASS H case
  await p.evaluate(()=>{window.closeSheets&&window.closeSheets();window.setRole('staff');window.go('home')})
  await p.waitForTimeout(400)
  await p.evaluate(()=>{const e=document.getElementById('scrollbody');e.scrollTop=e.scrollHeight})
  await p.waitForTimeout(350)
  await p.screenshot({path:`/tmp/fin-${theme}-bottom.png`})
  await p.close()
}
console.log('ok')
await b.close()
