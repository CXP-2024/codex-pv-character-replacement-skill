"""Run a queue of chained H3 Ref2VA jobs on one GPU. See comfyui/README.md."""
import json,time,hashlib,shutil,subprocess,threading,traceback,os
from pathlib import Path
import requests
R=Path(os.environ.get('H3_ROOT','/opt/h3')); C=R/'ComfyUI'; P=R/'chain'; P.mkdir(exist_ok=True)
s=requests.Session();s.trust_env=False;base=os.environ.get('COMFY_URL','http://127.0.0.1:8188')
def write(p,o):p.write_text(json.dumps(o,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def submit(g,d,stage):
 write(d/(stage+'_workflow.json'),g)
 r=s.post(base+'/prompt',json={'prompt':g,'client_id':d.name+'_'+stage},timeout=60)
 if not r.ok:raise RuntimeError(r.text)
 pid=r.json()['prompt_id'];write(d/(stage+'_submission.json'),{'prompt_id':pid,'time':time.time()})
 t=time.monotonic()
 while time.monotonic()-t<5400:
  h=s.get(base+'/history/'+pid,timeout=30).json().get(pid)
  if h:
   write(d/(stage+'_history.json'),h)
   if h.get('status',{}).get('status_str')=='error':raise RuntimeError(str(h['status']))
   if h.get('status',{}).get('completed'):return h,time.monotonic()-t
  time.sleep(3)
 s.post(base+'/interrupt',timeout=30)
 raise TimeoutError(pid)
q=s.get(base+'/queue',timeout=30).json();assert not q['queue_running'] and not q['queue_pending']
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,name,memory.total','--format=csv,noheader'],text=True).strip()
lock=R/'chain_gpu.lock'
with lock.open('x') as f:json.dump({'pid':os.getpid(),'gpu':gpu,'time':time.time()},f)
JOBS=json.loads((R/'chain_jobs.json').read_text())
def finished(x):return (P/x/'result.json').exists() or (P/x/'error.txt').exists()
def next_job():
 for x in JOBS:
  if finished(x['id']):continue
  par=x.get('parent')
  if par and (P/par/'error.txt').exists():
   (P/x['id']).mkdir(exist_ok=True);(P/x['id']/'error.txt').write_text('parent failed: '+par);print('SKIP',x['id'],'parent failed',flush=True);continue
  if par and not (P/par/'result.json').exists():continue
  return x
while True:
 j=next_job()
 if j is None:break
 d=P/j['id'];d.mkdir(exist_ok=True)
 if j.get('parent'):
  # Picture 1 = the parent's actual lossless H3 frame at parent_model_frame
  frames=sorted((C/'output/chain_lossless'/j['parent']).glob('*.png'))
  shutil.copy2(frames[j['parent_model_frame']],R/'chain_inputs'/f"{j['id']}.png")
  write(d/'guide_source.json',{'parent':j['parent'],'parent_model_frame':j['parent_model_frame'],'file':frames[j['parent_model_frame']].name})
 samples=[];stop=threading.Event()
 def monitor():
  while not stop.is_set():
   try:
    v=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu,temperature.gpu','--format=csv,noheader,nounits'],text=True).strip()
    samples.append({'time':time.time(),'gpu':v})
   except Exception:pass
   stop.wait(2)
 th=threading.Thread(target=monitor,daemon=True);th.start()
 try:
  print('START',j['id'],j['length'],flush=True);write(d/'job.json',j)
  for ext in ['png','mp4']:shutil.copy2(R/'chain_inputs'/f"{j['id']}.{ext}",C/'input'/f"{j['id']}.{ext}")
  write(d/'input_hashes.json',{ext:sha(R/'chain_inputs'/f"{j['id']}.{ext}") for ext in ['png','mp4','txt']})
  g=json.loads((R/'workflows/H3_Ref2VA_Encode_API.json').read_text())
  g['200']['inputs']['image']=j['id']+'.png';g['210']['inputs']['file']=j['id']+'.mp4'
  g['104']['inputs'].update({k:j[k] for k in ['width','height','length']})
  g['104']['inputs']['prompt']=(R/'chain_inputs'/f"{j['id']}.txt").read_text()
  g['303']={'class_type':'MiniMaxH3AddGuide','inputs':{'positive':['104',0],'latent':['104',1],'vae':['11',0],'image':['200',0],'frame_idx':j['anchor_frame']}}
  g['301']['inputs']['conditioning']=['303',0];g['301']['inputs']['filename_prefix']='chain_cache/'+j['id']
  # extra keyframe guides at their own model frames (repair reruns of fast shots)
  for k,e in enumerate(j.get('additional_anchors',[])):
   fn=e['image'];shutil.copy2(R/'chain_inputs'/fn,C/'input'/fn)
   g[str(500+k)]={'class_type':'LoadImage','inputs':{'image':fn}}
   g[str(600+k)]={'class_type':'MiniMaxH3AddGuide','inputs':{'positive':g['301']['inputs']['conditioning'],'latent':['104',1],'vae':['11',0],'image':[str(500+k),0],'frame_idx':e['frame']}}
   g['301']['inputs']['conditioning']=[str(600+k),0]
  h,enc=submit(g,d,'encode');cache=Path(h['outputs']['301']['cache_files'][0]);target=C/'models/embeddings'/cache.name;shutil.copy2(cache,target)
  write(d/'cache_binding.json',{'cache_sha256':sha(target),'encode_workflow_sha256':sha(d/'encode_workflow.json'),'gpu':gpu})
  g=json.loads((R/'workflows/H3_Ref2VA_Sample_API.json').read_text())
  g['302']['inputs']['cache_name']=target.name;g['15']['inputs']['noise_seed']=j['seed'];g['92']['inputs']['filename_prefix']='chain/'+j['id']
  g['93']={'class_type':'SaveImage','inputs':{'images':['10',0],'filename_prefix':'chain_lossless/'+j['id']+'/frame'}}
  h,sampling=submit(g,d,'sample')
  videos=list((C/'output/chain').glob(j['id']+'*.mp4'));assert len(videos)==1,videos
  shutil.copy2(videos[0],d/'raw.mp4')
  pngs=sorted((C/'output/chain_lossless'/j['id']).glob('*.png'));assert len(pngs)==j['length']
  subprocess.run(['ffmpeg','-v','error','-y','-framerate','24','-pattern_type','glob','-i',str(C/'output/chain_lossless'/j['id']/'*.png'),'-c:v','ffv1','-level','3','-threads','8',str(d/'lossless.mkv')],check=True)
  from PIL import Image,ImageDraw
  indexes=sorted(set([0,j['anchor_frame'],j['length']//4,j['length']//2,3*j['length']//4,j['length']-1]))
  sheet=Image.new('RGB',(1440,2*300),'#111827')
  for k,idx in enumerate(indexes):
   im=Image.open(pngs[idx]).convert('RGB');im.thumbnail((480,270));x=(k%3)*480;y=(k//3)*300;sheet.paste(im,(x,y+25));ImageDraw.Draw(sheet).text((x+5,y+5),f'{j["id"]} frame {idx}',fill='white')
  sheet.save(d/'contact.jpg',quality=95)
  probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(d/'raw.mp4')]))
  write(d/'result.json',{'status':'generated_qc_pending','encode_seconds':enc,'sample_decode_seconds':sampling,'peak_gpu_mib':max(int(x['gpu'].split(',')[0]) for x in samples),'gpu':gpu,'raw_sha256':sha(d/'raw.mp4'),'probe':probe})
  print('DONE',j['id'],enc,sampling,flush=True)
 except Exception:
  (d/'error.txt').write_text(traceback.format_exc());print('FAILED',j['id'],traceback.format_exc(),flush=True)
  s.post(base+'/free',json={'unload_models':True,'free_memory':True},timeout=60)
 finally:
  stop.set();th.join();write(d/'gpu_samples.json',samples)
lock.rename(R/('chain_gpu.completed_'+str(int(time.time()))+'.json'))
print('ALL_JOBS_COMPLETE',flush=True)
