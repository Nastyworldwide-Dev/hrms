// Evidence for the open --g-glass-fill ruling (owner question 4).
//
// mockup-4 declares --g-glass-fill: rgba(255,255,255,.86) light AND
// rgba(42,46,56,.86) dark, with a comment claiming .56 drags --g-ink2 from
// 6.2:1 to 3.7:1 over the light field. tokens.json's own description says
// "Light is deliberately more opaque than dark; do not correct (spec 6)".
// The two documents disagree, so this measures both against the SHIPPED
// tokens using the same WCAG math design/gates/contrast.mjs uses.
//
// Run: node design/tools/glass-fill-candidates.mjs  (from the repo root)
//
// Finding, 22 Sep 2026: the mockup's premise does not hold for the shipped
// geometry. Every blob centre sits OUTSIDE the content column, so the
// strongest alpha any of them lands on text is 0.0105 -- ink2 measures 6.36
// flat and 6.34 over the worst blob, a 0.02 delta, not the 2.5 the comment
// describes. Raising light to .86 is therefore a free but pointless +0.27,
// while the dark half of the same proposal FAILS: a #2A2E38 tint at .86
// drops --ink-muted to 3.84:1, under the 4.5 floor, in all three blob cases
// and flat. Recommendation: keep .56/.075. If the effect is wanted, .86
// light alone is safe; the dark value is not adoptable as written.

// Measure the .56/.075 (shipped) vs .86 (mockup-4) glass fill using the
// repo's OWN contrast math, lifted from design/gates/contrast.mjs.
import { readFileSync } from "node:fs";
const tokens = JSON.parse(readFileSync("design/tokens.json","utf8"));

function parse(c){
  if (typeof c !== "string") throw new Error("not a colour: "+c);
  const hex=c.match(/^#([0-9a-fA-F]{6})$/);
  if(hex) return {rgb:[1,3,5].map(i=>parseInt(c.slice(i,i+2),16)),a:1};
  const fn=c.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/);
  if(fn) return {rgb:[+fn[1],+fn[2],+fn[3]],a:fn[4]===undefined?1:+fn[4]};
  throw new Error("unparseable: "+c);
}
const over=(src,bg)=>src.rgb.map((ch,i)=>src.a*ch+(1-src.a)*bg[i]);
function lum([r,g,b]){const lin=[r,g,b].map(ch=>{const s=ch/255;return s<=0.04045?s/12.92:((s+0.055)/1.055)**2.4});return 0.2126*lin[0]+0.7152*lin[1]+0.0722*lin[2];}
function ratio(f,b){const[l1,l2]=[lum(f),lum(b)].sort((a,b)=>b-a);return (l1+0.05)/(l2+0.05);}

const themed=(n,t)=>{const x=tokens["color-themed"][n]||tokens["color-semantic"][n];return x.value[t];};
const constant=n=>tokens["color-constant"][n].value;
const px=(g,n)=>parseFloat(tokens[g][n].value);
const V={w:px("layout","viewport-width"),h:px("layout","viewport-height")};
const G=px("spacing","screen-gutter");

function blob(id){
  const size=px("field",`blob-${id}-size`), r=size/2, f=tokens.field;
  const cx=f[`blob-${id}-left`]?px("field",`blob-${id}-left`)+r:V.w-px("field",`blob-${id}-right`)-r;
  const cy=f[`blob-${id}-top`]?px("field",`blob-${id}-top`)+r:V.h-px("field",`blob-${id}-bottom`)-r;
  return {cx,cy,r,colour:parse(f[`blob-${id}-color`].value)};
}
const alphaAt=(d,r,p)=>(d>=r*0.7?0:p*(1-d/(r*0.7)));
function worst(b){
  const nx=Math.min(Math.max(b.cx,G),V.w-G), ny=Math.min(Math.max(b.cy,0),V.h);
  const d=Math.hypot(b.cx-nx,b.cy-ny);
  return alphaAt(d,b.r,b.colour.a);
}

const INKS=["ink","ink2","ink-muted","ink3","accent-ink","danger-ink"];
const MIN={ink:4.5,ink2:4.5,"ink-muted":4.5,ink3:3.0,"accent-ink":4.5,"danger-ink":4.5};

// candidate fills: [label, light, dark]
const CANDIDATES=[
  ["SHIPPED  .56 / .075w", "rgba(255,255,255,.56)", "rgba(255,255,255,.075)"],
  ["MOCKUP4  .86 / .86dark","rgba(255,255,255,.86)", "rgba(42,46,56,.86)"],
  ["HYBRID   .86 / .075w",  "rgba(255,255,255,.86)", "rgba(255,255,255,.075)"],
];

for(const [label,lightFill,darkFill] of CANDIDATES){
  console.log("\n================ "+label+" ================");
  for(const theme of ["light","dark"]){
    const fill=parse(theme==="light"?lightFill:darkFill);
    const bg=parse(themed("bg",theme)).rgb;
    const flat=over(fill,bg);            // panel over plain app bg
    console.log(`  --- ${theme} ---`);
    // 1. flat panel
    let worstFlat=99, worstFlatName="";
    for(const ink of INKS){
      const r=ratio(parse(themed(ink,theme)).rgb,flat);
      const pass=r>=MIN[ink];
      if(r/MIN[ink] < worstFlat){worstFlat=r/MIN[ink];worstFlatName=`${ink} ${r.toFixed(2)}/${MIN[ink]}`;}
      console.log(`    flat panel   ${ink.padEnd(11)} ${r.toFixed(2)}  min ${MIN[ink]}  ${pass?"PASS":"**FAIL**"}`);
    }
    // 2. panel over the WORST blob (the case .86 exists to fix)
    const op=tokens["color-themed"]["blob-opacity"].value[theme];
    let hardest=null;
    for(const id of ["a","b","c"]){
      const b=blob(id); const a=worst(b);
      if(a<=0) continue;
      const overBg=over({rgb:b.colour.rgb,a:a*op},bg);
      const surf=over(fill,overBg);
      for(const ink of INKS){
        const r=ratio(parse(themed(ink,theme)).rgb,surf);
        if(!hardest||r/MIN[ink]<hardest.norm) hardest={id,ink,r,min:MIN[ink],norm:r/MIN[ink]};
        const pass=r>=MIN[ink];
        if(!pass) console.log(`    blob ${id.toUpperCase()}       ${ink.padEnd(11)} ${r.toFixed(2)}  min ${MIN[ink]}  **FAIL**`);
      }
    }
    if(hardest) console.log(`    WORST over blob: ${hardest.ink} on blob ${hardest.id.toUpperCase()} = ${hardest.r.toFixed(2)} (min ${hardest.min}) ${hardest.r>=hardest.min?"PASS":"**FAIL**"}`);
    // 3. how much backdrop still shows
    console.log(`    backdrop visible through veil: ${((1-fill.a)*100).toFixed(1)}%`);
    // 4. does the panel separate from the page bg? (non-text UI, 3:1 is the a11y floor for boundaries)
    console.log(`    panel-vs-page separation: ${ratio(flat,bg).toFixed(3)}x luminance ratio`);
  }
}
