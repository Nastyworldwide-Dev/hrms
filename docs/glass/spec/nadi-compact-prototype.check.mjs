import { chromium } from '../../../frontend/node_modules/@playwright/test/index.mjs';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
const artifact=name=>fileURLToPath(new URL(name,import.meta.url));
const browser=await chromium.launch({headless:true});
const page=await browser.newPage();
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const url=new URL('nadi-compact-prototype.html',import.meta.url).href;
await page.goto(url);await page.evaluate(()=>document.fonts.ready);
const pages=await page.locator('#screen option').evaluateAll(es=>es.map(e=>e.value));
const overflows=[];
for(const width of [320,390,768,1440]){
 await page.setViewportSize({width,height:844});
 for(const theme of ['light','dark']){
  await page.evaluate(theme=>document.body.classList.toggle('dark',theme==='dark'),theme);
  for(const key of pages){
   await page.selectOption('#screen',key);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
   if(overflow)overflows.push({width,theme,key});
  }
 }
}
await page.setViewportSize({width:390,height:844});await page.selectOption('#screen','home');
await page.evaluate(()=>document.body.classList.remove('dark'));
const sopBottom=await page.getByRole('button',{name:'IT equipment care Pinned · General'}).evaluate(e=>e.getBoundingClientRect().bottom);
const navTop=await page.locator('#bottom').evaluate(e=>e.getBoundingClientRect().top);
await page.locator('.review').evaluate(e=>e.hidden=true);
await page.addStyleTag({content:'.review[hidden]{display:none}'});
await page.screenshot({path:artifact('nadi-compact-home-light.png')});
await page.evaluate(()=>document.body.classList.add('dark'));
await page.screenshot({path:artifact('nadi-compact-home-dark.png')});
await page.locator('.review').evaluate(e=>e.hidden=false);
await page.evaluate(()=>document.body.classList.remove('dark'));
await page.selectOption('#screen','assets');await page.screenshot({path:artifact('nadi-compact-assets.png')});await page.getByRole('button',{name:'Requests · 1',exact:true}).click();
if(!await page.getByRole('button',{name:/External monitor/}).isVisible())throw Error('asset request segment failed');
await page.selectOption('#screen','asset');await page.getByRole('button',{name:'Report a problem',exact:true}).click();
if(await page.locator('#issue-team').inputValue()!=='IT')throw Error('asset context team missing');
if(!(await page.locator('input[name=title]').inputValue()).includes('AST-0042'))throw Error('asset title context missing');
await page.screenshot({path:artifact('nadi-compact-new-issue.png')});
await page.locator('textarea').fill('Connection fails after wake');await page.getByRole('button',{name:'Send issue',exact:true}).click();
if(!await page.getByRole('status').isVisible())throw Error('demo form failed');
await page.locator('#issue-team').selectOption('HR');await page.locator('#issue-type').selectOption('Leave Balance Discrepancy');
if(!await page.getByLabel('Balance expected').isVisible())throw Error('conditional fields missing');
await page.selectOption('#screen','helpdesk');await page.getByRole('button',{name:'IT',exact:true}).click();
if(await page.locator('#issue-results .row').count()!==1)throw Error('IT filter failed');
await page.getByPlaceholder('Search title or issue number').fill('no-match');if(!await page.locator('#no-results').isVisible())throw Error('empty search failed');
await page.selectOption('#screen','home');await page.locator('#bottom [data-go=assets]').click();
if(await page.locator('#screen').inputValue()!=='assets')throw Error('bottom navigation failed');
await page.selectOption('#screen','request');await page.getByLabel('Asset category').selectOption('Monitor');await page.getByLabel('Needed by').fill('2026-09-20');await page.getByLabel('Reason').fill('Need a second screen for reviews');await page.getByRole('button',{name:'Send request',exact:true}).click();
if(!(await page.getByRole('status').textContent()).includes('no real record'))throw Error('asset request form failed');
const axePath=artifact('../../../frontend/node_modules/axe-core/axe.min.js');await page.addScriptTag({path:axePath});
const a11y=[];
for(const theme of ['light','dark']){
 await page.evaluate(theme=>document.body.classList.toggle('dark',theme==='dark'),theme);
 for(const key of pages){
  await page.selectOption('#screen',key);
  const result=await page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))});
  if(result.length)a11y.push({theme,key,violations:result});
 }
}
const result={screenCount:pages.length,layoutCases:pages.length*8,errors,overflows,homeSopBottom:sopBottom,bottomNavTop:navTop,sopAboveNav:sopBottom<navTop,interactionChecks:9,a11yCases:pages.length*2,a11y};
fs.writeFileSync(artifact('nadi-compact-prototype-checks.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));await browser.close();
if(errors.length||overflows.length||a11y.length||sopBottom>=navTop)process.exitCode=1;
