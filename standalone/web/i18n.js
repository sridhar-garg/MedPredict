/* Offline display-only localization. Never sends user records to a translator.
   Source strings, option values and form inputs remain unchanged. */
(() => {
 'use strict';
 const languages={en:'English',hi:'हिन्दी · Hindi',bn:'বাংলা · Bengali',mr:'मराठी · Marathi',ta:'தமிழ் · Tamil',te:'తెలుగు · Telugu',gu:'ગુજરાતી · Gujarati',kn:'ಕನ್ನಡ · Kannada',ml:'മലയാളം · Malayalam',pa:'ਪੰਜਾਬੀ · Punjabi',es:'Español · Spanish',fr:'Français · French',de:'Deutsch · German',pt:'Português · Portuguese',ar:'العربية · Arabic'};
 let language='en',catalog={},observer=null;
 const nodes=new WeakMap(),attrs=new WeakMap();
 const skip='script,style,svg,code,pre,textarea,[contenteditable],[data-no-translate],[translate="no"],.article,.journal-content,.journal-text,.review-text,.user-info,.user-avatar,.listingI';
 const actualSource=(node,map,key)=>{const val=key?node.getAttribute(key):node.data;const old=key?map.get(node)?.[key]:map.get(node);return old&&old.display===val?old.source:val;};
 function translate(value){
   if(language==='en'||typeof value!=='string')return value;
   const stripped=value.trim(),lower=stripped.toLowerCase();
   const direct=Object.hasOwn(catalog,stripped)?catalog[stripped]:catalog[lower];
   if(direct)return value.replace(stripped,direct);
   // Match decorative prefixes/suffixes without translating arbitrary user prose.
   const m=stripped.match(/^([^\p{L}\p{N}]*)(.*?)([^\p{L}\p{N}]*$)/u);
   if(m&&m[2]&&(catalog[m[2]]||catalog[m[2].toLowerCase()]))return value.replace(stripped,m[1]+(catalog[m[2]]||catalog[m[2].toLowerCase()])+m[3]);
   return value;
 }
 function text(node){
   if(!node.parentElement||node.parentElement.closest(skip)||!node.data.trim())return;
   const src=actualSource(node,nodes),display=translate(src);
   if(node.parentElement.tagName==='OPTION'&&!node.parentElement.hasAttribute('value'))node.parentElement.value=src.trim();
   nodes.set(node,{source:src,display});
   if(node.data!==display)node.data=display;
 }
 function attributes(el){
   if(el.closest(skip))return;
   for(const k of ['placeholder','title','aria-label']){
     if(!el.hasAttribute(k))continue;
     const src=actualSource(el,attrs,k),display=translate(src),old=attrs.get(el)||{};
     old[k]={source:src,display};attrs.set(el,old);
     if(el.getAttribute(k)!==display)el.setAttribute(k,display);
   }
 }
 function visit(root){
   if(!root)return;
   if(root.nodeType===3){text(root);return;}
   if(root.nodeType!==1&&root.nodeType!==9)return;
   if(root.nodeType===1&&root.closest(skip))return;
   if(root.nodeType===1)attributes(root);
   const walk=document.createTreeWalker(root,NodeFilter.SHOW_TEXT|NodeFilter.SHOW_ELEMENT);
   let n;while((n=walk.nextNode())){if(n.nodeType===3)text(n);else attributes(n);}
 }
 function set(next,provided){
   language=Object.hasOwn(languages,next)?next:'en';
   const raw=provided||window.MPI18nCatalogs?.[language]||{};
   catalog=Object.create(null);
   for(const [k,v] of Object.entries(raw))if(typeof v==='string'){catalog[k]=v;catalog[k.toLowerCase()]=v;}
   document.documentElement.lang=language;document.documentElement.dataset.language=language;
   if(document.body)visit(document.body);
 }
 function start(){
   if(observer||!document.body)return;
   observer=new MutationObserver(records=>{
     for(const r of records){
       if(r.type==='characterData')text(r.target);
       else if(r.type==='attributes')attributes(r.target);
       else for(const n of r.addedNodes)visit(n);
     }
   });
   observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','title','aria-label']});
   visit(document.body);
 }
 function sourceText(el){
   if(!el)return '';
   const walk=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let n,out='';
   while((n=walk.nextNode()))out+=actualSource(n,nodes);
   return out;
 }
 window.MPI18n=Object.freeze({languages,set,start,translate,sourceText,visit,language:()=>language});
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
