# lethe_min.py
# Minimal, human-readable memory/forgetting engine with DSL parsing.
# Focus: transparency, controllability, auditability — not SOTA.
#
# Features in this "min" build:
# - Emotions with multiple forgetting kernels: exponential, power_law, sigmoid, tanh
# - Floor (minimum residual weight)
# - Simple rules:
#     * rule on trust < T -> forget topic:"..." keep_log:bool
#     * rule on event == "..." with E=<emotion> -> reinforce tag:"..." by <float>
# - Optional interference: new memory attenuates similar prior memories (topic or tag)
# - Tiny DSL parser (line-based, tolerant), no external deps
#
# API used by lethe_cli.py:
#   engine = LetheEngine(dsl_rules_text)
#   before = engine.search(memories, query)
#   after  = engine.apply_rules(memories, context)
#   after2 = engine.search(after, query)
#   engine.audit_log -> list of dicts
#
# Memory item schema (dict expected, minimal):
# {
#   "id": int|str (optional),
#   "content": str,
#   "topic": str (optional),
#   "tags": [str] (optional),
#   "emotion": str (optional),   # e.g., "sadness", "gratitude"
#   "weight": float (optional),  # defaults to 0.5
#   "timestamp": "YYYY-MM-DD" (optional)
# }
#
# Notes:
# - We keep everything simple and robust; failures default to no-op with audit entry.
# - Time decay is applied on search() using timestamp and the attached emotion kernel.

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


# ---------- Emotions & Decay Kernels ----------

@dataclass
class Emotion:
    name: str
    lam: float = 0.1
    floor: float = 0.0
    decay_fn: str = "exponential"       # 'exponential' | 'power_law' | 'sigmoid' | 'tanh'
    params: Dict[str, float] = field(default_factory=dict)

def decay_exponential(lam: float, t: float) -> float:
    return math.exp(-lam * t)

def decay_power_law(k: float, t: float) -> float:
    return 1.0 / ((t + 1.0) ** max(k, 1e-6))

def decay_sigmoid(k: float, t0: float, t: float) -> float:
    # 1 → 0 curve (reverse of standard sigmoid)
    return 1.0 - (1.0 / (1.0 + math.exp(-k * (t - t0))))

def decay_tanh(k: float, t0: float, t: float) -> float:
    # Map tanh(-∞..+∞) -> 1..0
    return (1.0 - math.tanh(k * (t - t0))) * 0.5

def apply_decay_with_floor(w0: float, floor: float, factor01: float) -> float:
    factor = max(0.0, min(1.0, factor01))
    return floor + (max(w0, floor) - floor) * factor


# ---------- Rules ----------

@dataclass
class ForgetRule:
    trust_lt: float
    topic: str
    keep_log: bool = True

@dataclass
class ReinforceRule:
    event_eq: str
    emotion_gate: Optional[str] = None  # optional: "with E=gratitude"
    tag: Optional[str] = None
    by: float = 0.2

@dataclass
class InterfereRule:
    match: str = "topic"    # 'topic' | 'tag'
    alpha: float = 0.1


# ---------- Engine ----------

class LetheEngine:
    def __init__(self, dsl: Optional[str] = None):
        self.emotions: Dict[str, Emotion] = {}
        self.forget_rules: List[ForgetRule] = []
        self.reinforce_rules: List[ReinforceRule] = []
        self.interfere_rule: Optional[InterfereRule] = None
        self.retrieval_topk: int = 5
        self.retrieval_gate: str = "E-weighted"
        self.audit_log: List[Dict[str, Any]] = []
        # default emotion
        self.emotions["neutral"] = Emotion(name="neutral", lam=0.08, floor=0.0, decay_fn="exponential")
        if dsl:
            self.parse(dsl)

    # ----- Parsing -----
    def parse(self, text: str) -> None:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        for ln in lines:
            # emotion NAME { ... }
            m = re.match(r'^emotion\s+([A-Za-z_][\w-]*)\s*\{([^}]*)\}\s*$', ln)
            if m:
                name, body = m.group(1), m.group(2)
                params = self._parse_kv(body)
                emo = Emotion(
                    name=name,
                    lam=float(params.get("lambda", params.get("lam", 0.1))),
                    floor=float(params.get("floor", 0.0)),
                    decay_fn=str(params.get("decay", "exponential")).lower(),
                    params={k: float(v) for k, v in params.items() if k in ("k", "t0")}
                )
                self.emotions[name] = emo
                self._audit("parse_emotion", {"name": name, **params})
                continue

            # interference { match="topic", alpha=0.12 }
            m = re.match(r'^interference\s*\{([^}]*)\}\s*$', ln)
            if m:
                body = m.group(1)
                params = self._parse_kv(body)
                self.interfere_rule = InterfereRule(
                    match=str(params.get("match", "topic")).strip('"').strip("'"),
                    alpha=float(params.get("alpha", 0.1))
                )
                self._audit("parse_interference", {"params": params})
                continue

            # rule on trust < 0.4 -> forget topic:"ex-relationship" keep_log:true
            m = re.match(r'^rule\s+on\s+trust\s*<\s*([0-9.]+)\s*->\s*forget\s+topic:\s*"(.*?)"(?:\s+keep_log\s*:\s*(true|false))?\s*$', ln, re.I)
            if m:
                thr = float(m.group(1))
                topic = m.group(2)
                keep = True if (m.group(3) or "").lower() == "true" else True
                self.forget_rules.append(ForgetRule(trust_lt=thr, topic=topic, keep_log=keep))
                self._audit("parse_rule_forget", {"trust_lt": thr, "topic": topic, "keep_log": keep})
                continue

            # rule on event == "milestone" with E=gratitude -> reinforce tag:"support-thread" by 0.2
            m = re.match(r'^rule\s+on\s+event\s*==\s*"(.*?)"(?:\s+with\s+E\s*=\s*([A-Za-z_][\w-]*))?\s*->\s*reinforce\s+tag:\s*"(.*?)"\s+by\s*([0-9.]+)\s*$', ln, re.I)
            if m:
                event, emo_gate, tag, by = m.group(1), m.group(2), m.group(3), float(m.group(4))
                self.reinforce_rules.append(ReinforceRule(event_eq=event, emotion_gate=emo_gate, tag=tag, by=by))
                self._audit("parse_rule_reinforce", {"event_eq": event, "E": emo_gate, "tag": tag, "by": by})
                continue

            # retrieval { gate: E-weighted, topk: 5 }
            m = re.match(r'^retrieval\s*\{([^}]*)\}\s*$', ln)
            if m:
                params = self._parse_kv(m.group(1))
                if "topk" in params:
                    self.retrieval_topk = int(float(params["topk"]))
                if "gate" in params:
                    self.retrieval_gate = str(params["gate"])
                self._audit("parse_retrieval", params)
                continue

            # Optional: legacy "decay(...)" line — we parse but do not use directly in min build
            if ln.startswith("decay("):
                self._audit("parse_legacy_decay_line", {"line": ln})
                continue

            # unknown line
            self._audit("parse_unknown", {"line": ln})

    def _parse_kv(self, body: str) -> Dict[str, str]:
        # Parses key=value pairs where value can be number or "string"
        kv = {}
        # split by commas not in quotes
        parts = re.findall(r'(\w+)\s*:\s*(".*?"|[^,]+)|(\w+)\s*=\s*(".*?"|[^,]+)', body)
        # parts is a list of tuples with either (: form) or (= form). Extract both.
        for a1, a2, b1, b2 in parts:
            if a1:
                key = a1.strip()
                val = a2.strip()
            else:
                key = b1.strip()
                val = b2.strip()
            kv[key] = val.strip().strip(",")
        # dequote
        for k, v in list(kv.items()):
            if isinstance(v, str) and len(v) >= 2 and v[0] in ["'", '"'] and v[-1] == v[0]:
                kv[k] = v[1:-1]
        return kv

    def _audit(self, typ: str, data: Dict[str, Any]) -> None:
        self.audit_log.append({"stage": "parser", "type": typ, "data": data})

    # ----- Helpers -----
    @staticmethod
    def _now_days() -> float:
        # Return current time in days since epoch (UTC)
        return datetime.now(timezone.utc).timestamp() / 86400.0

    @staticmethod
    def _parse_days(ts: Optional[str]) -> Optional[float]:
        if not ts:
            return None
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt.timestamp() / 86400.0
        except Exception:
            return None

    def _emotion_for(self, m: dict) -> Emotion:
        name = (m.get("emotion") or "neutral").lower()
        return self.emotions.get(name, self.emotions["neutral"])

    def _apply_time_decay(self, m: dict) -> None:
        """Apply time decay to m['weight'] based on its timestamp and emotion kernel."""
        t_now = self._now_days()
        t_item = self._parse_days(m.get("timestamp"))
        if t_item is None:
            return  # no timestamp → no decay
        dt_days = max(0.0, t_now - t_item)
        emo = self._emotion_for(m)
        w0 = float(m.get("weight", 0.5))
        # choose kernel
        if emo.decay_fn == "exponential":
            f = decay_exponential(emo.lam, dt_days)
        elif emo.decay_fn == "power_law":
            k = float(emo.params.get("k", 1.0))
            f = decay_power_law(k, dt_days)
        elif emo.decay_fn == "sigmoid":
            k = float(emo.params.get("k", 1.0)); t0 = float(emo.params.get("t0", 7.0))
            f = decay_sigmoid(k, t0, dt_days)
        elif emo.decay_fn == "tanh":
            k = float(emo.params.get("k", 0.3)); t0 = float(emo.params.get("t0", 7.0))
            f = decay_tanh(k, t0, dt_days)
        else:
            f = decay_exponential(emo.lam, dt_days)
        m["weight"] = apply_decay_with_floor(w0, emo.floor, f)

    # ----- Public API -----
    def search(self, memories: List[dict], query: str) -> List[dict]:
        """Return top-k items matching query, after applying time decay to their weights."""
        scored = []
        q = (query or "").lower()
        for m in memories:
            m = dict(m)  # shallow copy
            # ensure weight
            m.setdefault("weight", 0.5)
            # decay by time+emotion
            self._apply_time_decay(m)
            text = (m.get("content") or "") .lower()
            tags = [t.lower() for t in m.get("tags") or []]
            topic = (m.get("topic") or "").lower()
            # simple matching score
            match = 0.0
            if q and (q in text or q in tags or q == topic):
                match = 0.25
            if q in tags:
                match += 0.25
            score = float(m["weight"]) + match
            scored.append((score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[: self.retrieval_topk]]

    def apply_rules(self, memories: List[dict], context: Dict[str, Any]) -> List[dict]:
        out = [dict(m) for m in memories]
        # Forget rule on trust
        trust = float(context.get("trust_level", context.get("trust", 1.0)))
        for fr in self.forget_rules:
            if trust < fr.trust_lt:
                for m in out:
                    tags = m.get("tags") or []
                    topic = (m.get("topic") or "")
                    # match if topic equals or if tag list contains exact topic string
                    if topic == fr.topic or fr.topic in tags:
                        w0 = float(m.get("weight", 0.5))
                        m["weight"] = max(0.1, w0 * 0.5)  # simple attenuation
                        if fr.keep_log:
                            self.audit_log.append({
                                "stage": "engine", "type": "forget",
                                "reason": f"trust<{fr.trust_lt}", "match": fr.topic,
                                "id": m.get("id"), "before": w0, "after": m["weight"]
                            })

        # Reinforce rule on event
        event = str(context.get("event") or "")
        for rr in self.reinforce_rules:
            if rr.event_eq == event:
                for m in out:
                    tags = [t.lower() for t in (m.get("tags") or [])]
                    emo_name = (m.get("emotion") or "neutral").lower()
                    if rr.tag and rr.tag.lower() in tags:
                        if (rr.emotion_gate is None) or (emo_name == rr.emotion_gate.lower()):
                            w0 = float(m.get("weight", 0.5))
                            m["weight"] = min(1.0, w0 + rr.by)
                            self.audit_log.append({
                                "stage": "engine", "type": "reinforce",
                                "event": rr.event_eq, "tag": rr.tag, "by": rr.by,
                                "id": m.get("id"), "before": w0, "after": m["weight"]
                            })

        # Interference (lightweight): for items sharing tag/topic with a "newest" item, attenuate older ones a bit
        if self.interfere_rule:
            # pick newest item per (topic or first tag) and attenuate others
            # parse timestamps to sort
            def ts_days(m):
                d = self._parse_days(m.get("timestamp"))
                return d if d is not None else -1e9  # unknown timestamps go very old
            out_sorted = sorted(out, key=ts_days, reverse=True)
            seen_keys = set()
            for nm in out_sorted:
                key = None
                if self.interfere_rule.match == "topic":
                    key = (nm.get("topic") or "").lower()
                else:
                    # first tag if exists
                    tg = nm.get("tags") or []
                    key = (tg[0].lower() if tg else "")
                if not key:
                    continue
                if key in seen_keys:
                    continue
                # this is the "newest" for that key
                seen_keys.add(key)
                for m in out:
                    if m is nm:
                        continue
                    if self.interfere_rule.match == "topic":
                        same = (m.get("topic") or "").lower() == key
                    else:
                        same = key in [t.lower() for t in (m.get("tags") or [])]
                    if same:
                        w0 = float(m.get("weight", 0.5))
                        m["weight"] = max(0.0, w0 * (1.0 - self.interfere_rule.alpha))
                        self.audit_log.append({
                            "stage": "engine", "type": "interference",
                            "key": key, "alpha": self.interfere_rule.alpha,
                            "id": m.get("id"), "before": w0, "after": m["weight"]
                        })

        return out
