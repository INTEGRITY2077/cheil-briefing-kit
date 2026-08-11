# -*- coding: utf-8 -*-
"""화두판 HTML에 라디오(오디오+대본)를 이식한다.

사용: python tools/embed_radio.py <화두판.html> <오디오.wav|mp3> <대본.md>

- 오디오: HTML 안의 유일한 data:audio 데이터 URI를 새 파일의 base64로 교체한다.
  (플레이어 JS가 data:→blob: 전환을 수행해 ⋮ 메뉴에 다운로드가 생긴다 — HTML쪽 코드 유지 필수)
- 대본: <summary>대본</summary> ... </details> 사이를 대본 md의 A:/B: 줄로 재구성한다.
- 실패 시 원본을 건드리지 않는다 (전부 검증 후 한 번에 쓴다).

2026-08-12 수작업 이식을 도구화한 것. 매일 루틴 4절에서 호출한다.
"""
import base64, io, os, re, sys

def main():
    html_p, wav_p, scr_p = sys.argv[1], sys.argv[2], sys.argv[3]
    html = io.open(html_p, encoding="utf-8").read()

    mime = "audio/wav" if wav_p.lower().endswith(".wav") else "audio/mpeg"
    b64 = base64.b64encode(open(wav_p, "rb").read()).decode()

    n = len(re.findall(r'data:audio/[^;]+;base64,[A-Za-z0-9+/=]+', html))
    if n != 1:
        sys.exit(f"중단: data:audio 데이터 URI가 {n}개다 (1개여야 한다)")
    html = re.sub(r'data:audio/[^;]+;base64,[A-Za-z0-9+/=]+',
                  f'data:{mime};base64,' + b64, html, count=1)

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
