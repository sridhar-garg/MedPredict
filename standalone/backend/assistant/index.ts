const allowed = new Set(["http://127.0.0.1:8766", "https://appassets.androidplatform.net"]);
const systemInstruction = "You are MedPredict's educational assistant. Explain general health concepts and medical terminology with uncertainty. Never diagnose, calculate an individual's disease risk, give dosing instructions, prescribe treatment, or replace a clinician. If a question indicates a possible emergency, advise seeking local emergency medical care. Do not ask for or repeat identifying information. Explain when evidence is insufficient.";

Deno.serve(async (req) => {
  const origin = req.headers.get("origin") || "";
  const headers: Record<string,string> = {"Content-Type":"application/json", "Cache-Control":"no-store", "Vary":"Origin", "Access-Control-Allow-Headers":"authorization,apikey,content-type", "Access-Control-Allow-Methods":"POST,OPTIONS"};
  if (allowed.has(origin)) headers["Access-Control-Allow-Origin"] = origin;
  const reply = (data:object,status=200) => new Response(JSON.stringify(data),{status,headers});
  if (!allowed.has(origin)) return reply({error:"Origin not allowed."},403);
  if(req.method==="OPTIONS") return new Response(null,{status:204,headers});
  if (req.method !== "POST") return reply({error:"Method not allowed."},405);
  const bearer = req.headers.get("Authorization") || "";
  if (!/^Bearer [A-Za-z0-9._-]+$/.test(bearer)) return reply({error:"Sign in with Google first."},401);
  try {
    const url = Deno.env.get("SUPABASE_URL")!;
    const publicKey = Deno.env.get("SUPABASE_ANON_KEY")!;
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const geminiKey = Deno.env.get("GEMINI_API_KEY");
    const model = Deno.env.get("GEMINI_MODEL");
    if (!geminiKey || !model || !/^[a-zA-Z0-9._-]+$/.test(model)) return reply({error:"Online AI is not configured."},503);
    const userRes = await fetch(`${url}/auth/v1/user`,{headers:{apikey:publicKey,Authorization:bearer},signal:AbortSignal.timeout(8000)});
    if(!userRes.ok) return reply({error:"Your sign-in expired. Sign in again."},401);
    const user = await userRes.json();
    if(user.app_metadata?.provider!=="google" || !user.email_confirmed_at) return reply({error:"A verified Google account is required."},403);
    const length = Number(req.headers.get("content-length") || 0);
    if(length>8192) return reply({error:"Question too long."},413);
    const raw=await req.text(); if(raw.length>8192)return reply({error:"Question too long."},413);
    const data=JSON.parse(raw);
    if (typeof data.question !== "string" || !data.question.trim() || data.question.length>2000 || data.consent!==true) return reply({error:"An educational question (up to 2,000 characters) and consent are required."},400);
    const quota = await fetch(`${url}/rest/v1/rpc/mp_claim_ai_call`,{method:"POST",headers:{apikey:serviceKey,Authorization:`Bearer ${serviceKey}`,"Content-Type":"application/json"},body:JSON.stringify({p_user:user.id}),signal:AbortSignal.timeout(8000)});
    if(!quota.ok) return reply({error:"Unable to reserve an online AI request."},503);
    if(await quota.json()!==true) return reply({error:"Daily online AI limit reached. The offline condition atlas is still available."},429);
    const res=await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,{method:"POST",headers:{"Content-Type":"application/json","x-goog-api-key":geminiKey},body:JSON.stringify({systemInstruction:{parts:[{text:systemInstruction}]},contents:[{role:"user",parts:[{text:data.question}]}],generationConfig:{maxOutputTokens:600,temperature:0.3}}),signal:AbortSignal.timeout(20000)});
    if(!res.ok)return reply({error:"Online AI is currently unavailable."},503);
    const result=await res.json();
    const answer=result.candidates?.[0]?.content?.parts?.map((p:{text?:string})=>p.text||"").join("").trim();
    if(!answer)return reply({error:"No answer was available for that question. Try a general educational question."},422);
    return reply({answer:answer.slice(0,12000)});
  }catch { return reply({error:"Online AI request could not be completed."},503); }
});
