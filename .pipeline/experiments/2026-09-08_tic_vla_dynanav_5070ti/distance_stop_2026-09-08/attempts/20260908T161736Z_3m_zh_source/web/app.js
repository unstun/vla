"use strict";
const $ = (id) => document.getElementById(id);
let state = {}, busy = false, held = false, recorder = null, media = null, timer = null;
let lastSample = null, lastImage = null, pendingCommand = null;
let voiceGeneration = 0, imageCount = 0;
function message(text, error = false) { $("message").textContent = text; $("message").classList.toggle("error", error); }
async function api(path, payload, audio = false) {
  const response = await fetch(`/api/${path}`, {method:"POST", headers:{"X-Demo-Request":"1","Content-Type":audio?"application/octet-stream":"application/json"}, body:audio?payload:JSON.stringify(payload || {})});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "请求失败，请重试。");
  return result;
}
function controls() {
  const ready = state.connected && state.ready && !state.stale;
  $("send").disabled = !ready || busy;
  $("mic").disabled = !ready || busy || state.asr_status !== "ready";
  $("stop").disabled = !state.connected;
  $("resume").disabled = !ready || !state.held || !state.last_command;
  $("start").disabled = state.connected || state.launch?.starting;
}
async function send(text, source = "text") {
  if(source !== "voice") voiceGeneration++;
  try {
    const result = await api("command", {text, source});
    pendingCommand = result.id;
    message(`已发送「${text}」，等待仿真确认…`);
    if (result.instruction) $("model-instruction").textContent = result.instruction;
  } catch(error) { message(error.message, true); }
}
$("send").addEventListener("click", () => send($("instruction").value));
$("instruction").addEventListener("keydown", e => {if(e.key === "Enter" && !$("send").disabled) send($("instruction").value);});
$("stop").addEventListener("click", () => {stopRecording(true);send("停下", "button");});
$("resume").addEventListener("click", () => send("继续", "button"));
$("start").addEventListener("click", async () => {
  $("start").disabled = true;
  try {await api("start"); message("正在启动医院仿真，场景加载后会保持静止。");} catch(error) {message(error.message,true);}
});
function stopRecording(cancel = false) {
  if(cancel) voiceGeneration++;
  held = false;
  clearTimeout(timer);
  if(recorder?.state === "recording") recorder.stop();
  $("mic").classList.remove("recording");
  $("mic-label").textContent = "按住说话";
}
async function startRecording(event) {
  if($("mic").disabled || busy || held) return;
  held = true;
  const generation = ++voiceGeneration;
  if(event?.pointerId !== undefined) $("mic").setPointerCapture(event.pointerId);
  try {
    if(!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) throw new Error("此浏览器不支持录音，请用 Chrome 打开本页面。");
    media = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
    if(!held) {media.getTracks().forEach(track=>track.stop()); media=null; return;}
    const chunks = [];
    recorder = new MediaRecorder(media);
    recorder.addEventListener("dataavailable", e => {if(e.data.size) chunks.push(e.data);});
    recorder.addEventListener("stop", async () => {
      const blob = new Blob(chunks,{type:recorder.mimeType});
      media.getTracks().forEach(track=>track.stop()); media=null; recorder=null;
      if(generation !== voiceGeneration) return;
      busy = true; controls(); message("正在本机识别语音…");
      try {
        const result = await api("transcribe", blob, true);
        if(generation !== voiceGeneration) return;
        $("transcript").textContent = `${result.text}（${result.asr_seconds.toFixed(2)} 秒）`;
        $("instruction").value = result.text;
        await send(result.text, "voice");
      } catch(error) {message(error.message,true);} finally {busy=false;controls();}
    },{once:true});
    recorder.start(); $("mic").classList.add("recording"); $("mic-label").textContent="松开发送";
    message("正在聆听… 例如：走到自动售货机前。");
    timer = setTimeout(stopRecording, 9800);
  } catch(error) {
    held=false; if(media) media.getTracks().forEach(track=>track.stop()); media=null;
    message(error.name === "NotAllowedError" ? "麦克风未获许可。请在地址栏允许麦克风，或使用文字输入。" : error.message,true);
  }
}
$("mic").addEventListener("pointerdown", startRecording);
$("mic").addEventListener("pointerup", () => stopRecording());
$("mic").addEventListener("pointercancel", () => stopRecording(true));
$("mic").addEventListener("keydown", e=>{if((e.code==="Space"||e.code==="Enter")&&!e.repeat){e.preventDefault();startRecording();}});
$("mic").addEventListener("keyup", e=>{if(e.code==="Space"||e.code==="Enter"){e.preventDefault();stopRecording();}});
window.addEventListener("blur", () => stopRecording(true));
async function updateImage(id, name, sequence) {
  const response = await fetch(`/api/${name}.jpg?seq=${sequence}`);
  if(!response.ok) return false;
  const blob = await response.blob(), url = URL.createObjectURL(blob);
  const image = new Image(); image.src = url;
  try { await image.decode(); } catch {URL.revokeObjectURL(url);return false;}
  const old = $(id).src;
  $(id).src = url; $(id).hidden = false;
  if(old.startsWith("blob:")) URL.revokeObjectURL(old);
  return true;
}
function renderMap() {
  const actual=state.actual_world||[], planned=state.planned_world||[], all=[...actual,...planned];
  if(!all.length)return;
  const xs=all.map(p=>p[0]),ys=all.map(p=>p[1]);
  const minX=Math.min(...xs)-1,maxX=Math.max(...xs)+1,minY=Math.min(...ys)-1,maxY=Math.max(...ys)+1;
  const scale=Math.min(280/(maxX-minX),165/(maxY-minY));
  const pos=p=>[20+(p[0]-minX)*scale,185-(p[1]-minY)*scale];
  const line=(pts,color)=>`<polyline points="${pts.map(p=>pos(p).join(",")).join(" ")}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`;
  const current=actual.length?pos(actual[actual.length-1]):[20,185];
  $("map").innerHTML=line(actual,"#faa428")+line(planned,"#28d8e1")+`<circle cx="${current[0]}" cy="${current[1]}" r="5" fill="#fff"/>`;
}
async function poll() {
  try {
    const response=await fetch("/api/status");state=await response.json();
    const live=state.connected&&state.ready&&!state.stale;
    $("connection").textContent=live?"● 仿真实时连接":state.connected?"画面更新延迟":state.launch?.starting?"正在加载场景…":"仿真未运行";
    $("connection").classList.toggle("live",live);
    $("asr-state").textContent=state.asr_status==="ready"?"支持中文 · 录音仅在本机识别 · 松开发送":state.asr_status==="error"?"语音识别加载失败，可使用文字输入":"正在加载本机语音识别…";
    $("start").textContent=state.launch?.starting?"正在启动…":"启动仿真";
    $("motion").textContent=!state.connected?"等待启动":state.stale?"等待更新":state.held?"静止 / 等待指令":"正在导航";
    $("velocity").textContent=state.connected&&state.v!==undefined?`${state.v.toFixed(2)} m/s`:"—";
    $("frame").textContent=state.connected?state.frame??"—":"—";
    $("stale").hidden=live||lastImage===null;
    if(!live) $("frequency").textContent="—";
    if(state.launch?.error) message(state.launch.error,true);
    if(pendingCommand&&state.ack?.id===pendingCommand){message(`已执行「${state.ack.text}」`);pendingCommand=null;}
    if(live&&lastImage!==`${state.run_id}:${state.sequence}`){
      lastImage=`${state.run_id}:${state.sequence}`;
      const frames=await Promise.allSettled([updateImage("scene","third_person",state.sequence),updateImage("front","front",state.sequence)]);
      if(frames[0].status==="fulfilled"&&frames[0].value){$("placeholder").hidden=true;imageCount++;}
      if(frames[1].status==="fulfilled"&&frames[1].value)$("front-placeholder").hidden=true;
      const now=performance.now();
      if(lastSample&&lastSample.run===state.run_id&&now-lastSample.time>1200){$("frequency").textContent=`${((imageCount-lastSample.count)/((now-lastSample.time)/1000)).toFixed(1)} Hz`;lastSample=null;}
      if(!lastSample||lastSample.run!==state.run_id)lastSample={count:imageCount,time:now,run:state.run_id};
      renderMap();
    }
  } catch(error){state={};$("connection").textContent="本机服务断开";$("stale").hidden=lastImage===null;}
  controls();setTimeout(poll,400);
}
poll();
