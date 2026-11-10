"use strict";
const timezone="Europe/Madrid";
const fmtDate=new Intl.DateTimeFormat("es-ES",{timeZone:timezone,day:"numeric",month:"short"});
const fmtLong=new Intl.DateTimeFormat("es-ES",{timeZone:timezone,weekday:"long",day:"numeric",month:"long"});
const fmtMonth=new Intl.DateTimeFormat("es-ES",{timeZone:timezone,month:"long",year:"numeric"});
const fmtTime=new Intl.DateTimeFormat("es-ES",{timeZone:timezone,hour:"2-digit",minute:"2-digit"});
const state={events:[],month:new Date(),filter:"todos",search:"",selected:null,status:"loading",manualEnabled:false};
const el=id=>document.getElementById(id);
function dayKey(d){return new Intl.DateTimeFormat("en-CA",{timeZone:timezone,year:"numeric",month:"2-digit",day:"2-digit"}).format(d)}
function eventDate(e){return e.all_day?new Date(e.start+"T12:00:00Z"):new Date(e.start)}
function eventKey(e){return e.all_day?e.start:dayKey(eventDate(e))}
function currentDay(){return dayKey(new Date())}
function fmtDay(e){return fmtDate.format(eventDate(e))}
function label(t){return {examen:"Examen",entrega:"Entrega",otro:"Evento"}[t]||"Evento"}
function safe(s){return String(s??"")}
function renderMetrics(){
 const future=state.events.filter(e=>eventKey(e)>=currentDay());
 el("metric-total").textContent=future.length;
 el("metric-entregas").textContent=future.filter(e=>e.type==="entrega").length;
 el("metric-examenes").textContent=future.filter(e=>e.type==="examen").length;
}
function renderCalendar(){
 const m=state.month.getMonth(),y=state.month.getFullYear(),first=new Date(y,m,1),offset=(first.getDay()+6)%7,days=new Date(y,m+1,0).getDate(),cells=Math.ceil((offset+days)/7)*7;
 el("month-title").textContent=fmtMonth.format(first);
 const grid=el("calendar-grid");grid.replaceChildren();
 const grouped=new Map();
 for(const e of state.events){const k=eventKey(e);if(!grouped.has(k))grouped.set(k,[]);grouped.get(k).push(e);}
 for(let n=0;n<cells;n++){
   const dt=new Date(y,m,1-offset+n,12),key=dayKey(dt),items=grouped.get(key)||[],outside=dt.getMonth()!==m;
   const b=document.createElement("button");b.type="button";b.className="day"+(outside?" outside":"")+(key===currentDay()?" today":"")+(key===state.selected?" selected":"");
   b.setAttribute("aria-label",fmtLong.format(dt)+(items.length?", "+items.length+" eventos":""));
   b.setAttribute("aria-pressed",String(key===state.selected));
   const number=document.createElement("span");number.className="day-number";number.textContent=dt.getDate();
   const dots=document.createElement("span");dots.className="dots";
   for(const e of items.slice(0,4)){const d=document.createElement("i");d.className="dot "+(e.type==="examen"?"exam":e.type==="entrega"?"task":"other");dots.append(d);}
   b.append(number,dots);
   b.addEventListener("click",()=>{state.selected=state.selected===key?null:key;if(outside)state.month=new Date(dt.getFullYear(),dt.getMonth(),1);renderCalendar();renderEvents();});
   grid.append(b);
 }
}
function eventElement(e){
 const row=document.createElement("article");row.className="event";
 const stamp=document.createElement("div");stamp.className="date-box";
 const d=eventDate(e);const [date,month]=fmtDay(e).split(" ");
 const number=document.createElement("strong");number.textContent=date;
 const mon=document.createElement("small");mon.textContent=month||"";
 stamp.append(number,mon);
 const details=document.createElement("div");details.className="event-details";
 const title=document.createElement("h3");title.className="event-title";title.textContent=safe(e.title);
 const subtitle=document.createElement("div");subtitle.className="event-subtitle";
 subtitle.textContent=(e.all_day?"Día completo":fmtTime.format(d))+(e.course?" · "+safe(e.course):"");
 details.append(title,subtitle);
 const badge=document.createElement("span");badge.className="event-type "+(e.type==="examen"?"examen":e.type==="entrega"?"entrega":"otro");badge.textContent=label(e.type);
 row.append(stamp,details,badge);return row;
}
function renderEvents(){
 let arr=state.events.filter(e=>eventKey(e)>=(state.selected||currentDay()));
 if(state.selected)arr=arr.filter(e=>eventKey(e)===state.selected);
 if(state.filter!=="todos")arr=arr.filter(e=>e.type===state.filter);
 if(state.search)arr=arr.filter(e=>(e.title+" "+(e.course||"")).toLocaleLowerCase("es").includes(state.search));
 const box=el("events-list");box.replaceChildren();
 el("list-count").textContent=String(arr.length);
 const selected=el("selected-day");
 selected.hidden=!state.selected;
 if(state.selected){
  selected.replaceChildren();
  const sp=document.createElement("span");sp.textContent="Eventos del "+fmtLong.format(new Date(state.selected+"T12:00:00Z"));
  const clear=document.createElement("button");clear.type="button";clear.textContent="Quitar ×";clear.addEventListener("click",()=>{state.selected=null;renderCalendar();renderEvents()});
  selected.append(sp,clear);
 }
 if(!arr.length){
  const empty=document.createElement("div");empty.className="empty-state";
  const strong=document.createElement("strong");
  strong.textContent=state.status==="config"?"Pendiente de conectar Aules":state.status==="error"?"No se pudieron cargar los eventos":"No hay eventos para mostrar";
  const sub=document.createElement("span");
  sub.textContent=state.status==="config"?"El administrador debe añadir AULES_ICS_URL en GitHub Actions.":state.status==="error"?"Prueba a recargar la página.":"Prueba otro filtro o consulta una fecha diferente.";
  empty.append(strong,sub);box.append(empty);return;
 }
 for(const e of arr.slice(0,120))box.append(eventElement(e));
}
async function load(){
 try{
  const response=await fetch("./events.json",{cache:"no-store"});
  if(!response.ok)throw new Error("HTTP "+response.status);
  const data=await response.json();
  if(!Array.isArray(data.events))throw new Error("Formato inválido");
  state.events=data.events.filter(e=>e&&typeof e.title==="string"&&typeof e.start==="string"&&["examen","entrega","otro"].includes(e.type)&&(!e.all_day||/^\d{4}-\d{2}-\d{2}$/.test(e.start))&&!Number.isNaN(eventDate(e).getTime())).sort((a,b)=>eventDate(a)-eventDate(b));
  state.status=data.status==="config"?"config":"ready";
  state.manualEnabled=data.manual_enabled===true;
  el("add-exam").hidden=!state.manualEnabled;
  const stamp=data.updated_at?new Date(data.updated_at):null;
  el("last-sync").textContent=state.status==="config"?"Pendiente de configurar la sincronización":stamp&&!Number.isNaN(stamp.getTime())?"Datos actualizados: "+new Intl.DateTimeFormat("es-ES",{dateStyle:"short",timeStyle:"short",timeZone:timezone}).format(stamp):"Datos de Aules";
 }catch(err){
  state.status="error";el("last-sync").textContent="Error al cargar los datos";console.error("Error al cargar eventos",err);
 }
 renderMetrics();renderCalendar();renderEvents();
}
function installExamForm(){
 const dialog=el("add-exam-dialog"),form=el("add-exam-form");
 el("add-exam").addEventListener("click",()=>{form.reset();dialog.showModal();el("exam-name").focus()});
 const close=()=>dialog.close();
 el("close-exam").addEventListener("click",close);
 el("cancel-exam").addEventListener("click",close);
 dialog.addEventListener("click",e=>{if(e.target===dialog)close()});
 form.addEventListener("submit",e=>{
  e.preventDefault();
  if(!form.reportValidity())return;
  const title=el("exam-name").value.trim().slice(0,100);
  const day=el("exam-date").value;
  if(!title||!/^\d{4}-\d{2}-\d{2}$/.test(day))return;
  // El formato de Calendar usa fecha final exclusiva para eventos de día completo.
  const end=new Date(day+"T12:00:00Z");
  end.setUTCDate(end.getUTCDate()+1);
  const next=end.toISOString().slice(0,10).replace(/-/g,"");
  const first=day.replace(/-/g,"");
  const url=new URL("https://calendar.google.com/calendar/render");
  url.searchParams.set("action","TEMPLATE");
  url.searchParams.set("text",title);
  url.searchParams.set("dates",first+"/"+next);
  url.searchParams.set("details","Examen compartido de clase — ASIR HUB. Selecciona el calendario ASIR HUB - Exámenes antes de guardar.");
  close();
  window.location.assign(url.toString());
 });
}
function init(){
 const now=new Date();state.month=new Date(now.getFullYear(),now.getMonth(),1);
 el("today-label").textContent=fmtLong.format(now);
 installExamForm();
 el("prev-month").addEventListener("click",()=>{state.month=new Date(state.month.getFullYear(),state.month.getMonth()-1,1);renderCalendar()});
 el("next-month").addEventListener("click",()=>{state.month=new Date(state.month.getFullYear(),state.month.getMonth()+1,1);renderCalendar()});
 el("today-button").addEventListener("click",()=>{const d=new Date();state.month=new Date(d.getFullYear(),d.getMonth(),1);state.selected=null;renderCalendar();renderEvents()});
 el("event-search").addEventListener("input",e=>{state.search=e.target.value.trim().toLocaleLowerCase("es");renderEvents()});
 document.querySelectorAll("[data-filter]").forEach(button=>button.addEventListener("click",()=>{state.filter=button.dataset.filter;document.querySelectorAll("[data-filter]").forEach(b=>b.classList.toggle("active",b===button));renderEvents()}));
 load();
}
document.addEventListener("DOMContentLoaded",init);
