"""
med_info.py — 의학정보(Medical Information) 응답 지원: HCP 질문 -> 근거 검색.

흐름:
  1) HCP 질문 + 약물명 입력
  2) 질문에서 핵심어 추출 -> 약물 AND 핵심어 로 PubMed 관련도 검색
  3) FDA 라벨 동시 조회 (허가 근거 확인용)
  4) mi_results.json 저장

요약/답변 초안 생성은 Claude Code 가 mi_results.json 을 읽어서 처리한다
(균형성·출처 추적·비판촉진 톤은 Claude 단계의 책임).

표준 라이브러리만 사용 — 설치 불필요.

사용법:
    python med_info.py --drug acetaminophen "임신 중 아세트아미노펜 복용이 안전한가요?"
    python med_info.py --drug acetaminophen --max 6 "Is acetaminophen safe in pregnancy?"
"""

import json
import re
import argparse

from drug_search import search_pubmed, search_fda, KO_TO_EN

# 검색어에서 빼는 불용어(한/영) — 질문 잡음 제거용.
STOPWORDS = {
    # 영어
    "is", "are", "the", "a", "an", "of", "in", "on", "for", "to", "and", "or",
    "with", "what", "how", "does", "do", "can", "should", "safe", "use", "using",
    "during", "about", "any", "there", "this", "that", "it", "be", "drug",
    # 한국어 조사/흔한 어미 (간단 처리)
    "이", "가", "은", "는", "을", "를", "의", "에", "에서", "에게", "와", "과",
    "복용", "사용", "안전한가요", "안전한가", "안전", "관련", "대한", "있나요",
    "있는지", "어떤가요", "무엇인가요", "알려줘", "알려주세요", "주세요",
}


def extract_keywords(question: str, drug: str) -> list[str]:
    """질문에서 약물명·불용어를 제외한 핵심 단어를 뽑는다."""
    tokens = re.findall(r"[A-Za-z가-힣]+", question)
    drug_words = set(drug.lower().split())
    kws = []
    for t in tokens:
        low = t.lower()
        if low in drug_words or low in STOPWORDS or len(t) < 2:
            continue
        if t not in kws:
            kws.append(t)
    return kws


def build_query(drug: str, keywords: list[str]) -> str:
    """drug AND (kw1 OR kw2 ...) 형태의 PubMed 질의."""
    if not keywords:
        return drug
    ors = " OR ".join(keywords)
    return f"{drug} AND ({ors})"


def main():
    ap = argparse.ArgumentParser(description="의학정보 Q&A 근거 검색 (PubMed + FDA)")
    ap.add_argument("question", help="HCP 질문 (자연어)")
    ap.add_argument("--drug", required=True, help="약물명 (영문 일반명 권장)")
    ap.add_argument("--max", type=int, default=6, help="PubMed 근거 최대 건수")
    ap.add_argument("--out", default="mi_results.json")
    args = ap.parse_args()

    drug = KO_TO_EN.get(args.drug.strip(), args.drug.strip())
    keywords = extract_keywords(args.question, drug)
    query = build_query(drug, keywords)

    print(f"[*] 약물: {drug}")
    print(f"[*] 추출 핵심어: {keywords or '(없음 → 약물 단독 검색)'}")
    print(f"[*] PubMed 질의: {query}")

    print("[*] PubMed 관련도 검색 중...")
    papers = search_pubmed(query, args.max, sort="relevance")
    print(f"    -> 근거 {len(papers)}건")

    print("[*] openFDA 라벨 조회 중...")
    fda = search_fda(drug)
    print(f"    -> 허가정보 {'있음' if fda.get('found') else '없음'}")

    out = {
        "question": args.question,
        "drug_query": args.drug,
        "drug_resolved": drug,
        "keywords": keywords,
        "pubmed_query": query,
        "evidence": papers,
        "fda": fda,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[+] 저장: {args.out}  (이제 Claude Code 가 답변 초안을 생성)")


if __name__ == "__main__":
    main()
