import {useEffect,useMemo,useState} from 'react'
import {Download,Image as ImageIcon,RefreshCw,Square,Upload,WandSparkles} from 'lucide-react'

type Scene={scene_number:number;start_seconds:number;end_seconds:number;transcript:string;visual_description:string;image_prompt:string;negative_prompt:string;historical_context?:string|null;importance:number;image_count:number}
type Storyboard={title:string;audio_duration:number;scenes:Scene[]}
type Status={project_id:string;stage:string;detail:string;progress:number;cancelled:boolean}
const API='http://127.0.0.1:8000'
const fmt=(s:number)=>`${Math.floor(s/60)}:${(s%60).toFixed(1).padStart(4,'0')}`

export default function App(){
 const[file,setFile]=useState<File|null>(null),[project,setProject]=useState(''),[status,setStatus]=useState<Status|null>(null)
 const[story,setStory]=useState<Storyboard|null>(null),[health,setHealth]=useState<any>(null),[busy,setBusy]=useState(false)
 const[opts,setOpts]=useState({aspect:'16:9',style:'Cinematic',min_scene_seconds:5,max_scene_seconds:12,images_per_scene:1,automatic_image_count:true,historical_accuracy:true,seed:42,steps:24,cfg:6.5,quality:'Standard',image_engine:'comfyui',checkpoint:''})
 useEffect(()=>{fetch(`${API}/api/health`).then(r=>r.json()).then(setHealth).catch(()=>{})},[])
 useEffect(()=>{if(!project)return;const t=setInterval(async()=>{const r=await fetch(`${API}/api/projects/${project}/status`);if(!r.ok)return;const s=await r.json();setStatus(s);if(s.stage==='Complete'){clearInterval(t);const q=await fetch(`${API}/api/projects/${project}/storyboard`);if(q.ok)setStory(await q.json());setBusy(false)}if(s.stage==='Error'||s.stage==='Cancelled'){clearInterval(t);setBusy(false)}},1200);return()=>clearInterval(t)},[project])
 const canRun=useMemo(()=>!!file&&!busy,[file,busy])
 async function generate(){if(!file)return;setStory(null);setBusy(true);const f=new FormData();f.append('audio',file);f.append('options_json',JSON.stringify(opts));const r=await fetch(`${API}/api/projects`,{method:'POST',body:f});if(!r.ok){setBusy(false);alert(await r.text());return}setProject((await r.json()).project_id)}
 async function cancel(){if(project)await fetch(`${API}/api/projects/${project}/cancel`,{method:'POST'})}
 async function regen(scene:Scene){const prompt=window.prompt('Edit image prompt',scene.image_prompt);if(prompt===null)return;const r=await fetch(`${API}/api/projects/${project}/scenes/${scene.scene_number}/regenerate`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({image_prompt:prompt,options:opts})});if(!r.ok)alert(await r.text());else setStory(s=>s?{...s,scenes:s.scenes.map(x=>x.scene_number===scene.scene_number?{...x,image_prompt:prompt}:x)}:s)}
 return <main className="shell">
  <header><div><div className="eyebrow">LOCAL • WINDOWS 11 • OLLAMA</div><h1>MoneyPrint Junior <span>Audio → Image</span></h1><p>Turn a sermon, documentary, story or soundtrack into a chronological visual storyboard.</p></div>
   <div className="health"><b>System</b><span className={health?.ollama?'ok':'bad'}>Ollama {health?.ollama?'ready':'offline'}</span><span className={health?.comfyui?'ok':'warn'}>ComfyUI {health?.comfyui?'ready':'not detected'}</span></div>
  </header>
  <section className="panel grid"><label className="drop"><Upload size={30}/><b>{file?file.name:'Choose WAV, MP3 or M4A'}</b><span>{file?'Ready to analyze':'Audio stays on your machine'}</span><input type="file" accept=".wav,.mp3,.m4a,audio/*" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
   <div className="controls">
    <label>Aspect<select value={opts.aspect} onChange={e=>setOpts({...opts,aspect:e.target.value})}><option>16:9</option><option>9:16</option><option>1:1</option></select></label>
    <label>Style<select value={opts.style} onChange={e=>setOpts({...opts,style:e.target.value})}>{['Photorealistic','Cinematic','Documentary','Historical','Biblical','Classical Painting','Illustration','Dark Dramatic','Inspirational'].map(x=><option key={x}>{x}</option>)}</select></label>
    <label>Quality<select value={opts.quality} onChange={e=>setOpts({...opts,quality:e.target.value})}><option>Draft</option><option>Standard</option><option>High</option></select></label>
    <label>Checkpoint<input value={opts.checkpoint} placeholder="model.safetensors" onChange={e=>setOpts({...opts,checkpoint:e.target.value})}/></label>
    <label>Min scene<input type="number" value={opts.min_scene_seconds} onChange={e=>setOpts({...opts,min_scene_seconds:+e.target.value})}/></label>
    <label>Max scene<input type="number" value={opts.max_scene_seconds} onChange={e=>setOpts({...opts,max_scene_seconds:+e.target.value})}/></label>
    <label className="check"><input type="checkbox" checked={opts.historical_accuracy} onChange={e=>setOpts({...opts,historical_accuracy:e.target.checked})}/>Historical Accuracy</label>
    <button className="primary" disabled={!canRun} onClick={generate}><WandSparkles size={18}/>Generate Storyboard</button>
   </div>
  </section>
  {status&&<section className="panel progress"><div><b>{status.stage}</b><span>{status.detail}</span></div><div className="bar"><i style={{width:`${Math.round(status.progress*100)}%`}}/></div><div className="row"><span>{Math.round(status.progress*100)}%</span>{busy&&<button className="ghost" onClick={cancel}><Square size={15}/>Cancel</button>}</div></section>}
  {status?.stage==='Error'&&<section className="error">{status.detail}</section>}
  {story&&<section className="story"><div className="storyhead"><div><div className="eyebrow">STORYBOARD</div><h2>{story.title}</h2><p>{story.scenes.length} scenes • {fmt(story.audio_duration)}</p></div><a className="primary link" href={`${API}/api/projects/${project}/export`}><Download size={18}/>Download ZIP</a></div>
   {story.scenes.map(scene=><article className="scene" key={scene.scene_number}><div className="thumb"><img src={`${API}/api/projects/${project}/images/${scene.scene_number}/1`} onError={e=>{e.currentTarget.style.display='none'}}/><ImageIcon className="placeholder"/></div><div className="sceneinfo"><div className="sceneTop"><b>Scene {String(scene.scene_number).padStart(3,'0')}</b><span>{fmt(scene.start_seconds)} → {fmt(scene.end_seconds)}</span></div><p className="transcript">{scene.transcript||'No speech in this scene.'}</p><label>Prompt<textarea defaultValue={scene.image_prompt}/></label>{scene.historical_context&&<small>{scene.historical_context}</small>}<button className="ghost" onClick={()=>regen(scene)}><RefreshCw size={15}/>Edit + Regenerate Scene</button></div></article>)}
  </section>}
 </main>
}
