"""
gen_preview.py — results.json 을 새 디자인(섹션·불릿)으로 정적 렌더해 preview.html 생성.
브라우저 캐시와 무관하게 새 레이아웃을 바로 확인하기 위한 파일.
"""
import json
import html
import label_format as lf

CSS = """
:root{--ink:#1a2330;--muted:#5b6b7d;--line:#e3e8ef;--accent:#1f6feb;--warn-bd:#f59e0b;--bg:#f6f8fb;}
*{box-sizing:border-box;} body{font-family:-apple-system,"Segoe UI","Malgun Gothic",sans-serif;
 color:var(--ink);background:var(--bg);margin:0;line-height:1.6;}
.wrap{max-width:860px;margin:0 auto;padding:32px 20px 64px;}
h1{font-size:1.6rem;margin:0 0 16px;}
section{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin-bottom:18px;}
h2{font-size:1.05rem;margin:0 0 14px;padding-left:10px;border-left:4px solid var(--accent);}
.kv{display:grid;grid-template-columns:96px 1fr;gap:7px 14px;font-size:.92rem;}
.kv dt{color:var(--muted);font-weight:600;} .kv dd{margin:0;}
.block{margin-top:16px;}
.block-h{font-size:.82rem;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.03em;margin-bottom:7px;}
.lead{font-size:.92rem;margin:0 0 6px;}
ul.clean{margin:0;padding-left:0;list-style:none;}
ul.clean li{position:relative;padding:5px 0 5px 20px;font-size:.9rem;border-bottom:1px dashed var(--line);}
ul.clean li:last-child{border-bottom:none;}
ul.clean li::before{content:"";position:absolute;left:4px;top:13px;width:6px;height:6px;border-radius:50%;background:var(--accent);}
.warn{background:#fff7ed;border:1px solid #fde6c0;border-left:4px solid var(--warn-bd);border-radius:8px;margin-top:16px;padding:6px 16px 12px;}
.warn-title{font-weight:700;color:#b45309;font-size:.86rem;padding-top:8px;}
.warn-item{padding:8px 0;border-top:1px solid #fde6c0;}
.warn-item:first-of-type{border-top:none;}
.warn-label{font-weight:700;color:#b45309;font-size:.85rem;}
.warn-text{font-size:.88rem;color:#5b4a2e;margin-top:2px;}
.paper{border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:12px;}
.paper h3{margin:0 0 6px;font-size:.98rem;}
.meta{font-size:.76rem;color:var(--muted);} a{color:var(--accent);text-decoration:none;}
"""


def esc(x):
    return html.escape(str(x or ""))


def main():
    d = json.load(open("results.json", encoding="utf-8"))
    f = d["fda"]
    ind = lf.format_indications(f.get("indications"))
    dose = lf.format_dosage(f.get("dosage"))
    warns = lf.format_warnings(f.get("warnings"))

    h = [f'<!doctype html><html lang="ko"><head><meta charset="utf-8">',
         f'<title>미리보기 — {esc(d["drug_resolved"])}</title><style>{CSS}</style></head><body><div class="wrap">',
         f'<h1>💊 약물 정보 — {esc(d["drug_resolved"])} <small style="font-size:.7rem;color:#5b6b7d">(정적 미리보기)</small></h1>',
         '<section><h2>허가 정보 (FDA)</h2>',
         '<dl class="kv">',
         f'<dt>일반명</dt><dd>{esc(", ".join(f.get("generic_name",[])))}</dd>',
         f'<dt>제품명</dt><dd>{esc(", ".join(f.get("brand_name",[])))}</dd>',
         f'<dt>투여경로</dt><dd>{esc(", ".join(f.get("route",[])))}</dd>',
         '</dl>']

    # 적응증
    h.append('<div class="block"><div class="block-h">적응증 (Indications)</div>')
    if ind["intro"]:
        h.append(f'<p class="lead">{esc(ind["intro"])}</p>')
    if ind["conditions"]:
        h.append('<ul class="clean">' + "".join(f"<li>{esc(c)}</li>" for c in ind["conditions"]) + "</ul>")
    h.append("</div>")

    # 용법용량
    h.append('<div class="block"><div class="block-h">용법·용량 (Dosage)</div><ul class="clean">')
    h.append("".join(f"<li>{esc(b)}</li>" for b in dose) + "</ul></div>")

    # 경고
    h.append('<div class="warn"><div class="warn-title">⚠ 주요 경고 (Warnings)</div>')
    for w in warns:
        if w["label"] and w["label"].lower() == "warnings":
            continue
        if not (w["text"] or w["label"]):
            continue
        h.append('<div class="warn-item">')
        if w["label"]:
            h.append(f'<span class="warn-label">{esc(w["label"])}</span>')
        if w["text"]:
            h.append(f'<div class="warn-text">{esc(w["text"])}</div>')
        h.append("</div>")
    h.append("</div></section>")

    # 논문
    h.append(f'<section><h2>최신 논문 ({len(d["pubmed"])}건)</h2>')
    for i, p in enumerate(d["pubmed"], 1):
        h.append(f'<div class="paper"><h3>{i}. {esc(p["title"])}</h3>'
                 f'<div class="meta">{esc(p["year"])} · {esc(p["journal"])} · '
                 f'<a href="{esc(p["url"])}" target="_blank">PMID {esc(p["pmid"])}</a></div></div>')
    h.append("</section></div></body></html>")

    with open("preview.html", "w", encoding="utf-8") as fp:
        fp.write("".join(h))
    print("[+] preview.html 생성 완료 — 더블클릭으로 열어보세요")


if __name__ == "__main__":
    main()
