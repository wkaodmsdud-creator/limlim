"""
label_format.py — FDA 라벨의 줄글 텍스트를 읽기 좋게 구조화한다.

openFDA 라벨 필드(적응증/용법용량/경고)는 구분자 없이 한 덩어리로 오는데,
OTC Drug Facts 의 표준 표제어(headers)를 기준으로 섹션·불릿으로 쪼갠다.
표준 라이브러리만 사용.
"""

import re

# 경고(warnings) 표준 표제어 — 이 문구들을 섹션 경계로 본다.
WARNING_HEADERS = [
    "Liver warning", "Allergy alert", "Sore throat warning", "Stomach bleeding warning",
    "Caffeine warning", "Reye's syndrome",
    "Do not use", "Ask a doctor before use if you have", "Ask a doctor before use if",
    "Ask a doctor or pharmacist before use if", "When using this product",
    "Stop use and ask a doctor if", "Stop use and ask a doctor or pharmacist if",
    "If pregnant or breast-feeding", "Keep out of reach of children",
    "In case of overdose", "Overdose warning",
]

# 용법·용량(directions) 표준 표제어 — 각 항목을 불릿으로 본다.
DOSAGE_HEADERS = [
    "do not take more than directed", "adults and children 12 years and over",
    "adults and children", "children under 12 years", "children under",
    "do not take for more than", "do not use more than directed",
    "do not exceed", "ask a doctor",
]


def _split_by_headers(text: str, headers: list[str]) -> list[dict]:
    """표제어 위치에서 텍스트를 잘라 [{'label':..., 'text':...}] 로 반환."""
    if not text:
        return []
    text = re.sub(r"\s+", " ", text).strip()
    # 표제어 후보를 위치순으로 모은다 (긴 표제어 우선 매칭).
    spots = []
    for h in headers:
        for m in re.finditer(re.escape(h), text, flags=re.IGNORECASE):
            spots.append((m.start(), m.end(), text[m.start():m.end()]))
    # 시작 위치 오름차순, 같은 위치면 긴 표제어 우선
    spots.sort(key=lambda x: (x[0], -x[1]))
    # 겹치는(앞선 표제어에 포함되는) 매칭 제거
    cleaned = []
    last_end = -1
    for s, e, lab in spots:
        if s >= last_end:
            cleaned.append((s, e, lab))
            last_end = e
    if not cleaned:
        return [{"label": None, "text": text}]

    sections = []
    pre = text[:cleaned[0][0]].strip()
    if pre:
        sections.append({"label": None, "text": pre})
    for i, (s, e, lab) in enumerate(cleaned):
        end = cleaned[i + 1][0] if i + 1 < len(cleaned) else len(text)
        body = text[e:end].strip(" :.-").strip()
        sections.append({"label": lab, "text": body})
    return sections


def format_warnings(text: str) -> list[dict]:
    """경고를 표제어별 섹션 리스트로. 의미 없는 'Warnings' 머리말은 제거."""
    secs = _split_by_headers(text, WARNING_HEADERS)
    return [s for s in secs
            if not (s["label"] is None and s["text"].strip().lower() in ("", "warnings"))]


def format_dosage(text: str) -> list[str]:
    """용법·용량을 불릿 문자열 리스트로."""
    text = re.sub(r"\s+", " ", text or "").strip()
    # 앞머리 'Directions' 제거
    text = re.sub(r"^Directions\b[:\s]*", "", text, flags=re.IGNORECASE)
    secs = _split_by_headers(text, DOSAGE_HEADERS)
    bullets = []
    for s in secs:
        line = (f"{s['label']} — {s['text']}" if s["label"] else s["text"]).strip(" —")
        if line:
            bullets.append(line)
    return bullets or ([text] if text else [])


def format_indications(text: str) -> dict:
    """적응증을 {intro, conditions[]} 로. 'due to:' 뒤 목록을 분리 시도."""
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"^(Uses|Indications and usage|Indications)\b[:\s]*", "", text,
                  flags=re.IGNORECASE).strip()
    if not text:
        return {"intro": "", "conditions": []}

    m = re.search(r"\bdue to:?\b", text, flags=re.IGNORECASE)
    if not m:
        # 문장 단위로 분리
        parts = [p.strip() for p in re.split(r"(?<=[.;])\s+", text) if p.strip()]
        return {"intro": parts[0] if parts else text,
                "conditions": parts[1:] if len(parts) > 1 else []}

    intro = text[:m.start()].strip().rstrip(",")
    rest = text[m.end():].strip(" :.-").strip()
    # 'temporarily reduces fever' 같은 별도 효능 문구 분리
    tail = ""
    tm = re.search(r"\btemporarily reduces?\b.*$", rest, flags=re.IGNORECASE)
    if tm:
        tail = rest[tm.start():].strip()
        rest = rest[:tm.start()].strip()
    # 남은 목록은 구분자가 없어 한 줄로 둔다(과분할 방지).
    conditions = [c for c in [rest, tail] if c]
    return {"intro": intro, "conditions": conditions}
