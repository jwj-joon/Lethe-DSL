# Minimal Lethe Prototype (Toy)
This is a single-file, dependency-free prototype to **test your idea**:
- Emotions define decay `lambda` and floor `a(E)`
- Rules: `forget` on low trust for sensitive topic; `reinforce` on event for a tag & emotion
- Retrieval: weight × keyword overlap × optional E-weighted gate

## Files
- `lethe_min.py` — engine
- `demo_lethe.py` — runnable demo

## Run
```bash
python demo_lethe.py
```

## Example DSL
```text
emotion sadness { lambda=0.35, floor=0.10 }
emotion gratitude { lambda=0.05, floor=0.20 }
rule on trust < 0.4 -> forget topic:"ex-relationship" keep_log:true
rule on event == "milestone" with E=gratitude -> reinforce tag:"support-thread" by 0.2
retrieval { gate: E-weighted, topk: 5, entropy_filter: off }
```

## Notes
- Parsing is **regex + forgiving**. It’s just enough for demoing.
- Decay uses hours since `last_updated` with exponential `exp(-lambda * dt)` and clamps to floor.
- Gating is toy: small boost to stable emotions (low lambda).
- Replace the keyword-overlap scorer with your own RAG or vector search later.
- The **audit log** records forget/reinforce actions.
