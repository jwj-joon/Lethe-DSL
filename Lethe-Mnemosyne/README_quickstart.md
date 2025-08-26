
# Lethe+ (Minimal v2) — 초간단 사용법

이 번들은 **DSL 없이도 읽히는 규칙 문장**을 그대로 사용하면서,
다음 기능을 추가합니다: `expire`(TTL), `pin`, `reinforce cap/cooldown`, `shield`, `TF-IDF 검색`, `why 설명`, `trust 기반 forget`.

## 0) 파일 구성
- `lethe_min_v2.py` — 엔진 (단일 파일)
- `example_v3.lethe` — 새 DSL 예제
- 출력: `lethe_before.csv`, `lethe_after.csv`, `lethe_audit.csv`

## 1) 규칙(Dsl) 수정
`example_v3.lethe`를 열어 규칙을 한국어 주석 따라 바로 수정하세요.

### 문법 요약
- 만료(TTL): `expire topic|tag|keyword:"..." after:30d action:shield|remove`
- 고정(Pin): `pin topic|tag:"..." priority:1.0` (검색 점수 가산)
- 강화(Reinforce): `rule on event == "EVENT" -> reinforce topic|tag:"..." by 0.2 cap:0.8 cooldown:24h`
- 신뢰도 기반: `rule on trust < 0.4 -> forget topic|tag:"..."`
- 검색 설정 블록:
  ```
  retrieval {
    topk:7
    synonyms alias=["a","b","c"]
  }
  ```

## 2) 실행 예시
```bash
# 규칙 적용 & 감사 로그 생성 (이벤트가 있을 때)
python lethe_min_v2.py run --mem memories.json --ctx context.json --dsl example_v3.lethe --event milestone   --audit lethe_audit.csv --before lethe_before.csv --after lethe_after.csv

# 검색 (설정된 synonyms를 포함해 TF-IDF + weight로 정렬)
python lethe_min_v2.py retrieve --mem memories.json --ctx context.json --dsl example_v3.lethe --query "support-thread" --topk 7
```

- `memories.json` 예: `[{"id":"m1","text":"...","topic":"family","tags":["support-thread"],"timestamp":1696000000,"weight":0.5,"trust":0.9}]`
- `context.json` 예: `{"now":"2025-08-26T12:00:00","trust":0.6}`

## 3) 출력물
- `lethe_before.csv`/`lethe_after.csv` — 규칙 적용 전/후의 가중치, 플래그(shielded) 비교
- `lethe_audit.csv` — 어떤 규칙이 어떤 항목에 적용됐는지 히스토리

## 4) 통합 팁
- 기존 프로젝트에서 **대체 런너**로 쓰면 안전합니다. 원래 코드 수정 없이 `memories.json`/`context.json`/`*.lethe`만 맞춰 사용.
- `shielded=True`인 항목은 검색엔진에서 제외되지만 데이터는 보존됩니다.

## 5) 라이선스/의견
원하시면 규칙 더 추가해 드릴 수 있어요. 문제 있으면 해당 JSON/DSL과 함께 알려주시면 재현해서 고칩니다.
