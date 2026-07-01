"""
app.py — 약물 정보 검색 웹사이트 (로컬 서버).

약물명을 검색하면 PubMed 논문 + FDA 허가정보를 실시간으로 조회해
깔끔한 보고서 형태로 보여준다. 표준 라이브러리만 사용 — 설치 불필요.

실행:
    python app.py
    -> 브라우저에서 http://localhost:8000 접속

API:
    GET /api/search?drug=acetaminophen&max=8  -> JSON
"""

import json
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from drug_search import search_pubmed, search_fda, KO_TO_EN
import label_format as lf

PORT = 8080

INDEX_HTML = r"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>약물 정보 검색</title>
<style>
:root{--ink:#0f172a;--muted:#64748b;--line:#e8edf3;--accent:#2563eb;
      --accent2:#7c3aed;--chip:#eef4ff;--bg:#eef2f8;--card:#ffffff;
      --radius:16px;--shadow:0 1px 2px rgba(15,23,42,.04),0 8px 24px rgba(15,23,42,.06);}
*{box-sizing:border-box;}
body{font-family:-apple-system,"Segoe UI","Malgun Gothic",sans-serif;color:var(--ink);
     margin:0;background:radial-gradient(1200px 500px at 50% -120px,#dbe6ff 0%,var(--bg) 60%);
     line-height:1.65;-webkit-font-smoothing:antialiased;}
.wrap{max-width:880px;margin:0 auto;padding:40px 20px 72px;}
header h1{font-size:1.9rem;margin:0 0 6px;letter-spacing:-.02em;display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.badge{font-size:.66rem;font-weight:700;background:linear-gradient(135deg,#22c55e,#16a34a);
     color:#fff;padding:4px 10px;border-radius:999px;box-shadow:0 2px 6px rgba(22,163,74,.35);}
header p{color:var(--muted);margin:0 0 26px;font-size:.92rem;}
.searchbar{display:flex;gap:10px;margin-bottom:10px;background:var(--card);padding:8px;
     border-radius:14px;box-shadow:var(--shadow);}
.searchbar input{flex:1;padding:14px 16px;font-size:1.02rem;border:none;border-radius:10px;outline:none;background:transparent;}
.searchbar button{padding:0 26px;font-size:1rem;font-weight:700;color:#fff;cursor:pointer;
     background:linear-gradient(135deg,var(--accent),var(--accent2));border:none;border-radius:10px;
     transition:transform .08s,box-shadow .2s;box-shadow:0 4px 14px rgba(37,99,235,.35);}
.searchbar button:hover{transform:translateY(-1px);box-shadow:0 6px 18px rgba(37,99,235,.45);}
.searchbar button:disabled{opacity:.5;cursor:default;transform:none;}
.hint{color:var(--muted);font-size:.82rem;margin-bottom:28px;}
.hint b{color:var(--accent);cursor:pointer;border-bottom:1px dotted;}
#status{padding:18px 0;color:var(--muted);font-size:.95rem;}
section{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
     padding:24px 26px;margin-bottom:18px;box-shadow:var(--shadow);}
h2{font-size:1.12rem;margin:0 0 18px;display:flex;align-items:center;gap:9px;letter-spacing:-.01em;}
h2 .ic{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;font-size:1rem;
     background:linear-gradient(135deg,#e0ecff,#ede5ff);}
h2 .count{margin-left:auto;font-size:.72rem;font-weight:700;color:var(--accent);
     background:var(--chip);padding:3px 10px;border-radius:999px;}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:4px;}
.kv .cell{background:#f8fafc;border:1px solid var(--line);border-radius:11px;padding:11px 14px;}
.kv .k{font-size:.7rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
.kv .v{font-size:.95rem;font-weight:600;margin-top:2px;}
.block{margin-top:22px;}
.block-h{font-size:.74rem;font-weight:800;color:var(--muted);text-transform:uppercase;
     letter-spacing:.06em;margin-bottom:10px;display:flex;align-items:center;gap:7px;}
.lead{font-size:.96rem;font-weight:600;margin:0 0 12px;color:#1e293b;}
/* 적응증 칩 */
.chips{display:flex;flex-wrap:wrap;gap:8px;}
.tag{background:linear-gradient(135deg,#eff6ff,#f5f3ff);color:#1d4ed8;border:1px solid #dbe4ff;
     border-radius:999px;padding:7px 14px;font-size:.86rem;font-weight:600;}
/* 용법용량 표 */
.dose{display:grid;gap:10px;}
.dose-row{display:grid;grid-template-columns:auto 1fr;gap:14px;align-items:start;
     background:#f8fafc;border:1px solid var(--line);border-radius:12px;padding:13px 16px;}
.dose-ic{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;font-size:1.05rem;
     background:#e0ecff;}
.dose-k{font-weight:700;font-size:.9rem;}
.dose-v{font-size:.9rem;color:#475569;margin-top:2px;}
/* 주의사항 위험도 카드 */
.warns{display:grid;gap:12px;}
.wcard{display:grid;grid-template-columns:auto 1fr;gap:14px;border-radius:13px;padding:15px 17px;
     border:1px solid;align-items:start;}
.wcard .wic{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;font-size:1.1rem;flex:none;}
.wlabel{font-weight:800;font-size:.92rem;letter-spacing:-.01em;}
.wsev{font-size:.66rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;
     padding:2px 8px;border-radius:999px;margin-left:8px;vertical-align:middle;}
.wbody{margin:8px 0 0;padding:0;list-style:none;}
.wbody li{position:relative;padding:4px 0 4px 16px;font-size:.88rem;color:#334155;}
.wbody li::before{content:"";position:absolute;left:2px;top:12px;width:5px;height:5px;border-radius:50%;background:currentColor;opacity:.5;}
.wbody.single{padding-left:0;} .wbody.single li{padding-left:0;} .wbody.single li::before{display:none;}
/* 위험도 색상 */
.sev-critical{background:#fef2f2;border-color:#fecaca;} .sev-critical .wic{background:#fee2e2;}
.sev-critical .wlabel{color:#b91c1c;} .sev-critical .wsev{background:#fee2e2;color:#b91c1c;}
.sev-stop{background:#fff7ed;border-color:#fed7aa;} .sev-stop .wic{background:#ffedd5;}
.sev-stop .wlabel{color:#c2410c;} .sev-stop .wsev{background:#ffedd5;color:#c2410c;}
.sev-caution{background:#fefce8;border-color:#fde68a;} .sev-caution .wic{background:#fef3c7;}
.sev-caution .wlabel{color:#a16207;} .sev-caution .wsev{background:#fef3c7;color:#a16207;}
.sev-info{background:#f0f9ff;border-color:#bae6fd;} .sev-info .wic{background:#e0f2fe;}
.sev-info .wlabel{color:#0369a1;} .sev-info .wsev{background:#e0f2fe;color:#0369a1;}
/* 논문 */
.paper{border:1px solid var(--line);border-radius:13px;padding:16px 18px;margin-bottom:12px;
     transition:border-color .15s,box-shadow .15s;}
.paper:hover{border-color:#c7d6f0;box-shadow:0 4px 14px rgba(37,99,235,.08);}
.paper h3{margin:0 0 8px;font-size:1rem;line-height:1.45;}
.meta{font-size:.78rem;color:var(--muted);margin-bottom:9px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.chip{display:inline-block;background:var(--chip);color:var(--accent);border-radius:999px;
     padding:3px 11px;font-size:.72rem;font-weight:700;}
.abs{font-size:.88rem;color:#475569;}
.abs.clamp{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;}
.toggle{color:var(--accent);font-size:.8rem;cursor:pointer;margin-top:6px;display:inline-block;font-weight:600;}
a{color:var(--accent);text-decoration:none;}
.empty{color:var(--muted);font-style:italic;}
footer{color:var(--muted);font-size:.78rem;text-align:center;margin-top:32px;}
</style></head>
<body>
<div class="wrap">
  <header>
    <h1>💊 약물 정보 검색 <span class="badge">디자인 v4 · 카드형</span></h1>
    <p>약물명을 검색하면 PubMed 최신 논문과 FDA 허가정보를 한눈에 정리합니다.</p>
  </header>

  <div class="searchbar">
    <input id="q" placeholder="약물명 입력 (영문 일반명 권장, 예: acetaminophen)" autofocus>
    <button id="go">검색</button>
  </div>
  <div class="hint">예시:
    <b onclick="ex('acetaminophen')">acetaminophen</b> ·
    <b onclick="ex('inclisiran')">inclisiran</b> ·
    <b onclick="ex('aspirin')">aspirin</b>
    &nbsp;|&nbsp; 한글 일부 지원: <b onclick="ex('타이레놀')">타이레놀</b>
  </div>

  <div id="status"></div>
  <div id="out"></div>

  <footer>데이터 소스: PubMed (E-utilities) · openFDA &nbsp;|&nbsp;
    임상 의사결정 대체 아님 — 원문 확인 권장</footer>
</div>

<script>
const $ = s => document.querySelector(s);
function ex(name){ $('#q').value = name; search(); }
function esc(s){ const d=document.createElement('div'); d.textContent=s==null?'':s; return d.innerHTML; }

async function search(){
  const drug = $('#q').value.trim();
  if(!drug) return;
  $('#go').disabled = true;
  $('#status').textContent = '🔎 검색 중... (PubMed + FDA 조회)';
  $('#out').innerHTML = '';
  try{
    const bust = '&_=' + Date.now();  // 캐시 무력화
    const r = await fetch('/api/search?drug=' + encodeURIComponent(drug) + '&max=8' + bust, {cache:'no-store'});
    const data = await r.json();
    if(data.error){ $('#status').textContent = '⚠️ ' + data.error; return; }
    render(data);
    $('#status').textContent = '';
  }catch(e){
    $('#status').textContent = '⚠️ 오류: ' + e.message;
  }finally{
    $('#go').disabled = false;
  }
}

// 경고 라벨 -> 위험도 분류 (색/아이콘/표시)
function classifyWarning(label){
  const l = (label||'').toLowerCase();
  if(/liver|stomach bleeding|allergy|reye|caffeine/.test(l))
    return {sev:'sev-critical', ic:'🛑', tag:'주의 경고'};
  if(/do not use|overdose|keep out of reach|pregnant|breast/.test(l))
    return {sev:'sev-stop', ic:'⛔', tag:'금기/안전'};
  if(/stop use/.test(l))
    return {sev:'sev-stop', ic:'✋', tag:'복용 중단'};
  if(/ask a doctor|when using/.test(l))
    return {sev:'sev-info', ic:'🩺', tag:'상담 권고'};
  return {sev:'sev-caution', ic:'⚠️', tag:'주의'};
}
function splitSentences(t){
  return (t||'').split(/(?<=[.!?])\s+/).map(s=>s.trim()).filter(Boolean);
}

function render(d){
  let h = '';
  const f = d.fda || {};

  // ===== 허가 정보 (FDA) =====
  h += '<section><h2><span class="ic">📋</span> 허가 정보 <span style="color:var(--muted);font-weight:600;font-size:.8rem">FDA</span></h2>';
  if(f.found){
    // 기본 정보 카드 그리드
    h += '<div class="kv">';
    h += '<div class="cell"><div class="k">일반명</div><div class="v">' + esc((f.generic_name||[]).join(', ')) + '</div></div>';
    if((f.brand_name||[]).length) h += '<div class="cell"><div class="k">제품명</div><div class="v">' + esc(f.brand_name.join(', ')) + '</div></div>';
    if((f.route||[]).length) h += '<div class="cell"><div class="k">투여경로</div><div class="v">' + esc(f.route.join(', ')) + '</div></div>';
    h += '</div>';

    // 적응증 — 칩
    const ind = f.indications_fmt;
    if(ind && (ind.intro || (ind.conditions||[]).length)){
      h += '<div class="block"><div class="block-h">🎯 적응증 (Indications)</div>';
      if(ind.intro) h += '<p class="lead">' + esc(ind.intro) + '</p>';
      if((ind.conditions||[]).length){
        h += '<div class="chips">';
        ind.conditions.forEach(c => h += '<span class="tag">' + esc(c) + '</span>');
        h += '</div>';
      }
      h += '</div>';
    }

    // 용법·용량 — 아이콘 행 카드
    const dose = f.dosage_fmt || [];
    if(dose.length){
      const icons = ['📌','🧑‍🤝‍🧑','📅','👶','💬','💊'];
      h += '<div class="block"><div class="block-h">💊 용법·용량 (Dosage)</div><div class="dose">';
      dose.forEach((b,i) => {
        const parts = b.split(' — ');
        const k = parts.length>1 ? parts[0] : '';
        const v = parts.length>1 ? parts.slice(1).join(' — ') : b;
        h += '<div class="dose-row"><div class="dose-ic">' + icons[i%icons.length] + '</div>'
           + '<div>' + (k ? '<div class="dose-k">' + esc(k) + '</div>' : '')
           + '<div class="dose-v">' + esc(v) + '</div></div></div>';
      });
      h += '</div></div>';
    }

    // 주요 경고 — 위험도별 색상 카드
    const warns = (f.warnings_fmt || []).filter(w => (w.text || w.label) && !(w.label && w.label.toLowerCase()==='warnings'));
    if(warns.length){
      h += '<div class="block"><div class="block-h">⚠️ 주요 경고 (Warnings)</div><div class="warns">';
      warns.forEach(w => {
        const c = classifyWarning(w.label);
        const sents = splitSentences(w.text);
        h += '<div class="wcard ' + c.sev + '"><div class="wic">' + c.ic + '</div><div>';
        if(w.label) h += '<span class="wlabel">' + esc(w.label) + '</span><span class="wsev">' + c.tag + '</span>';
        if(sents.length){
          const cls = sents.length>1 ? 'wbody' : 'wbody single';
          h += '<ul class="' + cls + '">' + sents.map(s=>'<li>'+esc(s)+'</li>').join('') + '</ul>';
        }
        h += '</div></div>';
      });
      h += '</div></div>';
    }
  }else{
    h += '<p class="empty">FDA 허가정보를 찾지 못했습니다 (영문 일반명으로 시도해 보세요).</p>';
  }
  h += '</section>';

  // ===== 최신 논문 =====
  const ps = d.pubmed || [];
  h += '<section><h2><span class="ic">📚</span> 최신 논문 <span class="count">' + ps.length + '건</span></h2>';
  if(ps.length){
    ps.forEach((p,i) => {
      h += '<div class="paper">';
      h += '<h3>' + (i+1) + '. ' + esc(p.title) + '</h3>';
      h += '<div class="meta"><span class="chip">' + esc(p.year) + '</span>' + esc(p.journal);
      if(p.pmid) h += ' · <a href="' + esc(p.url) + '" target="_blank">PMID ' + esc(p.pmid) + ' ↗</a>';
      h += '</div>';
      const id = 'abs'+i;
      h += '<div class="abs clamp" id="'+id+'">' + esc(p.abstract) + '</div>';
      if((p.abstract||'').length > 180)
        h += '<span class="toggle" onclick="document.getElementById(\''+id+'\').classList.toggle(\'clamp\')">▼ 초록 펼치기/접기</span>';
      h += '</div>';
    });
  }else{
    h += '<p class="empty">관련 논문을 찾지 못했습니다.</p>';
  }
  h += '</section>';

  $('#out').innerHTML = h;
}

$('#go').addEventListener('click', search);
$('#q').addEventListener('keydown', e => { if(e.key==='Enter') search(); });
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML, "text/html")
            return
        if parsed.path == "/api/search":
            qs = urllib.parse.parse_qs(parsed.query)
            drug_in = (qs.get("drug", [""])[0]).strip()
            max_n = int(qs.get("max", ["8"])[0])
            if not drug_in:
                self._send(400, json.dumps({"error": "약물명이 비어 있습니다."}), "application/json")
                return
            drug = KO_TO_EN.get(drug_in, drug_in)
            try:
                papers = search_pubmed(drug, max_n, sort="date")
                fda = search_fda(drug)
                # 줄글 라벨을 읽기 좋은 구조로 변환
                if fda.get("found"):
                    fda["indications_fmt"] = lf.format_indications(fda.get("indications"))
                    fda["dosage_fmt"] = lf.format_dosage(fda.get("dosage"))
                    fda["warnings_fmt"] = lf.format_warnings(fda.get("warnings"))
                result = {"drug_query": drug_in, "drug_resolved": drug,
                          "pubmed": papers, "fda": fda}
                self._send(200, json.dumps(result, ensure_ascii=False), "application/json")
            except Exception as e:  # 네트워크/파싱 오류 등
                self._send(200, json.dumps({"error": f"검색 실패: {e}"}, ensure_ascii=False),
                           "application/json")
            return
        self._send(404, json.dumps({"error": "not found"}), "application/json")

    def log_message(self, *args):  # 콘솔 로그 간소화
        pass


def _get_lan_ip():
    """같은 와이파이의 폰에서 접속할 PC의 내부 IP를 알아낸다."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # 실제 전송은 안 함, 라우팅용 IP만 확인
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    # 0.0.0.0 = 같은 네트워크(와이파이)의 다른 기기도 접속 허용
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    lan_ip = _get_lan_ip()
    print(f"[+] 약물 정보 검색 사이트 실행 중")
    print(f"    이 PC에서:  http://localhost:{PORT}")
    print(f"    폰/태블릿:  http://{lan_ip}:{PORT}   (같은 와이파이 필수)")
    print("    (종료: Ctrl+C)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] 종료")
        server.shutdown()


if __name__ == "__main__":
    main()
