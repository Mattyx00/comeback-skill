#!/usr/bin/env python3
"""comeback · youtube — local HTTP server for YouTube IFrame control."""

import http.server
import json
import sys
import threading
import urllib.parse
import time

PORT = 7777
state = {"cmd": "pause", "video_id": ""}
lock = threading.Lock()
play_locked_until = 0  # epoch seconds; /pause is ignored while time() < this

PLAYER_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>comeback · youtube ▶</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{background:#000;overflow:hidden}
    #player{position:fixed;inset:0;width:100%;height:100%}
    #hud{position:fixed;top:10px;right:12px;background:rgba(0,0,0,.65);
         color:#fff;padding:4px 10px;border-radius:6px;font:12px/1.5 monospace;
         z-index:9;cursor:pointer;user-select:none}
  </style>
</head>
<body>
<div id="player"></div>
<div id="hud" title="Clicca per attivare/disattivare audio">🔇 Avvio...</div>
<script>
var tag=document.createElement('script');
tag.src="https://www.youtube.com/iframe_api";
document.head.appendChild(tag);
var player,lastCmd="",vid="__VIDEO_ID__",muted=true;

document.getElementById('hud').addEventListener('click',function(){
  if(!player) return;
  if(muted){player.unMute();muted=false;}
  else{player.mute();muted=true;}
  updateHud(lastCmd);
});

function onYouTubeIframeAPIReady(){
  player=new YT.Player('player',{
    videoId:vid,
    playerVars:{autoplay:0,controls:1,rel:0,modestbranding:1,mute:1},
    events:{onReady:function(){poll()}}
  });
}
function poll(){
  fetch('/state').then(r=>r.json()).then(d=>{
    if(d.cmd!==lastCmd){
      lastCmd=d.cmd;
      if(d.cmd==='play'){player.playVideo();}
      else{player.pauseVideo();}
      updateHud(d.cmd);
    }
  }).catch(()=>{}).finally(()=>setTimeout(poll,600));
}
function updateHud(cmd){
  var icon = muted ? '🔇' : '🔊';
  document.getElementById('hud').textContent = cmd==='play'
    ? icon+' In riproduzione — clicca per '+(muted?'audio':'muto')
    : icon+' In pausa';
}
</script>
</body>
</html>
"""

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(p.query)

        if p.path == '/state':
            body = json.dumps(state).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)

        elif p.path in ('/', '/player'):
            vid = q.get('v', [''])[0]
            if vid:
                with lock:
                    state['video_id'] = vid
            html = PLAYER_HTML.replace('__VIDEO_ID__', state['video_id'])
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global play_locked_until
        p = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(p.query)

        if p.path == '/play':
            lock_secs = int(q.get('lock', ['0'])[0])
            with lock:
                state['cmd'] = 'play'
                if lock_secs > 0:
                    play_locked_until = time.time() + lock_secs
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')

        elif p.path == '/pause':
            with lock:
                if time.time() < play_locked_until:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'locked')
                    return
                state['cmd'] = 'pause'
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')

        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    vid = sys.argv[1] if len(sys.argv) > 1 else ''
    PORT = int(sys.argv[2]) if len(sys.argv) > 2 else PORT
    with lock:
        state['video_id'] = vid
    server = http.server.HTTPServer(('localhost', PORT), Handler)
    print(f'comeback · youtube ready → http://localhost:{PORT}/?v={vid}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
