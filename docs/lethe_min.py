# lethe_min.py
# Minimal Lethe engine (no external deps). Toy prototype for concept testing.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
import re, math, time
from datetime import datetime, timedelta

# ---------- Models ----------

@dataclass
class Emotion:
    name: str
    lam: float  # decay rate lambda
    floor: float  # memory floor a(E)

@dataclass
class MemoryUnit:
    id: str
    text: str
    topic: str = ""
    tags: List[str] = field(default_factory=list)
    emotion: str = "neutral"  # label for this memory
    created_at: datetime = field(default_factory=datetime.utcnow)
    weight: float = 0.5  # [0,1]
    # dynamic
    last_updated: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ForgetRule:
    trust_lt: float
    topic: str
    keep_log: bool = True

@dataclass
class ReinforceRule:
    event_eq: str
    emotion: str
    tag: str
    by: float = 0.2

@dataclass
class RetrievalConfig:
    gate: str = "E-weighted"
    topk: int = 8
    entropy_filter: bool = False

# ---------- Engine ----------

class LetheEngine:
    def __init__(self):
        self.emotions: Dict[str, Emotion] = {
            "neutral": Emotion("neutral", lam=0.15, floor=0.05)
        }
        self.forget_rules: List[ForgetRule] = []
        self.reinforce_rules: List[ReinforceRule] = []
        self.retrieval_cfg: RetrievalConfig = RetrievalConfig()
        self.audit_log: List[Dict[str, Any]] = []

    # --- DSL parsing (regex-based, very forgiving) ---
    def parse(self, dsl: str) -> None:
        lines = [ln.strip() for ln in dsl.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        for ln in lines:
            # emotion sadness { lambda=0.35, floor=0.10 }
            m = re.match(r'^emotion\s+(\w+)\s*\{\s*lambda\s*=\s*([0-9.]+)\s*,\s*floor\s*=\s*([0-9.]+)\s*\}$', ln, re.I)
            if m:
                name, lam, floor = m.group(1), float(m.group(2)), float(m.group(3))
                self.emotions[name] = Emotion(name, lam, floor)
                continue

            # rule on trust < 0.4 -> forget topic:"ex-relationship" keep_log:true
            m = re.match(r'^rule\s+on\s+trust\s*<\s*([0-9.]+)\s*->\s*forget\s+topic:"([^"]+)"\s*keep_log\s*:\s*(true|false)\s*$', ln, re.I)
            if m:
                thr, topic, keep = float(m.group(1)), m.group(2), m.group(3).lower() == "true"
                self.forget_rules.append(ForgetRule(trust_lt=thr, topic=topic, keep_log=keep))
                continue

            # rule on event == "milestone" with E=gratitude -> reinforce tag:"support-thread" by 0.2
            m = re.match(r'^rule\s+on\s+event\s*==\s*"([^"]+)"\s*with\s*E\s*=\s*(\w+)\s*->\s*reinforce\s+tag:"([^"]+)"\s*by\s*([+-]?[0-9.]+)\s*$', ln, re.I)
            if m:
                ev, emo, tag, by = m.group(1), m.group(2), m.group(3), float(m.group(4))
                self.reinforce_rules.append(ReinforceRule(event_eq=ev, emotion=emo, tag=tag, by=by))
                continue

            # retrieval { gate: E-weighted, topk: 8, entropy_filter: on }
            m = re.match(r'^retrieval\s*\{\s*gate\s*:\s*([\w\-]+)\s*,\s*topk\s*:\s*(\d+)\s*,\s*entropy_filter\s*:\s*(on|off)\s*\}$', ln, re.I)
            if m:
                gate, topk, ent = m.group(1), int(m.group(2)), m.group(3).lower() == "on"
                self.retrieval_cfg = RetrievalConfig(gate=gate, topk=topk, entropy_filter=ent)
                continue

            # If nothing matched, ignore or raise warning (here we ignore gracefully)
            # print(f"[LetheEngine] Unrecognized DSL line: {ln}")

    # --- Core dynamics ---
    def _emotion_params(self, emo_name: str) -> Tuple[float, float]:
        emo = self.emotions.get(emo_name, self.emotions["neutral"])
        return emo.lam, emo.floor

    def decay(self, mu: MemoryUnit, now: Optional[datetime] = None, I: float = 1.0) -> None:
        now = now or datetime.utcnow()
        lam, floor = self._emotion_params(mu.emotion)
        dt = (now - mu.last_updated).total_seconds() / 3600.0  # hours
        if dt <= 0: return
        new_weight = max(floor, mu.weight * math.exp(-lam * dt / max(I, 1e-6)))
        mu.weight = new_weight
        mu.last_updated = now

    def apply_rules(self, memories: List[MemoryUnit], context: Dict[str, Any]) -> None:
        # Forget rules
        for fr in self.forget_rules:
            trust = float(context.get("trust", 1.0))
            if trust < fr.trust_lt:
                for mu in memories:
                    if mu.topic == fr.topic:
                        before = mu.weight
                        lam, floor = self._emotion_params(mu.emotion)
                        mu.weight = max(floor, mu.weight * 0.1)  # hard down-weight for sensitive topic
                        if fr.keep_log:
                            self.audit_log.append({
                                "type": "forget",
                                "memory_id": mu.id,
                                "topic": mu.topic,
                                "before": before,
                                "after": mu.weight,
                                "time": datetime.utcnow().isoformat()
                            })

        # Reinforce rules
        for rr in self.reinforce_rules:
            if str(context.get("event", "")) == rr.event_eq:
                for mu in memories:
                    if mu.emotion == rr.emotion and rr.tag in mu.tags:
                        before = mu.weight
                        mu.weight = min(1.0, mu.weight + rr.by)
                        self.audit_log.append({
                            "type": "reinforce",
                            "memory_id": mu.id,
                            "tag": rr.tag,
                            "before": before,
                            "after": mu.weight,
                            "time": datetime.utcnow().isoformat()
                        })

    # E-weighted gate: simple multiplier based on emotion decay (smaller lambda => more stable => more weight)
    def _emotion_gate(self, mu: MemoryUnit) -> float:
        lam, floor = self._emotion_params(mu.emotion)
        # Map lambda to stability boost in [0.9, 1.1] (toy)
        stability = max(0.9, min(1.1, 1.1 - lam * 0.2))
        return stability

    def _keyword_overlap(self, q: str, text: str) -> float:
        qset = {w for w in re.findall(r'\w+', q.lower()) if len(w) > 2}
        tset = {w for w in re.findall(r'\w+', text.lower()) if len(w) > 2}
        if not qset: return 0.0
        overlap = len(qset & tset) / len(qset)
        return overlap

    def retrieve(self, memories: List[MemoryUnit], query: str) -> List[Tuple[MemoryUnit, float]]:
        scored = []
        for mu in memories:
            # always decay a little based on current time
            self.decay(mu)
            s = mu.weight * (1.0 + self._keyword_overlap(query, mu.text))
            if self.retrieval_cfg.gate.lower().startswith("e-weight"):
                s *= self._emotion_gate(mu)
            scored.append((mu, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[: self.retrieval_cfg.topk]

# Convenience: build memories from simple dicts
def build_memories(items: List[dict]) -> List[MemoryUnit]:
    res = []
    now = datetime.utcnow()
    for i, d in enumerate(items):
        created_days_ago = float(d.get("days_ago", 0))
        created_at = now - timedelta(days=created_days_ago)
        res.append(MemoryUnit(
            id=str(i+1),
            text=d.get("text", ""),
            topic=d.get("topic", ""),
            tags=d.get("tags", []),
            emotion=d.get("emotion", "neutral"),
            created_at=created_at,
            last_updated=created_at,
            weight=float(d.get("weight", 0.5))
        ))
    return res
