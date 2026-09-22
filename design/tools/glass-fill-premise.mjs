// Companion to glass-fill-candidates.mjs: tests the mockup's OWN stated
// numbers rather than just comparing candidates. Answers "is the premise
// true?" instead of "which value scores better".
//
// Run: node design/tools/glass-fill-premise.mjs  (from the repo root)
//
// Finding, 22 Sep 2026: the premise is false for the shipped field geometry.
// The three blob centres sit at x=-65, x=448 and x=-47 against a content
// column of x=[15,375] -- all three OUTSIDE it, each one 62-80px away with a
// gradient reach of 63-81px, so the alpha that actually lands on text is
// 0.0045 / 0.0042 / 0.0105. The mockup's "6.2 -> 3.7" would need roughly a
// blob centre INSIDE the column; measured here the drop is 6.36 -> 6.34.
// The dark claim ("2.0:1 over the lime blob") is the same shape: reproducible
// only if a blob sat at FULL strength behind a panel (ink2 1.26 in that
// hypothetical), which the shipped placement never allows.

// Test the mockup's OWN stated numbers against the shipped tokens.
import { readFileSync } from "node:fs";
const tokens=JSON.parse(readFileSync("design/tokens.json","utf8"));
function parse(c){const hex=c.match(/^#([0-9a-fA-F]{6})$/);if(hex)return{rgb:[1,3,5].map(i=>parseInt(c.slice(i,i+2),16)),a:1};const fn=c.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/);return{rgb:[+fn[1],+fn[2],+fn[3]],a:fn[4]===undefined?1:+fn[4]};}
const over=(s,b)=>s.rgb.map((c,i)=>s.a*c+(1-s.a)*b[i]);
const lum=([r,g,b])=>{const l=[r,g,b].map(c=>{const s=c/255;return s<=0.04045?s/12.92:((s+0.055)/1.055)**2.4});return .2126*l[0]+.7152*l[1]+.0722*l[2];};
const ratio=(f,b)=>{const[a,c]=[lum(f),lum(b)].sort((x,y)=>y-x);return (a+.05)/(c+.05);};
const themed=(n,t)=>(tokens["color-themed"][n]||tokens["color-semantic"][n]).value[t];
const px=(g,n)=>parseFloat(tokens[g][n].value);
const V={w:px("layout","viewport-width"),h:px("layout","viewport-height")},G=px("spacing","screen-gutter");

function blob(id){const size=px("field",`blob-${id}-size`),r=size/2,f=tokens.field;
  const cx=f[`blob-${id}-left`]?px("field",`blob-${id}-left`)+r:V.w-px("field",`blob-${id}-right`)-r;
  const cy=f[`blob-${id}-top`]?px("field",`blob-${id}-top`)+r:V.h-px("field",`blob-${id}-bottom`)-r;
  return {cx,cy,r,colour:parse(f[`blob-${id}-color`].value),id};}

console.log("=== Where do the shipped blobs actually sit vs the content column? ===");
console.log(`viewport ${V.w}x${V.h}, gutter ${G} -> content column x=[${G}, ${V.w-G}]`);
for(const id of ["a","b","c"]){
  const b=blob(id);
  const nx=Math.min(Math.max(b.cx,G),V.w-G), ny=Math.min(Math.max(b.cy,0),V.h);
  const d=Math.hypot(b.cx-nx,b.cy-ny);
  const reach=b.r*0.7;
  const a=d>=reach?0:b.colour.a*(1-d/reach);
  console.log(`  blob ${id.toUpperCase()}: centre (${b.cx.toFixed(0)},${b.cy.toFixed(0)}) r=${b.r.toFixed(0)} | dist to column ${d.toFixed(0)}px | gradient reach ${reach.toFixed(0)}px | alpha reaching text = ${a.toFixed(4)}`);
}

console.log("\n=== The mockup's claim: 'at .56 ink2 drops 6.2:1 -> 3.7:1' (light) ===");
for(const [lbl,fillS] of [["shipped .56","rgba(255,255,255,.56)"],["mockup .86","rgba(255,255,255,.86)"]]){
  const fill=parse(fillS), bg=parse(themed("bg","light")).rgb, op=tokens["color-themed"]["blob-opacity"].value.light;
  const flat=over(fill,bg);
  console.log(`  ${lbl}: ink2 on FLAT panel = ${ratio(parse(themed("ink2","light")).rgb,flat).toFixed(2)}`);
  for(const id of ["a","b","c"]){
    const b=blob(id);
    const nx=Math.min(Math.max(b.cx,G),V.w-G),ny=Math.min(Math.max(b.cy,0),V.h);
    const d=Math.hypot(b.cx-nx,b.cy-ny),reach=b.r*.7;
    const a=d>=reach?0:b.colour.a*(1-d/reach);
    if(a<=0){console.log(`    over blob ${id.toUpperCase()}: blob never reaches the column (alpha 0)`);continue;}
    const surf=over(fill,over({rgb:b.colour.rgb,a:a*op},bg));
    console.log(`    over blob ${id.toUpperCase()}: ink2 = ${ratio(parse(themed("ink2","light")).rgb,surf).toFixed(2)}`);
  }
}

console.log("\n=== The mockup's dark claim: '.075 white left ink2 at 2.0:1 over the lime blob' ===");
for(const [lbl,fillS] of [["shipped .075w","rgba(255,255,255,.075)"],["mockup .86 dark tint","rgba(42,46,56,.86)"]]){
  const fill=parse(fillS), bg=parse(themed("bg","dark")).rgb, op=tokens["color-themed"]["blob-opacity"].value.dark;
  console.log(`  ${lbl}: ink2 FLAT = ${ratio(parse(themed("ink2","dark")).rgb,over(fill,bg)).toFixed(2)} | ink-muted FLAT = ${ratio(parse(themed("ink-muted","dark")).rgb,over(fill,bg)).toFixed(2)}`);
  // worst case: what if a blob DID sit at full strength behind the panel?
  const lime=parse(tokens.field["blob-a-color"].value);
  const full=over(fill,over({rgb:lime.rgb,a:lime.a*op},bg));
  console.log(`    hypothetical blob-A at FULL strength behind panel: ink2 = ${ratio(parse(themed("ink2","dark")).rgb,full).toFixed(2)}`);
}
