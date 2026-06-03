const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.defineLayout({ name: "W", width: 13.33, height: 7.5 });
pres.layout = "W";
pres.author = "Piyush Tiwari";
pres.title = "Cascade Model — Supervisor Review";

// ---- paths ----------------------------------------------------------------
const FIGDIR = "/Users/piyush/code/System_Identification_DC_Motor/figures/";
const OUT    = "/Users/piyush/code/System_Identification_DC_Motor/slides/cascade_review.pptx";

// ---- palette --------------------------------------------------------------
const INK="0F2440", INK2="1B3A5B", BLUEMUTE="7FA8C9", ICE="CADCFC",
      TEAL="0F766E", TEAL_BG="D6F0EC", TEAL_LINE="9FD3CC",
      AMBER="B45309", AMBER_BG="FBE8D3", AMBER_LINE="E8C49B",
      RED="B91C1C", RED_BG="F6D9D6",
      SLATE="475569", BODY="1E293B", MUTE="64748B",
      CARD="EEF2F6", CBORDER="D8E0E8", LINE="CBD5E1", WHITE="FFFFFF";
const HEAD="Trebuchet MS", BODYF="Calibri", MONO="Consolas";
const M=0.7, CW=13.33-2*M;            // content width 11.93
const sh = () => ({type:"outer", color:"0F2440", blur:7, offset:3, angle:135, opacity:0.12});

// ---- numbering ------------------------------------------------------------
let SLIDEN = 0;                        // physical slide counter (drives footer)

// ---- helpers --------------------------------------------------------------
// Build a base + subscript (+ optional tail) rich-text run array. Runs inherit
// font/size/colour from the host addText box; only the middle run is subscript.
function sub(base, sb, tail){
  const r=[{text:base},{text:sb,options:{subscript:true}}];
  if(tail) r.push({text:tail});
  return r;
}
function footer(slide,n){
  slide.addText("System Identification of a DC Gearmotor & L298N Driver",
    {x:M,y:7.04,w:9,h:0.3,fontFace:BODYF,fontSize:9,color:MUTE,align:"left",valign:"middle",margin:0});
  slide.addText(String(n),
    {x:13.33-M-0.6,y:7.04,w:0.6,h:0.3,fontFace:BODYF,fontSize:9,color:MUTE,align:"right",valign:"middle",margin:0});
}
function darkSlide(){
  SLIDEN++;
  const s=pres.addSlide();
  s.background={color:INK};
  return s;
}
function scaffold(kicker,kickColor,title,say){
  SLIDEN++;
  const s=pres.addSlide();
  s.background={color:WHITE};
  s.addText(kicker.toUpperCase(),
    {x:M,y:0.5,w:CW,h:0.32,fontFace:HEAD,fontSize:12.5,bold:true,color:kickColor,charSpacing:3,align:"left",valign:"middle",margin:0});
  s.addText(title,
    {x:M,y:0.9,w:CW,h:1.18,fontFace:HEAD,fontSize:28,bold:true,color:INK,align:"left",valign:"top",margin:0});
  footer(s,SLIDEN);
  if(say) s.addNotes("SAY: "+say);
  return s;
}
function card(slide,x,y,w,h,fill,border){
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE,
    {x,y,w,h,fill:{color:fill||WHITE},line:{color:border||CBORDER,width:1},rectRadius:0.07,shadow:sh()});
}
function infoCard(slide,x,y,w,h,header,headerColor,lines,opts){
  opts=opts||{};
  card(slide,x,y,w,h,opts.fill||WHITE,opts.border||CBORDER);
  slide.addText(header,
    {x:x+0.22,y:y+0.16,w:w-0.44,h:0.4,fontFace:HEAD,fontSize:13.5,bold:true,color:headerColor||INK,align:"left",valign:"middle",margin:0});
  const arr=lines.map(t=>({text:t,options:{bullet:{indent:12},breakLine:true,paraSpaceAfter:6,
    fontSize:opts.fontSize||12.5,color:opts.color||BODY,fontFace:BODYF}}));
  slide.addText(arr,{x:x+0.24,y:y+0.62,w:w-0.48,h:h-0.76,valign:"top",margin:0});
}
function stat(slide,x,y,w,h,value,valColor,label){
  card(slide,x,y,w,h,WHITE,CBORDER);
  slide.addText(value,
    {x:x+0.08,y:y+0.12,w:w-0.16,h:h*0.55,fontFace:HEAD,fontSize:(value.length>7?28:38),bold:true,color:valColor,align:"center",valign:"middle",margin:0});
  slide.addText(label,
    {x:x+0.14,y:y+h*0.60,w:w-0.28,h:h*0.36,fontFace:BODYF,fontSize:11.5,color:SLATE,align:"center",valign:"top",margin:0});
}
function pill(slide,x,y,w,h,fill,txt){
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE,{x,y,w,h,fill:{color:fill},rectRadius:Math.min(0.12,h/2)});
  slide.addText(txt,{x:x+0.1,y,w:w-0.2,h,fontFace:HEAD,fontSize:13,bold:true,color:WHITE,align:"center",valign:"middle",margin:0});
}
function arrow(slide,x1,y,x2){
  slide.addShape(pres.shapes.LINE,{x:x1,y,w:x2-x1,h:0,line:{color:INK,width:2.25,endArrowType:"triangle"}});
}
function block(slide,x,y,w,h,fill,border,title,subtitle,tColor){
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:border,width:1.75},rectRadius:0.09,shadow:sh()});
  slide.addText(title,{x:x+0.15,y:y+0.16,w:w-0.3,h:0.55,fontFace:HEAD,fontSize:15,bold:true,color:tColor,align:"center",valign:"middle",margin:0});
  slide.addText(subtitle,{x:x+0.15,y:y+h-0.56,w:w-0.3,h:0.45,fontFace:MONO,fontSize:13,color:tColor,align:"center",valign:"middle",margin:0});
}
// Aspect-preserving, centered image placement. The box (bx,by,bw,bh) is the
// available area; the image is scaled to fit inside it without distortion and
// centred; a hugging frame (image rect + framePad) is drawn behind it.
function addFig(slide, bx, by, bw, bh, file, pxW, pxH, opts){
  opts=opts||{};
  const ar=pxW/pxH;
  let w=bw, h=w/ar;
  if(h>bh){ h=bh; w=h*ar; }
  const x=bx+(bw-w)/2, y=by+(bh-h)/2;
  if(opts.frame!==false){
    const fp=opts.framePad!==undefined?opts.framePad:0.08;
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE,
      {x:x-fp,y:y-fp,w:w+2*fp,h:h+2*fp,fill:{color:opts.fill||WHITE},
       line:{color:opts.line||CBORDER,width:1},rectRadius:0.04,
       shadow: opts.shadow===false?undefined:sh()});
  }
  slide.addImage({path:FIGDIR+file, x, y, w, h});
  return {x,y,w,h};
}
function figCaption(slide,x,y,w,txt){
  slide.addText(txt,{x,y,w,h:0.34,fontFace:BODYF,fontSize:10.5,italic:true,color:SLATE,align:"center",valign:"top",margin:0});
}

// ===========================================================================
// SLIDE 1 — TITLE (dark)
// ===========================================================================
let s=darkSlide();
s.addText("M.TECH THESIS REVIEW  ·  CONTROL SYSTEMS  ·  IIT KANPUR",
  {x:M,y:0.95,w:CW,h:0.4,fontFace:HEAD,fontSize:13,bold:true,color:BLUEMUTE,charSpacing:3,align:"left",margin:0});
s.addText("System Identification of a DC Gearmotor and L298N Driver",
  {x:M,y:1.6,w:CW,h:1.25,fontFace:HEAD,fontSize:37,bold:true,color:WHITE,align:"left",valign:"top",margin:0});
s.addText("A validated cascade model with region-dependent dynamics",
  {x:M,y:2.92,w:CW,h:0.55,fontFace:HEAD,fontSize:20,italic:true,color:ICE,align:"left",margin:0});
s.addShape(pres.shapes.ROUNDED_RECTANGLE,{x:M,y:3.78,w:CW,h:0.98,fill:{color:INK2},line:{color:"2C5273",width:1},rectRadius:0.07});
s.addText([
  {text:"The claim:  ",options:{bold:true,color:WHITE}},
  {text:"the plant is a cascade — a direction-specific driver block, then a near-symmetric motor block — and the split is earned from the data, not assumed.",options:{color:"DCE7F5"}}
],{x:M+0.28,y:3.78,w:CW-0.56,h:0.98,fontFace:BODYF,fontSize:15,valign:"middle",margin:0});
s.addText([
  {text:"Piyush Tiwari",options:{bold:true,color:WHITE,fontSize:15,breakLine:true}},
  {text:"Roll 241040099  ·  M.Tech, Electrical Engineering",options:{color:BLUEMUTE,fontSize:12}}
],{x:M,y:5.25,w:6.2,h:0.9,fontFace:BODYF,valign:"top",margin:0});
s.addText([
  {text:"Supervisor: Prof. Soumya Ranjan Sahoo",options:{color:BLUEMUTE,fontSize:12,breakLine:true}},
  {text:"Co-Supervisor: Dr. Abhilash Patel    ·    May 2026",options:{color:BLUEMUTE,fontSize:12}}
],{x:7.1,y:5.25,w:CW-6.4,h:0.9,fontFace:BODYF,valign:"top",align:"left",margin:0});
s.addText("12 V · 60:1 gearmotor    |    L298N H-bridge    |    600-PPR encoder    |    Arduino Uno R4 Minima",
  {x:M,y:6.55,w:CW,h:0.35,fontFace:MONO,fontSize:11,color:BLUEMUTE,align:"left",margin:0});
s.addNotes("SAY: This is a review of completed work — open-loop identification plus a closed-loop test — and I'm asking for approval to write it up. One structural question drove the whole thesis: is this plant one black box, or a cascade of physical blocks?");

// ===========================================================================
// SLIDE 2 — THE SPINE + cascade diagram
// ===========================================================================
s=scaffold("The one result","0F2440","Asymmetry and drift live in the driver. The motor is clean.",
  "Here's the one thing to leave with. The large directional asymmetry and the only measurable session drift BOTH localise to the cheap L298N driver — up to 2.2x near the deadzone — while the motor block is symmetric to within 9% and reproducible to 1%. Asymmetry confined to one identifiable block is exactly what earns the cascade. I'll point back to this slide all talk.");
// signal labels + arrows + blocks
s.addText("PWM\ncmd",{x:0.7,y:2.95,w:1.05,h:0.85,fontFace:MONO,fontSize:13,bold:true,color:INK,align:"center",valign:"middle",margin:0});
arrow(s,1.85,3.38,2.1);
block(s,2.15,2.7,3.7,1.35,AMBER_BG,AMBER,"STATIC DRIVER BLOCK",sub("PWM  →  V","motor"),AMBER);
s.addText(sub("V","motor"),{x:5.9,y:2.62,w:1.55,h:0.4,fontFace:MONO,fontSize:12,bold:true,color:SLATE,align:"center",valign:"bottom",margin:0});
arrow(s,5.9,3.38,7.5);
block(s,7.55,2.7,3.7,1.35,TEAL_BG,TEAL,"MOTOR DYNAMIC BLOCK",sub("V","motor","  →  RPM"),TEAL);
arrow(s,11.3,3.38,11.75);
s.addText("RPM",{x:11.55,y:3.45,w:1.05,h:0.4,fontFace:MONO,fontSize:13,bold:true,color:INK,align:"left",valign:"middle",margin:0});
// captions
s.addText([
  {text:"hysteretic deadzone",options:{bullet:{indent:11},breakLine:true,color:AMBER,fontSize:12.5,fontFace:BODYF,paraSpaceAfter:3}},
  {text:"asymmetric up to 2.2×",options:{bullet:{indent:11},breakLine:true,color:AMBER,fontSize:12.5,fontFace:BODYF,paraSpaceAfter:3}},
  {text:"the only measurable session drift",options:{bullet:{indent:11},color:AMBER,fontSize:12.5,fontFace:BODYF}}
],{x:2.25,y:4.2,w:3.55,h:0.9,valign:"top",margin:0});
s.addText([
  {text:"FOPDT, region-dependent τ",options:{bullet:{indent:11},breakLine:true,color:TEAL,fontSize:12.5,fontFace:BODYF,paraSpaceAfter:3}},
  {text:"symmetric to within 9%",options:{bullet:{indent:11},breakLine:true,color:TEAL,fontSize:12.5,fontFace:BODYF,paraSpaceAfter:3}},
  {text:"reproducible to ≈1%",options:{bullet:{indent:11},color:TEAL,fontSize:12.5,fontFace:BODYF}}
],{x:7.65,y:4.2,w:3.55,h:0.9,valign:"top",margin:0});
pill(s,2.15,5.2,3.7,0.52,AMBER,"asymmetry + drift live HERE");
pill(s,7.55,5.2,3.7,0.52,TEAL,"clean & reproducible");
s.addText("Asymmetry confined to one identifiable block is exactly what earns the cascade — this is contribution one.",
  {x:M,y:5.98,w:CW,h:0.55,fontFace:BODYF,fontSize:14,italic:true,color:BODY,align:"left",valign:"middle",margin:0});

// ===========================================================================
// SLIDE 3 — THE QUESTION + ladder of models
// ===========================================================================
s=scaffold("The question","B45309","The question is structural: one black box, or a cascade of physical blocks?",
  "I didn't assume the cascade. The L298N rig departs from the textbook ideal in five ways, and I fixed three candidate models in advance — naive LTI, static-plus-one-time-constant, and static-plus-region-dependent dynamics. The data picks the rung. That ladder is the backbone of the whole talk.");
s.addText("Five departures from the textbook ideal",{x:M,y:2.2,w:5.7,h:0.4,fontFace:HEAD,fontSize:14.5,bold:true,color:INK,margin:0});
s.addText([
  {text:"Driver voltage loss — droops below supply",options:{bullet:{indent:12},breakLine:true,fontSize:13.5,color:BODY,fontFace:BODYF,paraSpaceAfter:9}},
  {text:"Hysteretic deadzone with fwd/rev breakaway asymmetry",options:{bullet:{indent:12},breakLine:true,fontSize:13.5,color:BODY,fontFace:BODYF,paraSpaceAfter:9}},
  {text:"Forward/reverse gain mismatch",options:{bullet:{indent:12},breakLine:true,fontSize:13.5,color:BODY,fontFace:BODYF,paraSpaceAfter:9}},
  {text:"Operating-point-dependent dynamics",options:{bullet:{indent:12},breakLine:true,fontSize:13.5,color:BODY,fontFace:BODYF,paraSpaceAfter:9}},
  {text:"A small command-to-response delay",options:{bullet:{indent:12},fontSize:13.5,color:BODY,fontFace:BODYF}}
],{x:M,y:2.7,w:5.6,h:2.6,valign:"top",margin:0});
pill(s,M,5.55,5.0,0.5,AMBER,"The data picks the rung — not assumed");
// ladder cards
s.addText("A ladder of three models, fixed at the outset",{x:6.8,y:2.2,w:5.83,h:0.4,fontFace:HEAD,fontSize:14.5,bold:true,color:INK,margin:0});
function ladder(slide,y,h,tag,desc,hi){
  card(slide,6.8,y,5.83,h, hi?TEAL_BG:WHITE, hi?TEAL:CBORDER);
  slide.addText([
    {text:tag+"  ",options:{bold:true,color:hi?TEAL:INK,fontSize:14}},
    {text:desc,options:{color:BODY,fontSize:12.5}}
  ],{x:7.0,y:y+0.08,w:5.45,h:h-0.16,fontFace:BODYF,valign:"middle",margin:0});
}
ladder(s,2.68,0.9,"Model A","single global LTI, no static block — the straw-man baseline",false);
ladder(s,3.68,0.9,"Model B","static block + one global time constant",false);
ladder(s,4.68,1.32,"Model C  ✓","static block + region- & operating-point-dependent FOPDT — the winner",true);

// ===========================================================================
// SLIDE 4 — METHOD
// ===========================================================================
s=scaffold("Method","475569","Steady-state sweeps isolate the driver; step responses isolate the motor.",
  "Because static tests fix the driver and transients fix the motor, every behaviour I observe can be attributed to one block. That's what makes the decomposition testable rather than assumed.");
infoCard(s,M,2.25,5.7,4.05,"The rig","0F2440",[
  "12 V, 60:1 geared DC motor",
  "L298N H-bridge (single channel)",
  "600-PPR quadrature encoder",
  "Arduino Uno R4 Minima",
  "Measurement: PWM steps in → encoder RPM out",
  "20 operating points across the envelope"
],{fontSize:13.5});
infoCard(s,6.8,2.25,5.83,4.05,"How the two blocks separate","0F2440",[
  "Static sweeps (motor allowed to settle)  →  isolate the DRIVER block  [ PWM → voltage ]",
  "Step responses (the transients)  →  isolate the MOTOR block  [ voltage → speed ]"
],{fontSize:13.5});
pill(s,6.8+0.0,5.62,5.83,0.55,TEAL,"Each test fixes a different block → every behaviour attributes to one");

// ===========================================================================
// SLIDE 5 — EVIDENCE 1 : driver asymmetric
// ===========================================================================
s=scaffold("Open-loop evidence · 1 of 3","B45309","The driver's PWM→voltage map is asymmetric up to 2.2× — with a hysteretic deadzone.",
  "All the ugliness — asymmetry, deadzone, hysteresis — sits in the cheap driver. The PWM-to-voltage map differs by direction by up to a factor of 2.2 near the deadzone, and the driver droops 22 to 27 percent below supply at full duty.");
stat(s,M,2.3,2.72,1.7,"≤ 2.2×",AMBER,"directional asymmetry near the deadzone edge");
stat(s,M+2.9,2.3,2.72,1.7,"22–27%",AMBER,"voltage droop below supply at full duty");
infoCard(s,M,4.2,5.62,2.0,"Hysteretic deadzone  (forward / reverse)","B45309",[
  "Breakaway:  154 / 144  PWM",
  "Dropout:  114 / 112  PWM",
  "Different thresholds for starting vs stopping → genuine hysteresis"
],{fontSize:13.5,fill:AMBER_BG,border:AMBER_LINE});
addFig(s,6.7,2.35,5.93,3.5,"04_asymmetry_ratio.png",1200,750);
figCaption(s,6.7,5.92,5.93,"Fig 3.4 — Voltage-ratio (driver, amber) peaks at 2.2× near the deadzone; the RPM-ratio (motor, teal) stays far lower — the asymmetry is in the driver, not the motor.");

// ===========================================================================
// SLIDE 6 — EVIDENCE 2 : motor symmetric  (contribution 1)
// ===========================================================================
s=scaffold("Open-loop evidence · 2 of 3","0F766E","The motor block is symmetric to within 9% — the asymmetry is NOT in the motor.",
  "And here is the other half of contribution one. The motor's voltage-to-speed gain is direction-symmetric — 26.94 forward versus 24.52 reverse, a nine percent gap — and reproducible to about one percent. The LARGE asymmetry of the previous slide does not reappear in the motor. Asymmetry in one block, a clean other block: that is what earns the cascade.");
stat(s,M,2.35,3.55,1.75,"26.94",TEAL,sub("K","fwd","  (rpm / V)"));
stat(s,M+3.75,2.35,3.55,1.75,"24.52",TEAL,sub("K","rev","  (rpm / V)"));
card(s,8.2,2.35,4.43,0.82,WHITE,CBORDER);
s.addText([
  {text:"9%   ",options:{bold:true,color:TEAL,fontSize:23,fontFace:HEAD}},
  {text:"forward vs reverse gap",options:{color:SLATE,fontSize:14,fontFace:BODYF}}
],{x:8.45,y:2.35,w:3.93,h:0.82,valign:"middle",align:"left",margin:0});
card(s,8.2,3.28,4.43,0.82,WHITE,CBORDER);
s.addText([
  {text:"≈1%   ",options:{bold:true,color:TEAL,fontSize:23,fontFace:HEAD}},
  {text:"run-to-run reproducibility",options:{color:SLATE,fontSize:14,fontFace:BODYF}}
],{x:8.45,y:3.28,w:3.93,h:0.82,valign:"middle",align:"left",margin:0});
card(s,M,4.45,CW,1.5,TEAL_BG,TEAL);
s.addText([
  {text:"The large directional asymmetry of the driver does not reappear here. ",options:{bold:true,color:TEAL}},
  {text:"That one-block localisation — dirty driver, clean motor — is precisely what justifies splitting the plant into a cascade.  ",options:{color:BODY}},
  {text:"This is contribution one.",options:{bold:true,color:TEAL}}
],{x:M+0.3,y:4.45,w:CW-0.6,h:1.5,fontFace:BODYF,fontSize:15,valign:"middle",margin:0});

// ===========================================================================
// SLIDE 7 — EVIDENCE 3 : region-dependent dynamics  (wide figure → full band)
// ===========================================================================
s=scaffold("Open-loop evidence · 3 of 3","B45309","A single time constant is wrong by ~2×: the dynamics are region-dependent (Model C).",
  "One global time constant is misspecified by a factor of two and is rejected. Acceleration tau is a broad bathtub in PWM — about 81 milliseconds mid-range, rising to 200 near breakaway and 150 near full drive. Deceleration is a separate regime, roughly twice as slow, peaking at 321 to 366 milliseconds for stops that coast through the high-friction deadzone. The direction asymmetry even reverses sign between speeding up and slowing down.");
stat(s,M,2.12,3.79,1.0,"≈ 2×",AMBER,"decel τ vs accel τ");
stat(s,M+3.97,2.12,3.79,1.0,"81 ms",AMBER,"accel τ floor (→200 near breakaway)");
stat(s,M+2*3.97,2.12,3.79,1.0,"321–366",AMBER,"decel τ (ms), deadzone coast");
addFig(s,M,3.2,CW,3.35,"22_model_ladder_fullgrid.png",2083,760);
figCaption(s,M,6.6,CW,"Fig 4.8 — Model B's single τ fails worst at the bathtub bottom (PWM 180–220) and at deadzone-edge decel; Model C stays flat-low. Direction asymmetry reverses sign accel ↔ decel.");

// ===========================================================================
// SLIDE 8 — VALIDATION : LOOCV + cold-start  (wide figure → full band)
// ===========================================================================
s=scaffold("Validation · 1 of 2","0F766E","Cross-validation gives ~0.1–1 rpm error — and exposed a cold-start effect I confirmed by prediction.",
  "Leave-one-out cross-validation — adopted because no held-out dataset ever existed — gives a predictive excess of about 1 rpm for acceleration and 0.1 for deceleration. The ten-times gap traced to cold-start stochasticity: acceleration from rest catches the motor cold. That was a falsifiable prediction, and a warm-motor session confirmed it directly — the acceleration excess collapsed to minus 0.05 rpm.");
stat(s,M,2.12,3.79,1.0,"+1.06",TEAL,"accel LOOCV excess (rpm)");
stat(s,M+3.97,2.12,3.79,1.0,"+0.10",SLATE,"decel LOOCV excess (rpm)");
stat(s,M+2*3.97,2.12,3.79,1.0,"−0.05",TEAL,"warm accel excess — prediction met");
addFig(s,M,3.2,CW,3.35,"19_loocv_phase22_vs_gapfill.png",2240,770);
figCaption(s,M,6.6,CW,"Fig 5.2 — LOOCV RMSE vs in-sample floor. Left (cool session): accel excess +1.06. Right (warm session): accel excess collapses to −0.05 — the cold-start hypothesis, confirmed. No held-out set ever existed → LOOCV is the honest estimator.");

// ===========================================================================
// SLIDE 9 — VALIDATION : structured drift
// ===========================================================================
s=scaffold("Validation · 2 of 2","B45309","Calibration drifts between sessions in a structured way — so reuse is unsafe.",
  "Re-running the same conditions two weeks later revealed structured drift, not random noise — and it is itself a methodological result. Phase 3 then proved the cost directly: a session-fresh model had a time constant 25 percent off the locked value; reusing the stored parameters would have built a 30-percent-overdamped controller. The rule is firm — recalibrate in situ.");
const dc=[
  ["Cold-start transient","Forward-accel τ is inflated for the first ≈30 s, then recovers as the motor warms.","transient"],
  ["Low-speed decel slowdown","Deceleration to low targets runs persistently slower than interpolation predicts.","persistent"],
  ["Reverse high-PWM speed-up","Reverse τ ran persistently ≈20% below its earlier value.","persistent"]
];
const dw=3.78;
dc.forEach((c,i)=>{
  const x=M+i*(dw+0.295);
  card(s,x,2.3,dw,1.85,WHITE,CBORDER);
  s.addText(c[0],{x:x+0.2,y:2.42,w:dw-0.4,h:0.5,fontFace:HEAD,fontSize:13.5,bold:true,color:INK,valign:"middle",margin:0});
  s.addText(c[1],{x:x+0.2,y:2.92,w:dw-0.4,h:0.85,fontFace:BODYF,fontSize:12,color:BODY,valign:"top",margin:0});
  pill(s,x+0.2,3.72,1.55,0.34,(c[2]==="transient"?SLATE:AMBER),c[2]);
});
card(s,M,4.4,CW,1.55,AMBER_BG,AMBER_LINE);
s.addText([
  {text:"Phase 3 proved the cost:  ",options:{bold:true,color:AMBER,fontSize:14}},
  {text:"a session-fresh Model A had τ = 155 ms vs the locked 207 ms (~25% off). Reusing the locked parameters would have built a ~30%-overdamped controller.   ",options:{color:BODY,fontSize:14}},
  {text:"→ Recalibrate in situ; never reuse stored parameters.",options:{bold:true,color:AMBER,fontSize:14}}
],{x:M+0.3,y:4.4,w:CW-0.6,h:1.55,fontFace:BODYF,valign:"middle",margin:0});

// ===========================================================================
// SLIDE 10 — CLOSED-LOOP RESULT  (custom diverging bars)
// ===========================================================================
s=scaffold("Closed-loop test · 1 of 2","0F2440","I pre-registered the comparison, then ran it: cascade wins on steps, loses on the ramp.",
  "The metrics, success criteria and statistics were committed with a SHA-256 hash before a single trial ran — so this is honest in the strict sense. Positive means the cascade wins. It wins on the staircase, the reversal and the small-signal step, all clearly. It LOSES by about 1 rpm on the slow ramp through the deadzone. The pre-registered wins-universally hypothesis is falsified — and the largest win is the reversal, exactly the regime the open-loop work predicted.");
// axis label + baseline
s.addText("BASE − CASC  (rpm)   ·   positive = cascade wins",
  {x:0.95,y:2.18,w:7.0,h:0.32,fontFace:BODYF,fontSize:11.5,bold:true,color:SLATE,align:"left",margin:0});
const base=4.55, sc=0.30;
s.addShape(pres.shapes.LINE,{x:1.0,y:base,w:6.8,h:0,line:{color:SLATE,width:1.25}});
const bars=[
  ["P1 · staircase","p ≈ 0.004",+2.83,TEAL,false],
  ["P2 · deadzone ramp","loses",-1.09,RED,true],
  ["P3 · reversal","p ≈ 0.004",+5.22,TEAL,false],
  ["P4 · small-signal","p ≈ 0.004",+1.03,TEAL,false]
];
const centers=[2.0,3.6,5.2,6.8], bw=0.92;
bars.forEach((b,i)=>{
  const cx=centers[i], val=b[2], hgt=Math.abs(val)*sc, x=cx-bw/2;
  if(val>=0){
    s.addShape(pres.shapes.RECTANGLE,{x,y:base-hgt,w:bw,h:hgt,fill:{color:b[3]},line:{type:"none"}});
    s.addText("+"+val.toFixed(2),{x:cx-0.8,y:base-hgt-0.34,w:1.6,h:0.3,fontFace:HEAD,fontSize:13,bold:true,color:b[3],align:"center",margin:0});
  } else {
    s.addShape(pres.shapes.RECTANGLE,{x,y:base,w:bw,h:hgt,fill:{color:b[3]},line:{type:"none"}});
    s.addText(val.toFixed(2),{x:cx-0.8,y:base+hgt+0.04,w:1.6,h:0.3,fontFace:HEAD,fontSize:13,bold:true,color:b[3],align:"center",margin:0});
  }
  s.addText([
    {text:b[0],options:{bold:true,color:INK,fontSize:11.5,breakLine:true}},
    {text:b[1],options:{color:(b[4]?RED:MUTE),fontSize:10.5,italic:b[4]}}
  ],{x:cx-0.95,y:5.45,w:1.9,h:0.7,fontFace:BODYF,align:"center",valign:"top",margin:0});
});
// right panel
infoCard(s,8.35,2.32,4.28,3.75,"Pre-registered & fair","0F2440",[
  "SHA-256 of metrics + success criteria committed before any trial",
  "Fairness gate: cascade RMS PWM ≤ 1.5× baseline — no winning by hammering harder",
  "n = 8 paired trials per profile · 64 trials total",
  "All four 95% CIs exclude zero — three positive (wins), P2 negative (the one loss)"
],{fontSize:12.5});
s.addText([
  {text:"Cascade wins by 1–5 rpm on stepwise profiles; loses by ~1 rpm on the slow ramp through the deadzone — ",options:{color:BODY}},
  {text:"the “wins universally” hypothesis is falsified, specifically.",options:{bold:true,color:INK}}
],{x:M,y:6.42,w:CW,h:0.55,fontFace:BODYF,fontSize:13,italic:true,valign:"middle",margin:0});

// ===========================================================================
// SLIDE 11 — CLOSED-LOOP : the P2 loss, mechanism + fix
// ===========================================================================
s=scaffold("Closed-loop test · 2 of 2","0F766E","The one loss has an identified cause — and a concrete fix.",
  "The loss is mechanistically specific. The feedforward inverts the static block, so it inherits the block's slope discontinuity at the breakaway edge. On steps that must cross the deadzone fast, that jump helps — which is why three profiles win. On a slow ramp it injects step-like PWM, producing a 55-rpm reverse overshoot at the zero crossing and breaking the smooth signal a plain PI would give. The fix is a smoothed feedforward. A falsified hypothesis that localises its own failure is a result, not a setback.");
// explicit numerals (robust across PowerPoint / Keynote / LibreOffice; auto-number
// bullets restart at 1 in some renderers)
s.addText([
  {text:"1.   The feedforward inverts the static block → it inherits the slope discontinuity at breakaway.",options:{breakLine:true,fontSize:13.5,color:BODY,fontFace:BODYF,paraSpaceAfter:9}},
  {text:"2.   On steps that must cross the deadzone fast, that jump is helpful → P1, P3, P4 win.",options:{breakLine:true,fontSize:13.5,color:BODY,fontFace:BODYF,paraSpaceAfter:9}},
  {text:"3.   On a slow ramp it injects step-like PWM → ≈55 rpm reverse overshoot at the zero crossing.",options:{breakLine:true,fontSize:13.5,color:BODY,fontFace:BODYF,paraSpaceAfter:9}},
  {text:"4.   That breaks the smooth signal a plain PI integrator would give → P2 loses.",options:{fontSize:13.5,color:BODY,fontFace:BODYF}}
],{x:M,y:2.3,w:5.7,h:2.45,valign:"top",margin:0});
card(s,M,4.85,5.7,1.0,TEAL_BG,TEAL);
s.addText([
  {text:"Fix:  ",options:{bold:true,color:TEAL,fontSize:13.5}},
  {text:"a smoothed-feedforward cascade variant — taper through the deadzone instead of stepping. The natural next bench-day target.",options:{color:BODY,fontSize:13.5}}
],{x:M+0.22,y:4.85,w:5.7-0.44,h:1.0,fontFace:BODYF,valign:"middle",margin:0});
s.addText("A pre-registered hypothesis, falsified in a mechanistically-identified way that points to a fix, is a result — not a setback.",
  {x:M,y:6.0,w:5.7,h:0.85,fontFace:BODYF,fontSize:12.5,italic:true,bold:true,color:INK,align:"left",valign:"top",margin:0});
addFig(s,6.65,2.2,6.0,4.0,"25_p2_zero_crossing_zoom.png",1350,1080);
figCaption(s,6.65,6.32,6.0,"Fig 6.3 — at the zero crossing the CASC feedforward steps the PWM and drives a ~55 rpm reverse overshoot (blue); BASE (red) stays smooth.");

// ===========================================================================
// SLIDE 12 — HONEST LIMITS
// ===========================================================================
s=scaffold("Honesty","B45309","The limits — stated before you ask.",
  "None of this undermines the structural claim, and stating it up front is part of why the model is credible. The static map rests on a single sweep, backed by a spot-check and the implicit cross-validation of the step-response endpoints. The dynamic tables are an honestly-labelled two-session composite. The FOPDT fits are effective at the extremes. Validation is interpolation within the grid only. One condition is irreducibly noisy.");
const FOPDT_DESC=[
  {text:"Effective at the operating-point extremes & coast-to-rest (friction-dominated); "},
  {text:"T"},{text:"d",options:{subscript:true}},
  {text:" is an effective parameter, not physical latency."}
];
const lim=[
  ["Static map","One sweep (no run02/03), backed by a 2-point spot-check + implicit cross-validation of the step-response endpoints.",WHITE,CBORDER,INK],
  ["Dynamic tables","An honestly-labelled two-session composite — the bathtub and target-dependence pictures need both sessions.",WHITE,CBORDER,INK],
  ["FOPDT fits",FOPDT_DESC,WHITE,CBORDER,INK],
  ["Validation scope","Interpolation within the calibration grid only — not extrapolation, not uncorrected cross-session prediction.",WHITE,CBORDER,INK],
  ["One noisy point","Reverse 240 → 100 is irreducibly noisy through the deadzone.",WHITE,CBORDER,INK]
];
const cw3=3.78, ch=1.78;
function limitCard(x,y,t,d,fill,border,hc){
  card(s,x,y,cw3,ch,fill,border);
  s.addText(t,{x:x+0.2,y:y+0.14,w:cw3-0.4,h:0.42,fontFace:HEAD,fontSize:13.5,bold:true,color:hc,valign:"middle",margin:0});
  s.addText(d,{x:x+0.2,y:y+0.6,w:cw3-0.4,h:ch-0.72,fontFace:BODYF,fontSize:12,color:BODY,valign:"top",margin:0});
}
limitCard(M+0*(cw3+0.295),2.3,...lim[0]);
limitCard(M+1*(cw3+0.295),2.3,...lim[1]);
limitCard(M+2*(cw3+0.295),2.3,...lim[2]);
limitCard(M+0*(cw3+0.295),4.25,...lim[3]);
limitCard(M+1*(cw3+0.295),4.25,...lim[4]);
// takeaway cell (teal) in the 6th grid slot
card(s,M+2*(cw3+0.295),4.25,cw3,ch,TEAL_BG,TEAL);
s.addText("None of this undermines the structural claim. Naming the limits is part of why the model is trustworthy.",
  {x:M+2*(cw3+0.295)+0.22,y:4.25,w:cw3-0.44,h:ch,fontFace:BODYF,fontSize:13,bold:true,color:TEAL,valign:"middle",align:"left",margin:0});

// ===========================================================================
// SLIDE 13 — RECAP + THE ASK  (dark)
// ===========================================================================
s=darkSlide();
s.addText("RECAP & THE ASK",{x:M,y:0.55,w:CW,h:0.32,fontFace:HEAD,fontSize:12.5,bold:true,color:BLUEMUTE,charSpacing:3,margin:0});
s.addText("Five contributions — and one request.",{x:M,y:0.95,w:CW,h:0.7,fontFace:HEAD,fontSize:28,bold:true,color:WHITE,margin:0});
const contribs=[
  "An earned cascade — asymmetry & drift in the driver; motor symmetric to 9%, reproducible to 1%.",
  "Region-dependent dynamics — a single time constant is misspecified by ~2×.",
  "Cross-validation that surfaced — and a warm session confirmed — a cold-start effect.",
  "A methodological finding — calibration drifts between sessions; recalibrate in situ.",
  "A pre-registered closed-loop test — wins stepwise, loses on ramp-through-deadzone, and localises its own failure."
];
contribs.forEach((t,i)=>{
  const y=1.78+i*0.66;
  s.addShape(pres.shapes.OVAL,{x:M,y:y,w:0.46,h:0.46,fill:{color:TEAL}});
  s.addText(String(i+1),{x:M,y:y,w:0.46,h:0.46,fontFace:HEAD,fontSize:15,bold:true,color:WHITE,align:"center",valign:"middle",margin:0});
  s.addText(t,{x:M+0.68,y:y-0.04,w:CW-0.7,h:0.55,fontFace:BODYF,fontSize:14.5,color:"E6EEF7",valign:"middle",margin:0});
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE,{x:M,y:5.32,w:CW,h:1.05,fill:{color:TEAL},rectRadius:0.07});
s.addText([
  {text:"All seven chapters' results are complete and validated within the calibration grid.  ",options:{color:"EAFBF7"}},
  {text:"I'm requesting approval to proceed to thesis writing.",options:{bold:true,color:WHITE}}
],{x:M+0.3,y:5.32,w:CW-0.6,h:1.05,fontFace:BODYF,fontSize:16,valign:"middle",margin:0});
s.addNotes("SAY: To restate, now proven: the data — not my assumption — splits this plant into a dirty driver and a clean motor; the dynamics need a region-dependent model; it's cross-validated, its drift is characterised, and its closed-loop behaviour is pre-registered and honestly mixed. The work is complete. I'm asking to proceed to writing.");

// ===========================================================================
// SLIDE 14 — BACKUP DIVIDER (dark)
// ===========================================================================
s=darkSlide();
s.addText("RESERVE",{x:M,y:2.3,w:CW,h:0.4,fontFace:HEAD,fontSize:13,bold:true,color:BLUEMUTE,charSpacing:3,margin:0});
s.addText("Backup — flip to on demand",{x:M,y:2.85,w:CW,h:0.9,fontFace:HEAD,fontSize:34,bold:true,color:WHITE,margin:0});
s.addText([
  {text:"Anticipated questions → where each is already answered",options:{bullet:{indent:12},breakLine:true,color:ICE,fontSize:15,fontFace:BODYF,paraSpaceAfter:8}},
  {text:"The model ladder on real step responses  (Fig 4.6 / 4.7)",options:{bullet:{indent:12},breakLine:true,color:ICE,fontSize:15,fontFace:BODYF,paraSpaceAfter:8}},
  {text:"Closed-loop trajectories & the fairness check  (Fig 6.2)",options:{bullet:{indent:12},color:ICE,fontSize:15,fontFace:BODYF}}
],{x:M,y:4.0,w:CW,h:1.6,valign:"top",margin:0});
s.addText("Keep the figure-heavy detail ready; pull it up only when asked.",
  {x:M,y:6.0,w:CW,h:0.4,fontFace:BODYF,fontSize:13,italic:true,color:BLUEMUTE,margin:0});

// ===========================================================================
// SLIDE 15 — Q-MAP (light)
// ===========================================================================
s=scaffold("Backup","475569","Anticipated questions — and where each is already answered.",
  "Every question they ask whose answer is already in the work means I showed something but didn't assert it. When that happens, I flip here and point to the slide.");
const rows=[
  [{text:"Likely question",options:{bold:true,color:WHITE,fill:{color:INK}}},{text:"Answered on",options:{bold:true,color:WHITE,fill:{color:INK}}}],
  ["Why a cascade, not one black-box model?","Slides 3 & 6 · backup ladder"],
  ["How do you know the asymmetry is the driver, not the motor?","Slides 5 & 6"],
  ["Is it reproducible? Did you validate?","Slides 8 & 12"],
  ["Why LOOCV instead of a held-out test set?","Slide 8 — no held-out set existed"],
  ["Why does it lose on P2?","Slide 11 — FF discontinuity, with the fix"],
  ["Why trust the time constants given the drift?","Slide 9 — drift characterised; recalibrate in situ"]
];
s.addTable(rows,{
  x:M,y:2.3,w:CW,colW:[7.6,4.33],
  border:{type:"solid",pt:0.75,color:CBORDER},
  align:"left",valign:"middle",fontFace:BODYF,fontSize:13,color:BODY,
  rowH:0.52,
  fill:{color:WHITE},
  margin:[3,6,3,6]
});
// Note row
s.addText("Tip: every “already-in-the-work” question = something shown but not asserted. Flip here, point to the slide.",
  {x:M,y:6.35,w:CW,h:0.4,fontFace:BODYF,fontSize:12.5,italic:true,color:SLATE,margin:0});

// ===========================================================================
// SLIDE 16 — BACKUP : model ladder overlay
// ===========================================================================
s=scaffold("Backup","475569","The model ladder, on real step responses.",
  "If they ask why C earns its complexity over A and B: Model A reaches the wrong level and rises with the wrong shape; Model C tracks both level and transient. The scoreboard on the next slide shows C wins every direction-by-region group.");
addFig(s,M,2.3,7.5,4.25,"20_model_ladder_overlay.png",1934,1183);
figCaption(s,M,6.62,7.5,"Fig 4.6 — measured vs Model A / B / C on four representative transitions; per-panel RMSE annotated.");
infoCard(s,8.45,2.3,4.18,4.25,"Why C earns its complexity","0F2440",[
  "Model A reaches the wrong level and rises with the wrong shape.",
  "Model B fixes the level but keeps one global τ.",
  "Model C tracks both level and transient in every panel.",
  "Per-panel RMSE (annotated) drops monotonically A → B → C."
],{fontSize:13});

// ===========================================================================
// SLIDE 17 — BACKUP : A/B/C scoreboard  (wide figure → full band)
// ===========================================================================
s=scaffold("Backup","475569","A/B/C scoreboard — Model C wins every direction × region group.",
  "If they want the headline scoreboard: Model C wins every one of the four direction-by-region groups, on both prediction error and goodness-of-fit. The big jump is adding the static block, A to B; region-dependent tau, B to C, is the consistent finisher.");
addFig(s,M,2.4,CW,3.55,"21_model_ladder_scoreboard.png",2084,730);
figCaption(s,M,6.05,CW,"Fig 4.7 — left: post-step RMSE (lower = better); right: FIT% (higher = better, Model A clipped at −50). Model C is best in all four groups on both metrics.");
s.addText("The static block (A → B) is the big jump; region-dependent τ (B → C) is the consistent finisher.",
  {x:M,y:6.5,w:CW,h:0.4,fontFace:BODYF,fontSize:12.5,italic:true,color:SLATE,align:"center",margin:0});

// ===========================================================================
// SLIDE 18 — BACKUP : closed-loop trajectories + fairness
// ===========================================================================
s=scaffold("Backup","475569","Closed-loop trajectories and the fairness check.",
  "The trajectory figure shows reference versus measured, one pair per profile and controller; on P2 you can see the cascade deviating at the zero crossings. The fairness gate confirms the cascade did not win by hammering harder, and the pre-registration hash was committed before bench day.");
addFig(s,M,2.3,6.1,4.25,"24_closed_loop_trajectories.png",1680,1440);
figCaption(s,M,6.62,6.1,"Fig 6.2 — reference vs measured, one pair per (profile × controller).");
infoCard(s,7.05,2.3,5.58,4.25,"The fairness check","0F2440",[
  "Fairness gate satisfied: cascade RMS PWM ≤ 1.5× baseline on every profile (ratios 0.99–1.04) — no winning by hammering harder.",
  "Pre-registration: SHA-256 of metrics + success criteria committed before bench day.",
  "Per-pair noise small: sd of differences 0.14–0.29 rpm — effects stable across 8 repetitions."
],{fontSize:13});

pres.writeFile({ fileName: OUT }).then(f=>console.log("WROTE", f)).catch(e=>{console.error("ERROR", e); process.exit(1);});
