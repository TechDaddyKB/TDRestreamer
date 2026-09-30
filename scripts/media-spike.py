#!/usr/bin/env python3
"""Loopback-only protocol spike. No external destinations or platform accounts."""
import json
import array
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess as sp
import time
import urllib.request

root=Path(__file__).resolve().parents[1]
work=root/'runtime'/'media-spike';work.mkdir(parents=True,exist_ok=True)
gateway=os.environ.get('MEDIAMTX_BIN',str(root/'.tools/mediamtx/mediamtx'))
if not Path(gateway).is_file():raise SystemExit('Set MEDIAMTX_BIN to a checksum-verified MediaMTX v1.21.1 binary.')
for cmd in ['ffmpeg','ffprobe']:
 if not shutil.which(cmd):raise SystemExit(f'{cmd} is required')
config='''logLevel: warn
rtspAddress: 127.0.0.1:18554
rtspTransports: [tcp]
rtmpAddress: 127.0.0.1:19350
hlsAddress: 127.0.0.1:18888
hlsVariant: mpegts
webrtcAddress: 127.0.0.1:18889
webrtcLocalUDPAddress: 127.0.0.1:18189
webrtcIPsFromInterfaces: false
webrtcAdditionalHosts: [127.0.0.1]
webrtcICEServers2: []
srtAddress: 127.0.0.1:18890
authMethod: internal
authInternalUsers:
- user: any
  ips: [127.0.0.1, '::1']
  permissions:
  - action: publish
  - action: read
paths:
  all_others:
'''
(work/'mediamtx.yml').write_text(config)
procs=[];logs=[]
def launch(name,args):
 f=(work/(name+'.log')).open('w');logs.append(f);p=sp.Popen(args,stdout=f,stderr=sp.STDOUT,cwd=work);procs.append(p);return p

def run(args,timeout=30):
 p=sp.run(args,capture_output=True,timeout=timeout)
 if p.returncode:raise RuntimeError(p.stderr.decode()[-2500:])
 return p.stdout

def probe(url):
 args=['ffprobe','-v','error']
 if url.startswith('rtsp'):args+=['-rtsp_transport','tcp']
 if url.startswith('rtmp'):args+=['-rtmp_enhanced_codecs','avc1,mp4a']
 return json.loads(run(args+['-show_streams','-of','json',url],15))['streams']

report={'gateway':run([gateway,'--version']).decode().strip(),'ffmpeg':run(['ffmpeg','-version']).decode().splitlines()[0],'tests':{},'limitations':['Synthetic source, not real OBS','No Twitch or other platform delivery tested','No authenticated browser WebRTC playback tested','No hardware qualification or long soak','No application worker/publisher integration']}
try:
 p=launch('gateway',[gateway,str(work/'mediamtx.yml')])
 for _ in range(50):
  if p.poll() is not None:raise RuntimeError((work/'gateway.log').read_text())
  try:
   with socket.create_connection(('127.0.0.1',18554),timeout=.2):break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('gateway did not bind')
 source=launch('source',['ffmpeg','-nostdin','-hide_banner','-loglevel','warning','-re','-f','lavfi','-i','testsrc2=size=640x360:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-f','lavfi','-i','sine=frequency=880:sample_rate=48000','-map','0:v','-map','1:a','-map','2:a','-c:v','libx264','-preset','ultrafast','-tune','zerolatency','-g','30','-c:a','aac','-f','rtsp','-rtsp_transport','tcp','rtsp://127.0.0.1:18554/source'])
 time.sleep(2)
 tracks=probe('rtsp://127.0.0.1:18554/source')
 assert [s['codec_type'] for s in tracks].count('audio')==2
 report['tests']['rtsp_multi_audio']={'passed':True,'codecs':[s['codec_name'] for s in tracks]}
 relay=launch('enhanced-relay',['ffmpeg','-nostdin','-hide_banner','-loglevel','warning','-rtsp_transport','tcp','-i','rtsp://127.0.0.1:18554/source','-map','0','-c','copy','-rtmp_enhanced_codecs','avc1,mp4a','-f','flv','rtmp://127.0.0.1:19350/relayed'])
 time.sleep(2)
 try:
  tracks=probe('rtmp://127.0.0.1:19350/relayed')
  assert [s['codec_type'] for s in tracks].count('audio')==2
  report['tests']['enhanced_rtmp_multi_audio']={'passed':True,'codecs':[s['codec_name'] for s in tracks]}
 except Exception as e:
  report['tests']['enhanced_rtmp_multi_audio']={'passed':False,'reason':str(e),'relay_log':(work/'enhanced-relay.log').read_text()[-2000:]}
 # Distinct publisher process, selecting only the second supplied mix.
 selected=launch('selected',['ffmpeg','-nostdin','-hide_banner','-loglevel','warning','-rtsp_transport','tcp','-i','rtsp://127.0.0.1:18554/source','-map','0:v:0','-map','0:a:1','-c','copy','-f','flv','rtmp://127.0.0.1:19350/selected'])
 time.sleep(2)
 tracks=probe('rtmp://127.0.0.1:19350/selected');assert len(tracks)==2
 samples=array.array('h',run(['ffmpeg','-nostdin','-v','error','-i','rtmp://127.0.0.1:19350/selected','-map','0:a:0','-t','1','-ar','48000','-ac','1','-f','s16le','pipe:1'],15))
 def power(hz):
  real=sum(v*math.cos(2*math.pi*hz*n/48000) for n,v in enumerate(samples))
  imag=sum(v*math.sin(2*math.pi*hz*n/48000) for n,v in enumerate(samples))
  return real*real+imag*imag
 assert power(880)>100*max(1,power(440)), 'selected mix is not the expected 880 Hz tone'
 report['tests']['selected_audio_relay']={'passed':True,'audio_tracks':1,'audio_identity_verified':True,'expected_tone_hz':880}

 failed=sp.run(['ffmpeg','-nostdin','-v','error','-rtsp_transport','tcp','-i','rtsp://127.0.0.1:18554/source','-map','0:v:0','-map','0:a:0','-c','copy','-f','flv','rtmp://127.0.0.1:19351/unavailable'],capture_output=True,timeout=15)
 assert failed.returncode!=0 and selected.poll() is None
 assert len(probe('rtmp://127.0.0.1:19350/selected'))==2
 report['tests']['independent_process_failure']={'passed':True,'limitation':'connection refusal, not stalled-socket/backpressure qualification'}
 with urllib.request.urlopen('http://127.0.0.1:18888/selected/index.m3u8',timeout=20) as res:
  playlist=res.read().decode();assert '#EXTM3U' in playlist
 report['tests']['hls_playlist']={'passed':True,'browser_playback_verified':False}
finally:
 for p in reversed(procs):
  if p.poll() is None:
   p.terminate()
   try:p.wait(timeout=5)
   except sp.TimeoutExpired:p.kill();p.wait()
 for f in logs:f.close()
 (work/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if any(not result['passed'] for result in report['tests'].values()):raise SystemExit(1)
