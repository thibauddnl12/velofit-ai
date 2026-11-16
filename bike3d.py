# ==============================================================================
#  bike3d.py — vélo 3D orientable qui montre les réglages à faire
#
#  Produit une page HTML autonome (aucune bibliothèque externe, aucun appel réseau) :
#  un petit moteur de rendu sur <canvas> dessine le vélo en perspective, on le fait
#  tourner à la souris ou au doigt, et chaque réglage est indiqué par un numéro,
#  une flèche et une silhouette animée de la pièce à déplacer.
#  Utilisation : st.iframe(bike3d.viewer_html(reglages, discipline), height=bike3d.HEIGHT)
#  (ou st.components.v1.html(...) avec un Streamlit antérieur à 1.56)
# ==============================================================================
from __future__ import annotations

import json

HEIGHT = 470

KINDS = {
    "Route / Endurance": "road",
    "Compétition / Course": "road",
    "Gravel": "gravel",
    "VTT / XC": "mtb",
    "Triathlon / CLM": "tri",
    "Triathlon (prolongateurs)": "tri",
    "Contre-la-montre (prolongateurs)": "tri",
}
KIND_LABEL = {"road": "Vélo de route", "gravel": "Gravel", "mtb": "VTT", "tri": "Vélo à prolongateurs"}


def viewer_html(adjustments, discipline: str = "Route / Endurance") -> str:
    """Page HTML du vélo 3D. `adjustments` : liste produite par velofit_core.bike_adjustments()."""
    kind = KINDS.get(discipline, "road")
    items = []
    for a in adjustments or []:
        items.append(dict(n=int(a["n"]), part=a["part"], dir=a.get("dir"), amount=a.get("amount") or "", status=a.get("status", "info"),
                          title=a.get("title", ""), reasons=list(a.get("reasons") or []), conflicts=list(a.get("conflicts") or [])))
    data = json.dumps(dict(kind=kind, label=KIND_LABEL[kind], items=items), ensure_ascii=False).replace("</", "<\\/")
    return _PAGE.replace("/*DATA*/null", data)


_PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark">
<style>
  :root{color-scheme:dark;}    /* même schéma que la page hôte : sinon le navigateur met un fond blanc opaque derrière le cadre */
  html,body{margin:0;height:100%;background:transparent;overflow:hidden;color:#eef2f7;
    font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;-webkit-text-size-adjust:100%;}
  #wrap{position:absolute;inset:0;border:1px solid rgba(255,255,255,.16);border-radius:16px;overflow:hidden;
    background:radial-gradient(120% 90% at 70% 0%,rgba(198,244,50,.07),transparent 60%),#0a0f16;}
  canvas{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:pan-y;cursor:grab;}
  canvas.drag{cursor:grabbing;}
  .bar{position:absolute;left:10px;top:10px;right:10px;display:flex;gap:6px;flex-wrap:nowrap;align-items:center;pointer-events:none;}
  .bar button{pointer-events:auto;font:600 12px/1 inherit;font-family:inherit;color:#c9d2de;background:rgba(17,24,35,.9);
    border:1px solid rgba(255,255,255,.18);border-radius:8px;padding:8px 10px;cursor:pointer;min-height:32px;}
  .bar button:hover{border-color:#c6f432;color:#c6f432;}
  .bar button.on{background:#c6f432;border-color:#c6f432;color:#0a0f05;}
  .bar .sp{flex:1 1 0;min-width:0;}
  .bar button{flex:0 0 auto;white-space:nowrap;}
  .kind{font:500 11px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.1em;text-transform:uppercase;color:#8b97a8;
    pointer-events:none;padding:0 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:0 1 auto;min-width:0;}
  @media (max-width:600px){.kind{display:none}}
  #tip{position:absolute;left:10px;right:10px;bottom:10px;background:rgba(10,15,22,.93);border:1px solid rgba(255,255,255,.16);
    border-left:3px solid #c6f432;border-radius:10px;padding:9px 12px;font-size:13px;line-height:1.45;color:#c9d2de;}
  #tip b{color:#fff;font-size:14px;} #tip .r{display:block;color:#a5b1c2;margin-top:2px;} #tip .c{display:block;color:#fbbf24;margin-top:2px;}
  #tip .lg{display:inline-flex;align-items:center;gap:5px;margin-right:12px;white-space:nowrap;}
  #tip .lg i{width:8px;height:8px;border-radius:50%;display:inline-block;}
  @media (max-width:480px){.bar{gap:4px;left:8px;right:8px;top:8px}.bar button{padding:7px 7px;font-size:11px;min-height:30px}.kind{display:none}
    #tip{font-size:12.5px;left:8px;right:8px;bottom:8px;padding:8px 10px}}
  @media (max-width:345px){.bar{gap:3px}.bar button{padding:6px 5px;font-size:10.5px}}
</style></head>
<body><div id="wrap">
  <canvas id="c" aria-label="Vélo en trois dimensions : faites glisser pour le faire tourner"></canvas>
  <div class="bar">
    <button data-v="q" class="on">3/4</button><button data-v="p">Profil</button><button data-v="f">Face</button><button data-v="t">Dessus</button>
    <span class="sp"></span><span class="kind" id="kind"></span>
    <button id="zo" aria-label="Dézoomer">−</button><button id="zi" aria-label="Zoomer">+</button><button id="auto" class="on">Rotation</button>
  </div>
  <div id="tip"></div>
</div>
<script>
(function(){
"use strict";
var DATA = /*DATA*/null || {kind:"road",label:"Vélo de route",items:[]};
var COL = {bad:"#fb7185", warn:"#fbbf24", info:"#5ec8ff", ok:"#34d399"};
var NAME = {bad:"À corriger", warn:"À surveiller", info:"Repère matériel", ok:"Optimal"};
var cv = document.getElementById("c"), ctx = cv.getContext("2d"), tip = document.getElementById("tip");
var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---------------------------------------------------------------- géométrie (mm : x vers l'avant, y vers le haut, z côté transmission)
var GEO = {
  road:  {R:340, ty:13, wb:990,  cs:410, drop:70, sta:73.5, stl:520, stack:560, reach:385, ha:73,   htl:140, stem:100, bar:"drop", sh:705, ring:98},
  gravel:{R:350, ty:20, wb:1020, cs:425, drop:72, sta:73.5, stl:520, stack:580, reach:385, ha:71.5, htl:150, stem:90,  bar:"drop", sh:705, ring:86},
  tri:   {R:340, ty:12, wb:990,  cs:400, drop:72, sta:78,   stl:520, stack:520, reach:410, ha:72.5, htl:100, stem:80,  bar:"aero", sh:715, ring:102},
  mtb:   {R:372, ty:28, wb:1130, cs:435, drop:45, sta:75,   stl:440, stack:615, reach:440, ha:68,   htl:110, stem:60,  bar:"flat", sh:700, ring:66}
};
var g = GEO[DATA.kind] || GEO.road;
var rad = Math.PI/180;
function V(x,y,z){return [x,y,z||0];}
function add(a,b){return [a[0]+b[0],a[1]+b[1],a[2]+b[2]];}
function mul(a,k){return [a[0]*k,a[1]*k,a[2]*k];}
function mix(a,b,t){return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];}
function setZ(a,z){return [a[0],a[1],z];}

var Ar = V(0,g.R), Af = V(g.wb,g.R), BB = V(Math.sqrt(g.cs*g.cs-g.drop*g.drop), g.R-g.drop);
var sdir = V(-Math.cos(g.sta*rad), Math.sin(g.sta*rad)), hdir = V(-Math.cos(g.ha*rad), Math.sin(g.ha*rad));
var STtop = add(BB, mul(sdir,g.stl)), HTtop = add(BB, V(g.reach,g.stack)), HTbot = add(HTtop, mul(hdir,-g.htl));
var STEER = add(HTtop, mul(hdir,38)), stemDir = V(Math.cos(7*rad), Math.sin(7*rad)), CL = add(STEER, mul(stemDir,g.stem));
var SAD = add(BB, mul(sdir,g.sh));
var crankDir = V(Math.cos(-22*rad), Math.sin(-22*rad)), PR = add(BB, mul(crankDir,172)), PL = add(BB, mul(crankDir,-172));
var CEN = V(g.wb/2, 560, 0);

var P = [];                                   // primitives : segments (tubes) et polygones
function seg(a,b,r,col,part,o){ P.push({t:0,a:a,b:b,r:r,col:col,part:part||"",thin:o&&o.thin,al:o&&o.al||1,plain:o&&o.plain}); }
function ring(c,r,tube,col,part,n,o){
  n = n||40; var prev=null;
  for(var i=0;i<=n;i++){ var an=i/n*Math.PI*2, p=V(c[0]+Math.cos(an)*r, c[1]+Math.sin(an)*r, c[2]); if(prev) seg(prev,p,tube,col,part,{plain:true,al:o&&o.al||1}); prev=p; }
}
function poly(pts,fill,stroke,part){ P.push({t:1,pts:pts,fill:fill,stroke:stroke,part:part||""}); }
function path(pts,r,col,part){ for(var i=1;i<pts.length;i++) seg(pts[i-1],pts[i],r,col,part); }

var FRAME="#d3dae3", DARK="#5d6a7c", TYRE="#39424f", METAL="#9aa6b5", BLACK="#2a323e";

function wheel(c,tag){
  ring(c, g.R-g.ty, g.ty, TYRE, tag, 56);
  ring(c, g.R-g.ty, g.ty*0.34, "#4b5565", tag, 56);
  ring(c, g.R-2*g.ty-7, 4.5, METAL, "", 48);
  var hw = tag==="tyreR"?62:50;
  seg(setZ(c,-hw), setZ(c,hw), 11, DARK, "");
  var n=16, rr=g.R-2*g.ty-9;
  for(var i=0;i<n;i++){ var an=(i/n)*Math.PI*2+0.1, z=(i%2?1:-1)*26;
    seg(V(c[0]+Math.cos(an+0.5)*16, c[1]+Math.sin(an+0.5)*16, z), V(c[0]+Math.cos(an)*rr, c[1]+Math.sin(an)*rr, 0), 1, METAL, "", {thin:true, al:.55}); }
}

function build(){
  wheel(Ar,"tyreR"); wheel(Af,"tyreF");
  // cadre
  var st1 = add(STtop, mul(sdir,-28)), ht1 = add(HTtop, mul(hdir,-22)), ht2 = add(HTbot, mul(hdir,26));
  seg(BB, STtop, 17, FRAME, "frame"); seg(st1, ht1, 16, FRAME, "frame"); seg(BB, ht2, 20, FRAME, "frame"); seg(HTbot, HTtop, 21, FRAME, "frame");
  var ss = add(STtop, mul(sdir,-45));
  [-1,1].forEach(function(s){
    seg(setZ(BB,s*22), setZ(Ar,s*62), 10, FRAME, "frame");
    seg(setZ(ss,s*14), setZ(Ar,s*62), 8, FRAME, "frame");
  });
  seg(setZ(BB,-42), setZ(BB,42), 23, FRAME, "frame");
  // fourche
  var crown = add(HTbot, mul(hdir,-22));
  seg(HTbot, crown, 17, FRAME, "frame");
  if(g.bar==="flat"){
    seg(setZ(crown,-62), setZ(crown,62), 15, BLACK, "frame");
    [-1,1].forEach(function(s){ var top=setZ(crown,s*62), ax=setZ(Af,s*62), mid=mix(top,ax,.5);
      seg(top, mid, 13, METAL, "frame"); seg(mid, ax, 19, BLACK, "frame"); });
    var arch = mix(crown,Af,.52); seg(setZ(arch,-62), setZ(arch,62), 9, BLACK, "frame");
  } else {
    seg(setZ(crown,-46), setZ(crown,46), 13, FRAME, "frame");
    [-1,1].forEach(function(s){ seg(setZ(crown,s*46), setZ(Af,s*52), 11, FRAME, "frame"); });
  }
  // tige de selle et selle
  seg(STtop, add(SAD, mul(sdir,-34)), 12, BLACK, "post");
  var sy = SAD[1];
  var out = [[-138,40],[-128,60],[-70,68],[10,46],[80,24],[132,17],[146,8]], topP=[], botP=[], q, i2;
  out.forEach(function(q){ topP.push(V(SAD[0]+q[0], sy+(q[0]<-90?6:0), q[1])); botP.push(V(SAD[0]+q[0]*.94, sy-26, q[1]*.72)); });
  out.slice().reverse().forEach(function(q){ topP.push(V(SAD[0]+q[0], sy+(q[0]<-90?6:0), -q[1])); botP.push(V(SAD[0]+q[0]*.94, sy-26, -q[1]*.72)); });
  for(i2=0;i2<topP.length;i2++){ var j2=(i2+1)%topP.length; poly([topP[i2],topP[j2],botP[j2],botP[i2]], "#262d38", "", "saddle"); }
  poly(botP, "#1d232c", "", "saddle");
  P.push({t:1,pts:topP,fill:"#465061",stroke:"",part:"saddle",bias:14});
  seg(V(SAD[0]-40, sy-30), V(SAD[0]+50, sy-30), 5, METAL, "saddle");
  // direction, potence, cintre
  seg(HTtop, STEER, 15, DARK, "frame");
  seg(STEER, CL, 14, BLACK, "stem");
  if(g.bar==="drop"){
    var hw = DATA.kind==="gravel"?215:200, fl = DATA.kind==="gravel"?28:6;
    seg(setZ(CL,-hw), setZ(CL,hw), 11, BLACK, "bars");
    [-1,1].forEach(function(s){
      var z=s*hw, zf=s*(hw+fl);
      path([V(CL[0],CL[1],z), V(CL[0]+62,CL[1]-2,z), V(CL[0]+86,CL[1]-34,s*(hw+fl*.4)), V(CL[0]+74,CL[1]-82,s*(hw+fl*.8)), V(CL[0]+30,CL[1]-122,zf), V(CL[0]-38,CL[1]-128,zf)], 10, BLACK, "bars");
      seg(V(CL[0]+70,CL[1]+2,z), V(CL[0]+112,CL[1]+48,z), 12, DARK, "bars");
    });
  } else if(g.bar==="flat"){
    path([V(CL[0]-26,CL[1]+14,-372), V(CL[0],CL[1]+6,-150), V(CL[0],CL[1],0), V(CL[0],CL[1]+6,150), V(CL[0]-26,CL[1]+14,372)], 11, BLACK, "bars");
    [-1,1].forEach(function(s){ seg(V(CL[0]-26,CL[1]+14,s*372), V(CL[0]-20,CL[1]+12,s*300), 14, DARK, "bars"); });
  } else {
    seg(setZ(CL,-205), setZ(CL,205), 9, BLACK, "bars");
    [-1,1].forEach(function(s){
      seg(V(CL[0],CL[1],s*205), V(CL[0]+70,CL[1]-6,s*205), 10, DARK, "bars");
      path([V(CL[0]-40,CL[1]+34,s*62), V(CL[0]+230,CL[1]+44,s*58), V(CL[0]+300,CL[1]+92,s*52)], 10, BLACK, "bars");
      poly([V(CL[0]-66,CL[1]+48,s*52), V(CL[0]+24,CL[1]+48,s*52), V(CL[0]+24,CL[1]+48,s*132), V(CL[0]-66,CL[1]+48,s*132)], "#3a4350", "#8b97a8", "bars");
    });
  }
  // transmission
  seg(setZ(BB,-74), setZ(BB,74), 8, METAL, "");
  seg(setZ(BB,74), setZ(PR,80), 12, METAL, "crank"); seg(setZ(BB,-74), setZ(PL,-80), 12, METAL, "crank");
  seg(setZ(PR,80), setZ(PR,165), 6, METAL, "pedal"); seg(setZ(PL,-80), setZ(PL,-165), 6, METAL, "pedal");
  [[PR,1],[PL,-1]].forEach(function(q){ var c=q[0], s=q[1];
    poly([V(c[0]-44,c[1]+6,s*96), V(c[0]+44,c[1]+6,s*96), V(c[0]+44,c[1]+6,s*160), V(c[0]-44,c[1]+6,s*160)], "#4a5463", "#9aa6b5", "pedal"); });
  var cz = 52;
  ring(setZ(BB,cz), g.ring, 3.5, METAL, "", 30);
  for(var i=0;i<5;i++){ var an=i/5*Math.PI*2+0.4; seg(setZ(BB,cz), V(BB[0]+Math.cos(an)*g.ring, BB[1]+Math.sin(an)*g.ring, cz), 4, METAL, "", {al:.8}); }
  ring(setZ(Ar,cz-4), DATA.kind==="mtb"?92:56, 3, METAL, "", 24); ring(setZ(Ar,cz-4), 30, 3, METAL, "", 16);
  var rr = DATA.kind==="mtb"?92:56;
  seg(V(Ar[0], Ar[1]+rr, cz-2), V(BB[0], BB[1]+g.ring, cz), 2.2, DARK, "");
  seg(V(Ar[0], Ar[1]-rr, cz-2), V(BB[0], BB[1]-g.ring, cz), 2.2, DARK, "");
}
build();

// ---------------------------------------------------------------- réglages : pièces concernées, flèches, numéros
var TAGS = {saddle:["saddle"], bars:["bars"], stem:["stem"], cleats:["pedal"], crank:["crank"], bar_width:["bars"], tyres:["tyreF","tyreR"]};
var GHOST = {saddle:["saddle"], bars:["bars","stem"], stem:["bars"], cleats:["pedal"]};
var up = V(0,1,0), fwd = V(1,0,0);
var DIRV = {
  saddle:{up:sdir, down:mul(sdir,-1), fwd:fwd, back:mul(fwd,-1)},
  bars:{up:hdir, down:mul(hdir,-1)},
  stem:{longer:stemDir, shorter:mul(stemDir,-1)},
  cleats:{fwd:fwd, back:mul(fwd,-1)}
};
var barEnd = g.bar==="flat" ? V(CL[0]-26, CL[1]+14, 372) : V(CL[0], CL[1], g.bar==="aero"?205:200);
var ANCH = {saddle:add(SAD,V(0,6,0)), bars:add(CL,V(0,8,0)), stem:mix(STEER,CL,.5), cleats:V(PR[0],PR[1]+8,128), crank:setZ(mix(BB,PR,.55),80),
  bar_width:barEnd, tyres:V(Af[0]+(g.R-g.ty)*Math.cos(52*rad), Af[1]+(g.R-g.ty)*Math.sin(52*rad), 0)};
var OFFS = {cleats:V(60,-95,90), crank:V(-40,-150,70), bar_width:V(30,95,70), tyres:V(95,85,0), saddle:V(-70,120,0), bars:V(40,130,0), stem:V(0,120,60)};

var partStatus = {};
var items = DATA.items.map(function(a){
  var d = a.dir && DIRV[a.part] ? DIRV[a.part][a.dir] : null, an = ANCH[a.part] || CEN, it = {a:a, d:d, an:an};
  (TAGS[a.part]||[]).forEach(function(t){ if(!partStatus[t]) partStatus[t]=a.status; });
  if(d){
    var c;                                   // centre de la flèche, placé à côté de la pièce
    if(a.part==="saddle") c = (a.dir==="up"||a.dir==="down") ? add(SAD, mul(sdir,124)) : add(SAD, V(96,62,78));
    else if(a.part==="bars") c = add(CL, mul(hdir,128));
    else if(a.part==="stem") c = add(mix(STEER,CL,.5), V(0,-74,78));
    else c = add(an, V(0,-62,24));
    it.t0 = add(c, mul(d,-72)); it.t1 = add(c, mul(d,72));
    it.far = (dist(it.t0,an) > dist(it.t1,an)) ? it.t0 : it.t1; it.near = it.far===it.t0 ? it.t1 : it.t0;
    it.badge = it.far;
  } else {
    it.badge = add(an, OFFS[a.part] || V(0,110,0));
  }
  return it;
});
function sub(a,b){return [a[0]-b[0],a[1]-b[1],a[2]-b[2]];}
function dist(a,b){var d=sub(a,b);return Math.sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);}
function norm(a){var l=Math.sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2])||1;return [a[0]/l,a[1]/l,a[2]/l];}

// ---------------------------------------------------------------- caméra
var VIEWS = {q:[-0.62,0.20], p:[0,0.06], f:[-Math.PI/2,0.10], t:[-0.25,1.12]};
var yaw=-0.62, pitch=0.20, zoom=1, tYaw=null, tPitch=null, auto=!REDUCED, base=-0.62, t0=0, sel=-1;
var W=0, H=0, DPR=1, S=1, CAM=3600, small=false, cyw=1, syw=0, cpt=1, spt=0, MIDY=200;
function resize(){
  var r = cv.getBoundingClientRect(); if(r.width<10||r.height<10) return false;
  DPR = Math.min(window.devicePixelRatio||1, 2.5); W=r.width; H=r.height; small = W<520;
  cv.width=Math.round(W*DPR); cv.height=Math.round(H*DPR); ctx.setTransform(DPR,0,0,DPR,0,0);
  return true;
}
function pr(p, off){
  var x=p[0]-CEN[0], y=p[1]-CEN[1], z=p[2];
  if(off){ x+=off[0]; y+=off[1]; z+=off[2]; }
  var x1=x*cyw+z*syw, z1=-x*syw+z*cyw, y2=y*cpt-z1*spt, z2=y*spt+z1*cpt, k=CAM/(CAM-z2)*S;
  return [W/2+x1*k, MIDY-y2*k, z2, k];
}
function tint(hex, to, t){
  var a=parseInt(hex.slice(1),16), b=parseInt(to.slice(1),16);
  var r=Math.round((a>>16)+(((b>>16)-(a>>16))*t)), gg=Math.round(((a>>8)&255)+((((b>>8)&255)-((a>>8)&255))*t)), bl=Math.round((a&255)+(((b&255)-(a&255))*t));
  return "rgb("+r+","+gg+","+bl+")";
}
function fog(z){ return Math.max(.5, Math.min(1, .78+z/2600)); }

// ---------------------------------------------------------------- dessin
function tube(A,B,w,col,al){
  ctx.globalAlpha = al; ctx.lineCap="round";
  ctx.strokeStyle="#06090e"; ctx.lineWidth=w+2.2; ctx.beginPath(); ctx.moveTo(A[0],A[1]); ctx.lineTo(B[0],B[1]); ctx.stroke();
  ctx.strokeStyle=col; ctx.lineWidth=w; ctx.beginPath(); ctx.moveTo(A[0],A[1]); ctx.lineTo(B[0],B[1]); ctx.stroke();
  if(w>3.2){
    var dx=B[0]-A[0], dy=B[1]-A[1], l=Math.sqrt(dx*dx+dy*dy)||1, nx=-dy/l, ny=dx/l; if(ny>0){nx=-nx;ny=-ny;}
    var o=w*0.24; ctx.globalAlpha=al*0.42; ctx.strokeStyle="#ffffff"; ctx.lineWidth=Math.max(1,w*0.26);
    ctx.beginPath(); ctx.moveTo(A[0]+nx*o,A[1]+ny*o); ctx.lineTo(B[0]+nx*o,B[1]+ny*o); ctx.stroke();
  }
  ctx.globalAlpha=1;
}
function colorOf(p){ var s = partStatus[p.part]; return s ? tint(p.col, COL[s], s==="info" ? (p.plain ? .26 : .42) : .74) : p.col; }
function drawPrim(p, off, ghostCol, ghostAl){
  if(p.t===0){
    var A=pr(p.a,off), B=pr(p.b,off), k=(A[3]+B[3])/2, w=Math.max(p.thin?0.8:1.2, p.r*2*k);
    if(ghostCol){ ctx.globalAlpha=ghostAl; ctx.lineCap="round"; ctx.strokeStyle=ghostCol; ctx.lineWidth=Math.max(1.5,w*0.62);
      ctx.beginPath(); ctx.moveTo(A[0],A[1]); ctx.lineTo(B[0],B[1]); ctx.stroke(); ctx.globalAlpha=1; return; }
    if(p.thin || p.plain){ ctx.globalAlpha=p.al*(p.thin?fog((A[2]+B[2])/2):1); ctx.lineCap="round"; ctx.strokeStyle=p.thin?p.col:colorOf(p); ctx.lineWidth=w; ctx.beginPath(); ctx.moveTo(A[0],A[1]); ctx.lineTo(B[0],B[1]); ctx.stroke(); ctx.globalAlpha=1; return; }
    tube(A,B,w,colorOf(p),p.al*fog((A[2]+B[2])/2));
  } else {
    ctx.beginPath(); for(var i=0;i<p.pts.length;i++){ var q=pr(p.pts[i],off); if(i) ctx.lineTo(q[0],q[1]); else ctx.moveTo(q[0],q[1]); } ctx.closePath();
    if(ghostCol){ ctx.globalAlpha=ghostAl*.5; ctx.fillStyle=ghostCol; ctx.fill(); ctx.globalAlpha=ghostAl; ctx.strokeStyle=ghostCol; ctx.lineWidth=1.5; ctx.stroke(); ctx.globalAlpha=1; return; }
    var s=partStatus[p.part]; ctx.fillStyle = s ? tint(p.fill, COL[s], s==="info" ? .4 : .62) : p.fill; ctx.fill(); ctx.strokeStyle="#06090e"; ctx.lineWidth=1.1; ctx.lineJoin="round"; ctx.stroke();
  }
}
function depth(p){ if(p.t===0){ return (pr(p.a)[2]+pr(p.b)[2])/2; } var s=0; for(var i=0;i<p.pts.length;i++) s+=pr(p.pts[i])[2]; return s/p.pts.length+(p.bias||2); }

function ground(){
  ctx.lineWidth=1; ctx.strokeStyle="rgba(255,255,255,.07)";
  var x0=-450, x1=g.wb+450, z0=-520, z1=520, i, a, b;
  for(i=0;i<=8;i++){ var z=z0+(z1-z0)*i/8; a=pr(V(x0,0,z)); b=pr(V(x1,0,z)); ctx.beginPath(); ctx.moveTo(a[0],a[1]); ctx.lineTo(b[0],b[1]); ctx.stroke(); }
  for(i=0;i<=14;i++){ var x=x0+(x1-x0)*i/14; a=pr(V(x,0,z0)); b=pr(V(x,0,z1)); ctx.beginPath(); ctx.moveTo(a[0],a[1]); ctx.lineTo(b[0],b[1]); ctx.stroke(); }
  [Ar,Af].forEach(function(c){ ctx.beginPath(); for(var j=0;j<=24;j++){ var an=j/24*Math.PI*2, q=pr(V(c[0]+Math.cos(an)*150,0,Math.sin(an)*46)); if(j) ctx.lineTo(q[0],q[1]); else ctx.moveTo(q[0],q[1]); }
    ctx.fillStyle="rgba(0,0,0,.42)"; ctx.fill(); });
}

function arrow(it, al){
  var A=pr(it.t0), B=pr(it.t1), col=COL[it.a.status]||COL.info, dx=B[0]-A[0], dy=B[1]-A[1], l=Math.sqrt(dx*dx+dy*dy);
  if(l<6) return; var ux=dx/l, uy=dy/l, hs=Math.max(9, Math.min(15, l*0.3)), lw=Math.max(3, Math.min(5.5, l*0.09));
  ctx.globalAlpha=al; ctx.lineCap="round";
  ctx.strokeStyle="#06090e"; ctx.lineWidth=lw+3; ctx.beginPath(); ctx.moveTo(A[0],A[1]); ctx.lineTo(B[0]-ux*hs*.6,B[1]-uy*hs*.6); ctx.stroke();
  ctx.strokeStyle=col; ctx.lineWidth=lw; ctx.beginPath(); ctx.moveTo(A[0],A[1]); ctx.lineTo(B[0]-ux*hs*.6,B[1]-uy*hs*.6); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(B[0],B[1]); ctx.lineTo(B[0]-ux*hs-uy*hs*.62, B[1]-uy*hs+ux*hs*.62); ctx.lineTo(B[0]-ux*hs+uy*hs*.62, B[1]-uy*hs-ux*hs*.62); ctx.closePath();
  ctx.fillStyle=col; ctx.strokeStyle="#06090e"; ctx.lineWidth=1.5; ctx.fill(); ctx.stroke(); ctx.globalAlpha=1;
}
function rrect(x,y,w,h,r){ ctx.beginPath(); ctx.moveTo(x+r,y); ctx.arcTo(x+w,y,x+w,y+h,r); ctx.arcTo(x+w,y+h,x,y+h,r); ctx.arcTo(x,y+h,x,y,r); ctx.arcTo(x,y,x+w,y,r); ctx.closePath(); }

var hits = [], active = -1, moving = [];
items.forEach(function(it,i){ if(it.d) moving.push(i); });
function labels(time){
  var L = items.map(function(it,i){
    var b=pr(it.badge), an=pr(it.an), txt=it.a.amount||"", R=small?11:12.5;
    ctx.font = "600 "+(small?11.5:12.5)+"px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace";
    var tw = txt ? ctx.measureText(txt).width+16 : 0, bx=b[0], by=b[1];
    if(it.d){ var nr=pr(it.near), ux=b[0]-nr[0], uy=b[1]-nr[1], ul=Math.sqrt(ux*ux+uy*uy); if(ul<1){ ux=0; uy=-1; ul=1; } bx=b[0]+ux/ul*(R+9); by=b[1]+uy/ul*(R+9); an=pr(mix(it.t0,it.t1,.5)); }
    return {it:it,i:i,x:bx,y:by,ax:an[0],ay:an[1],tw:tw,R:R,txt:txt,left:!!it.d && (pr(it.near)[0]-b[0] > 8),dir:!!it.d};
  });
  var top = small?46:50, bot = H - (tip.offsetHeight||44) - 16;
  L.forEach(function(l){ l.x=Math.max(l.R+6, Math.min(W-l.R-6, l.x)); l.y=Math.max(top+l.R, Math.min(bot-l.R, l.y));
    if(l.x+l.R+4+l.tw > W-6) l.left=true; if(l.left && l.x-l.R-4-l.tw < 6) l.left=false; });
  for(var pass=0; pass<8; pass++){
    for(var a=0;a<L.length;a++) for(var b=a+1;b<L.length;b++){
      var p=L[a], q=L[b], px0=p.left?p.x-p.R-p.tw-4:p.x-p.R, px1=p.left?p.x+p.R:p.x+p.R+p.tw+4, qx0=q.left?q.x-q.R-q.tw-4:q.x-q.R, qx1=q.left?q.x+q.R:q.x+q.R+q.tw+4;
      if(px0<qx1+4 && qx0<px1+4 && Math.abs(p.y-q.y) < p.R+q.R+5){ var push=(p.R+q.R+5-Math.abs(p.y-q.y))/2+.5, s=(p.y<=q.y)?-1:1; p.y+=s*push; q.y-=s*push;
        p.y=Math.max(top+p.R, Math.min(bot-p.R, p.y)); q.y=Math.max(top+q.R, Math.min(bot-q.R, q.y)); }
    }
  }
  hits = [];
  L.forEach(function(l){
    var col=COL[l.it.a.status]||COL.info, dim=(sel>=0 && sel!==l.i)?.38:1, on=sel===l.i;
    if(!l.dir){
      ctx.globalAlpha=dim*.75; ctx.strokeStyle=col; ctx.lineWidth=1.2; ctx.setLineDash([3,3]); ctx.beginPath(); ctx.moveTo(l.x,l.y); ctx.lineTo(l.ax,l.ay); ctx.stroke(); ctx.setLineDash([]);
      var pu = REDUCED?0.5:(time/1500+l.i*.3)%1; ctx.globalAlpha=dim*(1-pu)*.9; ctx.beginPath(); ctx.arc(l.ax,l.ay,5+pu*12,0,Math.PI*2); ctx.strokeStyle=col; ctx.lineWidth=2; ctx.stroke();
      ctx.globalAlpha=dim; ctx.beginPath(); ctx.arc(l.ax,l.ay,3.4,0,Math.PI*2); ctx.fillStyle=col; ctx.fill();
    }
    if(l.i===active && !REDUCED){ var pb=(time/900)%1; ctx.globalAlpha=(1-pb)*.8; ctx.beginPath(); ctx.arc(l.x,l.y,l.R+3+pb*9,0,Math.PI*2); ctx.strokeStyle=col; ctx.lineWidth=2; ctx.stroke(); }
    ctx.globalAlpha=dim;
    if(l.txt){ var x0 = l.left ? l.x-l.R-l.tw+2 : l.x+l.R-8, w=l.tw+6; rrect(x0, l.y-10.5, w, 21, 6); ctx.fillStyle="rgba(10,15,22,.94)"; ctx.fill(); ctx.strokeStyle=col; ctx.lineWidth=on?1.8:1; ctx.stroke();
      ctx.fillStyle="#eef2f7"; ctx.textBaseline="middle"; ctx.textAlign=l.left?"right":"left"; ctx.font="600 "+(small?11.5:12.5)+"px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace";
      ctx.fillText(l.txt, l.left ? l.x-l.R-4 : l.x+l.R+4, l.y+.5); }
    ctx.beginPath(); ctx.arc(l.x,l.y,l.R+(on?2:0),0,Math.PI*2); ctx.fillStyle=col; ctx.fill(); ctx.strokeStyle="#06090e"; ctx.lineWidth=2; ctx.stroke();
    ctx.fillStyle="#0a0f05"; ctx.textAlign="center"; ctx.textBaseline="middle"; ctx.font="700 "+(small?12:13)+"px Inter,system-ui,-apple-system,Arial,sans-serif"; ctx.fillText(String(l.it.a.n), l.x, l.y+.5);
    ctx.globalAlpha=1;
    hits.push({i:l.i, x0:(l.left?l.x-l.R-l.tw-4:l.x-l.R)-4, x1:(l.left?l.x+l.R:l.x+l.R+l.tw+4)+4, y0:l.y-l.R-5, y1:l.y+l.R+5});
  });
}

function frame(time){
  if(!W && !resize()) return;
  if(tYaw!==null){ yaw+=(tYaw-yaw)*.14; pitch+=(tPitch-pitch)*.14; if(Math.abs(tYaw-yaw)<.004 && Math.abs(tPitch-pitch)<.004){ yaw=tYaw; pitch=tPitch; tYaw=null; base=yaw; t0=time; } }
  else if(auto && !dragging){ yaw = base + 0.42*Math.sin((time-t0)/2300); }
  cyw=Math.cos(yaw); syw=Math.sin(yaw); cpt=Math.cos(pitch); spt=Math.sin(pitch);
  var topY = (small?50:54), botY = H-(tip.offsetHeight||48)-18; MIDY = (topY+botY)/2+6;
  S = Math.min((W-30)/1780, (botY-topY-8)/1290) * zoom;
  ctx.clearRect(0,0,W,H);
  ground();
  var order = P.map(function(p){ return [depth(p), p]; }).sort(function(a,b){ return a[0]-b[0]; });
  for(var i=0;i<order.length;i++) drawPrim(order[i][1]);
  var CY = 3200, cyc = REDUCED ? .62 : ((time/CY)%1), ph = cyc<.55 ? (1-Math.cos(cyc/.55*Math.PI))/2 : 1, fade = cyc>.86 ? 1-(cyc-.86)/.14 : 1;
  active = -1;
  if(sel>=0 && items[sel] && items[sel].d) active = sel;
  else if(sel<0 && moving.length) active = REDUCED ? moving[0] : moving[Math.floor(time/CY)%moving.length];
  if(active>=0){ var ga=items[active], gcol=COL[ga.a.status]||COL.info, goff=mul(ga.d, 70*ph);
    (GHOST[ga.a.part]||[]).forEach(function(tag){ P.forEach(function(p){ if(p.part===tag) drawPrim(p, goff, gcol, (.3+.6*ph)*fade); }); }); }
  items.forEach(function(it,i){ if(it.d) arrow(it, (sel>=0 && sel!==i)?.3:1); });
  labels(time);
}
var running=false, visible=true;
function loop(time){ running=false; try{ frame(time); }catch(e){ fail(e); return; } if(visible){ running=true; requestAnimationFrame(loop); } }
function kick(){ if(!running){ running=true; requestAnimationFrame(loop); } }
function fail(e){ tip.innerHTML = "<b>Aperçu 3D indisponible sur cet appareil.</b><span class='r'>La liste des réglages reste affichée à côté.</span>"; if(window.console) console.error(e); }

// ---------------------------------------------------------------- interactions
var dragging=false, moved=0, lx=0, ly=0, pid=null;
cv.addEventListener("pointerdown", function(e){ dragging=true; moved=0; lx=e.clientX; ly=e.clientY; pid=e.pointerId; try{cv.setPointerCapture(pid);}catch(_){ } cv.classList.add("drag"); tYaw=null; });
cv.addEventListener("pointermove", function(e){
  if(!dragging){ var h=hit(e); cv.style.cursor = h>=0 ? "pointer" : "grab"; return; }
  var dx=e.clientX-lx, dy=e.clientY-ly; lx=e.clientX; ly=e.clientY; moved+=Math.abs(dx)+Math.abs(dy);
  yaw+=dx*0.009; if(e.pointerType!=="touch") pitch=Math.max(-0.25, Math.min(1.35, pitch+dy*0.006));
});
function end(e){ if(!dragging) return; dragging=false; cv.classList.remove("drag"); base=yaw; t0=performance.now();
  if(moved<6 && e.type==="pointerup"){ var h=hit(e); sel = (h===sel) ? -1 : h; showTip(); } }
cv.addEventListener("pointerup", end); cv.addEventListener("pointercancel", end); cv.addEventListener("pointerleave", function(e){ if(e.pointerType==="mouse") end(e); });
function hit(e){ var r=cv.getBoundingClientRect(), x=e.clientX-r.left, y=e.clientY-r.top; for(var i=hits.length-1;i>=0;i--){ var h=hits[i]; if(x>=h.x0&&x<=h.x1&&y>=h.y0&&y<=h.y1) return h.i; } return -1; }
function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); }
function showTip(){
  if(sel>=0 && items[sel]){ var a=items[sel].a, col=COL[a.status]||COL.info; tip.style.borderLeftColor=col;
    tip.innerHTML = "<b>"+a.n+". "+esc(a.title)+"</b><span class='r'>"+a.reasons.map(esc).join(" · ")+"</span>"+(a.conflicts.length?"<span class='c'>À réévaluer ensuite : "+a.conflicts.map(esc).join(" · ")+"</span>":""); return; }
  tip.style.borderLeftColor="#c6f432";
  if(!items.length){ tip.innerHTML="<b>Aucun réglage à faire sur le vélo.</b><span class='r'>Tous les angles mesurés sont dans les plages cibles. Faites glisser pour faire tourner le vélo.</span>"; return; }
  var seen={}, lg=""; items.forEach(function(it){ var s=it.a.status; if(!seen[s]){ seen[s]=1; lg+="<span class='lg'><i style='background:"+(COL[s]||COL.info)+"'></i>"+NAME[s]+"</span>"; } });
  tip.innerHTML = lg+"<span class='r'>Faites glisser pour tourner le vélo. Touchez un numéro pour voir le détail du réglage.</span>";
}
Array.prototype.forEach.call(document.querySelectorAll(".bar button[data-v]"), function(b){
  b.addEventListener("click", function(){ var v=VIEWS[b.getAttribute("data-v")]; tYaw=v[0]; tPitch=v[1];
    Array.prototype.forEach.call(document.querySelectorAll(".bar button[data-v]"), function(o){ o.classList.toggle("on", o===b); }); });
});
var bAuto=document.getElementById("auto");
bAuto.addEventListener("click", function(){ auto=!auto; base=yaw; t0=performance.now(); bAuto.classList.toggle("on", auto); });
if(REDUCED) bAuto.classList.remove("on");
document.getElementById("zi").addEventListener("click", function(){ zoom=Math.min(1.9, zoom*1.18); });
document.getElementById("zo").addEventListener("click", function(){ zoom=Math.max(.6, zoom/1.18); });
document.getElementById("kind").textContent = DATA.label || "";
window.addEventListener("resize", function(){ resize(); });
if(window.ResizeObserver){ new ResizeObserver(function(){ if(resize()) kick(); }).observe(cv); }
if(window.IntersectionObserver){ new IntersectionObserver(function(en){ visible = en[0].isIntersecting; if(visible) kick(); }, {threshold:0.01}).observe(cv); }
window.__bike = {state:function(){ return {yaw:yaw, pitch:pitch, sel:sel, zoom:zoom, n:items.length, prims:P.length, hits:hits}; }};
showTip(); resize(); kick();
})();
</script></body></html>
"""
