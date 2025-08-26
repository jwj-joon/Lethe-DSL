# demo_lethe.py
# Run a tiny end-to-end demo of the Minimal Lethe engine.
import json
from lethe_min import LetheEngine, build_memories

DSL = """
# emotions
emotion sadness { lambda=0.35, floor=0.10 }
emotion gratitude { lambda=0.05, floor=0.20 }
emotion joy { lambda=0.10, floor=0.15 }

# rules
rule on trust < 0.4 -> forget topic:"ex-relationship" keep_log:true
rule on event == "milestone" with E=gratitude -> reinforce tag:"support-thread" by 0.2

# retrieval
retrieval { gate: E-weighted, topk: 5, entropy_filter: off }
"""

# sample memories
MEMS = [
    {"text": "Talked about ex-relationship and felt overwhelmed.", "topic": "ex-relationship", "tags": ["sensitive"], "emotion": "sadness", "weight": 0.7, "days_ago": 2},
    {"text": "Advisor praised the draft; felt gratitude and motivation.", "topic": "research", "tags": ["support-thread"], "emotion": "gratitude", "weight": 0.6, "days_ago": 1},
    {"text": "Went for a 30-minute run; felt joy afterwards.", "topic": "health", "tags": ["routine"], "emotion": "joy", "weight": 0.55, "days_ago": 0.2},
    {"text": "Noted cafe as a good quiet place for writing.", "topic": "environment", "tags": ["cue"], "emotion": "neutral", "weight": 0.5, "days_ago": 5},
    {"text": "Support message from a friend reduced stress.", "topic": "social", "tags": ["support-thread"], "emotion": "gratitude", "weight": 0.45, "days_ago": 3},
]

def tableify(rows):
    # return a simple list of dicts for printing or external display
    return [{
        "id": mu.id, "topic": mu.topic, "emotion": mu.emotion, "tags": ",".join(mu.tags),
        "weight": round(mu.weight, 4), "score": round(score, 4), "text": mu.text[:80] + ("..." if len(mu.text) > 80 else "")
    } for mu, score in rows]

def main():
    engine = LetheEngine()
    engine.parse(DSL)
    memories = build_memories(MEMS)

    print("=== BEFORE rules (top-5 for query='support') ===")
    before = engine.retrieve(memories, query="support")
    print(json.dumps(tableify(before), indent=2))

    context = {"trust": 0.3, "event": "milestone"}
    engine.apply_rules(memories, context)

    print("\\n=== AFTER rules (top-5 for query='support') ===")
    after = engine.retrieve(memories, query="support")
    print(json.dumps(tableify(after), indent=2))

    print("\\n=== AUDIT LOG ===")
    print(json.dumps(engine.audit_log, indent=2))

if __name__ == "__main__":
    main()
