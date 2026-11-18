const $ = (id) => document.getElementById(id);
let token = localStorage.getItem("campus_token") || "";
let currentUser = null;
let editingTicketId = null;

function showToast(message){const el=$("toast");el.textContent=message;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),2600)}
function authHeaders(){return token?{"Authorization":`Bearer ${token}`}:{}} 
async function api(path, options={}) {
  const headers={"Content-Type":"application/json",...authHeaders(),...(options.headers||{})};
  const response=await fetch(path,{...options,headers});
  const text=await response.text(); let data={};
  try{data=text?JSON.parse(text):{}}catch{data={raw:text}}
  if(!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}
function showApp(user){currentUser=user;$("authView").classList.add("hidden");$("appView").classList.remove("hidden");$("logoutBtn").classList.remove("hidden");$("studentName").textContent=user.name;loadDashboard();}
function showAuth(){$("appView").classList.add("hidden");$("authView").classList.remove("hidden");$("logoutBtn").classList.add("hidden");}
function setAuthTab(tab){document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("active",b.dataset.tab===tab));$("loginForm").classList.toggle("hidden",tab!=="login");$("signupForm").classList.toggle("hidden",tab!=="signup");$("authMessage").textContent="";}
document.querySelectorAll(".tab").forEach(b=>b.addEventListener("click",()=>setAuthTab(b.dataset.tab)));

$("loginForm").addEventListener("submit",async e=>{e.preventDefault();const f=new FormData(e.target);try{const d=await api("/api/auth/login",{method:"POST",body:JSON.stringify({email:f.get("email"),password:f.get("password")})});token=d.access_token;localStorage.setItem("campus_token",token);showApp(d.user);showToast("Welcome back!");}catch(err){$("authMessage").textContent=err.message;}});
$("signupForm").addEventListener("submit",async e=>{e.preventDefault();const f=new FormData(e.target);try{const d=await api("/api/auth/signup",{method:"POST",body:JSON.stringify({name:f.get("name"),email:f.get("email"),password:f.get("password")})});token=d.access_token;localStorage.setItem("campus_token",token);showApp(d.user);showToast("Account created!");}catch(err){$("authMessage").textContent=err.message;}});
$("logoutBtn").addEventListener("click",()=>{token="";currentUser=null;localStorage.removeItem("campus_token");showAuth();showToast("Logged out");});

async function loadDashboard(){
 try{const [me,tickets,announcements]=await Promise.all([api("/api/me"),api("/api/tickets"),api("/api/announcements")]);currentUser=me;$("studentName").textContent=me.name;$("totalCount").textContent=tickets.length;$("openCount").textContent=tickets.filter(t=>t.status==="open"||t.status==="in_progress").length;$("resolvedCount").textContent=tickets.filter(t=>t.status==="resolved").length;renderTickets(tickets);renderAnnouncements(announcements);}
 catch(err){if(err.message.toLowerCase().includes("token")||err.message.toLowerCase().includes("auth")){token="";localStorage.removeItem("campus_token");showAuth();}else showToast(err.message);}
}
function renderTickets(tickets){const filter=$("statusFilter").value;const rows=filter?tickets.filter(t=>t.status===filter):tickets;$("ticketList").innerHTML=rows.length?rows.map(t=>`<article class="ticket"><div><strong>#${t.id} · ${escapeHtml(t.issue)}</strong><p>${escapeHtml(t.description)}</p><small>${escapeHtml(t.location)} · ${new Date(t.created_at).toLocaleString()}</small></div><div class="ticket-actions"><span class="status ${t.status}">${t.status.replace("_"," ")}</span><button class="mini-btn" onclick="editTicket(${t.id})">Edit</button><button class="mini-btn" onclick="deleteTicket(${t.id})">Delete</button></div></article>`).join(""):`<div class="empty">No requests found. Report your first issue!</div>`;}
function renderAnnouncements(rows){$("announcementList").innerHTML=rows.map(a=>`<div class="announcement"><strong>${escapeHtml(a.title)}</strong><p>${escapeHtml(a.message)}</p></div>`).join("")||"No announcements yet.";}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
$("statusFilter").addEventListener("change",loadDashboard);
$("newTicketBtn").addEventListener("click",()=>{$("ticketFormPanel").scrollIntoView({behavior:"smooth"});$("ticketForm").reset();editingTicketId=null;$("formTitle").textContent="Report a problem";$("cancelEdit").classList.add("hidden");});
$("ticketForm").addEventListener("submit",async e=>{e.preventDefault();const f=new FormData(e.target);const body={issue:f.get("issue"),location:f.get("location"),description:f.get("description")};try{if(editingTicketId){await api(`/api/tickets/${editingTicketId}`,{method:"PUT",body:JSON.stringify(body)});showToast("Ticket updated");}else{await api("/api/tickets",{method:"POST",body:JSON.stringify(body)});showToast("Complaint submitted");}e.target.reset();editingTicketId=null;$("formTitle").textContent="Report a problem";$("cancelEdit").classList.add("hidden");$("ticketMessage").textContent="";loadDashboard();}catch(err){$("ticketMessage").textContent=err.message;}});
window.editTicket=async id=>{try{const t=await api(`/api/tickets/${id}`);editingTicketId=id;const f=$("ticketForm");f.issue.value=t.issue;f.location.value=t.location;f.description.value=t.description;$("formTitle").textContent=`Edit ticket #${id}`;$("cancelEdit").classList.remove("hidden");$("ticketFormPanel").scrollIntoView({behavior:"smooth"});}catch(err){showToast(err.message);}};
window.deleteTicket=async id=>{if(!confirm(`Delete ticket #${id}?`))return;try{await api(`/api/tickets/${id}`,{method:"DELETE"});showToast("Ticket deleted");loadDashboard();}catch(err){showToast(err.message);}};
$("cancelEdit").addEventListener("click",()=>{$("ticketForm").reset();editingTicketId=null;$("formTitle").textContent="Report a problem";$("cancelEdit").classList.add("hidden");});

$("sendRequest").addEventListener("click",async()=>{
 const method=$("method").value;let endpoint=$("endpoint").value.trim();if(!endpoint.startsWith("/"))endpoint="/"+endpoint;
 const query=$("query").value.trim();if(query)endpoint+=(endpoint.includes("?")?"&":"?")+query;
 let extra={};try{extra=$("headers").value.trim()?JSON.parse($("headers").value):{};}catch{$("responseOutput").textContent="Headers must be valid JSON.";return;}
 const headers={...authHeaders(),...extra};const options={method,headers};
 if(["POST","PUT","PATCH"].includes(method)){try{options.body=$("body").value.trim()?JSON.stringify(JSON.parse($("body").value)): "{}";headers["Content-Type"]="application/json";}catch{$("responseOutput").textContent="Request body must be valid JSON.";return;}}
 $("responseOutput").textContent="Sending request…";$("responseStatus").textContent="Sending";
 try{const response=await fetch(endpoint,options);const raw=await response.text();let data;try{data=raw?JSON.parse(raw):{};}catch{data=raw;}$("responseStatus").textContent=`${response.status} ${response.statusText}`;$("responseOutput").textContent=JSON.stringify(data,null,2);}
 catch(err){$("responseStatus").textContent="Network error";$("responseOutput").textContent=err.message;}
});
async function boot(){if(token){try{const me=await api("/api/me");showApp(me);return;}catch{token="";localStorage.removeItem("campus_token");}}showAuth();}
boot();
