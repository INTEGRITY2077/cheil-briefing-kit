# -*- coding: utf-8 -*-
"""웹판 HTML에 라디오(오디오+대본)를 이식한다.

사용: python tools/embed_radio.py <웹판.html> <오디오.wav|mp3> <대본.md>

- HTML에 플레이어 블록(data:audio URI + 대본 details)이 이미 있으면 교체하고,
  **없으면 <body> 직후에 플레이어 블록을 새로 삽입한다** (뼈대 HTML도 그대로 사용 가능).
- 플레이어 JS: data:→blob: 전환(⋮ 메뉴 다운로드 활성), 배속 −/+ 버튼(1.0~2.0).
- 대본: <summary>대본</summary> ... </details> 사이를 대본 md의 A:/B: 줄로 재구성한다.
- 실패 시 원본을 건드리지 않는다 (전부 검증 후 한 번에 쓴다).
"""
import base64, io, os, re, sys

USAGE = "사용법: python tools/embed_radio.py <웹판.html> <오디오.wav|mp3> <대본.md>"

PLAYER_CSS = """
<style>
.kit-radio{border:1px solid #d6d3ca;padding:14px 18px;margin:14px 0;display:flex;flex-direction:column;gap:9px;font-family:system-ui,sans-serif}
.kit-radio audio{width:100%}
.kit-radio details{border-top:1px solid #e2e0d8;padding-top:8px}
.kit-radio summary{cursor:pointer;font-size:13px}
.kit-radio .spd{display:flex;align-items:center;gap:10px;font-size:11px}
.kit-radio .spd button{width:34px;height:30px;border:1px solid #b9b5a8;background:none;font-size:16px;cursor:pointer}
.kit-radio .spd b{font-size:12px;font-weight:400;min-width:38px;text-align:center}
.kit-radio .rl{display:grid;grid-template-columns:40px 1fr;gap:11px;padding:8px 0;border-bottom:1px solid #eceae2}
.kit-radio .rl:last-child{border-bottom:none}
.kit-radio .rl i{font-style:normal;font-size:10px;padding-top:4px;color:#8a877d}
.kit-radio .rl p{margin:0;font-size:14px;line-height:1.6}
</style>
"""

PLAYER_HTML = """<div class="kit-radio">
  <audio id="radioA" controls preload="none" src="data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="></audio>
  <div class="spd"><span>배속</span><button type="button" id="spdDn">−</button><b id="spdV">1.0×</b><button type="button" id="spdUp">+</button></div>
  <details><summary>대본</summary>
  </details>
</div>
<script>
(function(){
  var a=document.getElementById('radioA'),v=document.getElementById('spdV');
  var dn=document.getElementById('spdDn'),up=document.getElementById('spdUp');
  if(!a||!v)return;
  var spd=1.3;
  function apply(){a.playbackRate=spd;v.textContent=spd.toFixed(1)+'\\u00d7';}
  function step(d){spd=Math.min(2,Math.max(1,Math.round((spd+d)*10)/10));apply();}
  var srcU=a.getAttribute('src');
  function swap(b){var t=a.currentTime,p=!a.paused;a.src=URL.createObjectURL(b);a.currentTime=t;if(p)a.play();apply();}
  function viaAtob(){
    try{
      var m=srcU.match(/^data:([^;,]+)(;base64)?,([\\s\\S]*)$/);
      if(m&&m[2]){
        var bin=atob(m[3].replace(/\\s+/g,'')),n=bin.length,u8=new Uint8Array(n);
        for(var i=0;i<n;i++)u8[i]=bin.charCodeAt(i);
        swap(new Blob([u8],{type:m[1]}));
      }
    }catch(e){}
  }
  try{fetch(srcU).then(function(r){return r.blob()}).then(swap).catch(viaAtob);}catch(e){viaAtob();}
  if(dn)dn.addEventListener('click',function(){step(-0.1)});
  if(up)up.addEventListener('click',function(){step(0.1)});
  a.addEventListener('play',apply);
  apply();
})();
</script>
"""

def main():
    if len(sys.argv) < 4:
        sys.exit(USAGE)
    html_p, wav_p, scr_p = sys.argv[1], sys.argv[2], sys.argv[3]
    for f in (html_p, wav_p, scr_p):
        if not os.path.exists(f):
            sys.exit(f"파일 없음: {f}\n{USAGE}")
    html = io.open(html_p, encoding="utf-8").read()

    # 0) 플레이어 블록이 없으면 <body> 직후에 삽입한다
    n = len(re.findall(r'data:audio/[^;]+;base64,[A-Za-z0-9+/=]+', html))
    if n == 0:
        m = re.search(r'<body[^>]*>', html)
        block = PLAYER_CSS + PLAYER_HTML
        if m:
            html = html[:m.end()] + "\n" + block + html[m.end():]
        else:
            html = block + html
        n = 1
        print("플레이어 블록이 없어 새로 삽입했다")
    if n != 1:
        sys.exit(f"중단: data:audio 데이터 URI가 {n}개다 (1개여야 한다)")

    # 1) 오디오 교체
    mime = "audio/wav" if wav_p.lower().endswith(".wav") else "audio/mpeg"
    b64 = base64.b64encode(open(wav_p, "rb").read()).decode()
    html = re.sub(r'data:audio/[^;]+;base64,[A-Za-z0-9+/=]+',
                  f'data:{mime};base64,' + b64, html, count=1)

    # 2) 대본 교체
    lines = []
    for raw in io.open(scr_p, encoding="utf-8"):
        m = re.match(r'^([AB]):\s*(.+)$', raw.strip())
        if m:
            cls, who = ('ra', '앵커') if m.group(1) == 'A' else ('rb', '기자')
            lines.append(f'<div class="rl {cls}"><i>{who}</i><p>{m.group(2)}</p></div>')
    if not lines:
        sys.exit("중단: 대본에 A:/B: 줄이 없다")
    pat = re.compile(r'(<summary>대본</summary>).*?(</details>)', re.S)
    if not pat.search(html):
        sys.exit("중단: HTML에서 대본 블록을 못 찾았다")
    html = pat.sub(lambda m: m.group(1) + '\n' + '\n'.join(lines) + '\n  ' + m.group(2), html, count=1)

    io.open(html_p, "w", encoding="utf-8").write(html)
    print(f"완료: {os.path.basename(html_p)} ← {os.path.basename(wav_p)} ({len(b64)//1024}KB b64), 대사 {len(lines)}줄")

if __name__ == "__main__":
    main()
