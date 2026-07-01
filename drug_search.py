"""
drug_search.py — 약물명으로 PubMed 논문 + FDA 허가정보를 수집한다.

역할: 검색·수집만 담당하고 결과를 results.json 으로 저장한다.
요약/보고서 생성은 Claude Code 가 results.json 을 읽어서 처리한다.

표준 라이브러리(urllib)만 사용 — 별도 설치 불필요.

사용법:
    python drug_search.py acetaminophen
    python drug_search.py "inclisiran" --max 5
"""

import sys
import json
import argparse
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OPENFDA_LABEL = "https://api.fda.gov/drug/label.json"

# PubMed/FDA 는 영문 일반명 기준이라 자주 쓰는 한글명만 간단 매핑.
KO_TO_EN = {
    "아세트아미노펜": "acetaminophen",
    "타이레놀": "acetaminophen",
    "레크비오": "inclisiran",
    "아스피린": "aspirin",
}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "mini-project/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def search_pubmed(drug: str, max_results: int = 5, sort: str = "date") -> list[dict]:
    """esearch 로 PMID 목록을, efetch 로 초록을 가져온다.

    sort="date" 면 최신순(보고서용), "relevance" 면 관련도순(의학정보 응답용).
    """
    # 1) PMID 검색
    q = urllib.parse.urlencode({
        "db": "pubmed",
        "term": drug,
        "retmax": max_results,
        "sort": sort,
        "retmode": "json",
    })
    search = json.loads(_get(f"{PUBMED_BASE}/esearch.fcgi?{q}"))
    pmids = search.get("esearchresult", {}).get("idlist", [])
    if not pmids:
        return []

    # 2) 초록 본문 fetch (XML)
    q2 = urllib.parse.urlencode({
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    })
    xml_raw = _get(f"{PUBMED_BASE}/efetch.fcgi?{q2}")
    root = ET.fromstring(xml_raw)

    papers = []
    for art in root.findall(".//PubmedArticle"):
        title = art.findtext(".//ArticleTitle") or "(제목 없음)"
        abstract = " ".join(
            (node.text or "") for node in art.findall(".//Abstract/AbstractText")
        ).strip()
        year = art.findtext(".//PubDate/Year") or art.findtext(".//PubDate/MedlineDate") or "?"
        journal = art.findtext(".//Journal/Title") or ""
        pmid = art.findtext(".//PMID") or ""
        papers.append({
            "pmid": pmid,
            "title": title,
            "journal": journal,
            "year": year,
            "abstract": abstract or "(초록 없음)",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return papers


def search_fda(drug: str) -> dict:
    """openFDA drug/label 에서 허가/라벨 핵심 필드를 가져온다."""
    q = urllib.parse.urlencode({
        "search": f"openfda.generic_name:{drug}",
        "limit": 1,
    })
    try:
        data = json.loads(_get(f"{OPENFDA_LABEL}?{q}"))
    except urllib.error.HTTPError:
        return {"found": False}

    results = data.get("results", [])
    if not results:
        return {"found": False}

    r = results[0]
    openfda = r.get("openfda", {})

    def first(field):
        v = r.get(field)
        return v[0].strip() if isinstance(v, list) and v else None

    return {
        "found": True,
        "brand_name": openfda.get("brand_name", []),
        "generic_name": openfda.get("generic_name", []),
        "manufacturer": openfda.get("manufacturer_name", []),
        "route": openfda.get("route", []),
        "indications": first("indications_and_usage"),
        "dosage": first("dosage_and_administration"),
        "warnings": first("warnings") or first("warnings_and_cautions"),
        "adverse_reactions": first("adverse_reactions"),
    }


def main():
    ap = argparse.ArgumentParser(description="약물 정보 수집기 (PubMed + FDA)")
    ap.add_argument("drug", help="약물명 (영문 일반명 권장, 일부 한글명 지원)")
    ap.add_argument("--max", type=int, default=5, help="PubMed 논문 최대 건수 (기본 5)")
    ap.add_argument("--out", default="results.json", help="결과 저장 파일")
    args = ap.parse_args()

    drug = KO_TO_EN.get(args.drug.strip(), args.drug.strip())
    print(f"[*] 검색 약물: {drug}")

    print("[*] PubMed 검색 중...")
    papers = search_pubmed(drug, args.max)
    print(f"    -> 논문 {len(papers)}건 수집")

    print("[*] openFDA 검색 중...")
    fda = search_fda(drug)
    print(f"    -> 허가정보 {'있음' if fda.get('found') else '없음'}")

    out = {"drug_query": args.drug, "drug_resolved": drug, "pubmed": papers, "fda": fda}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[+] 저장 완료: {args.out}")


if __name__ == "__main__":
    main()
