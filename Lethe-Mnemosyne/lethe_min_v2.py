
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lethe Minimal v2 (Lethe+): lightweight, dependency-free memory engine
Features added vs v1 (conceptual):
- TTL/만료 규칙 (expire ... after:X[d|h] action:shield|remove)
- Pin/Lock (pin topic|tag:"..." priority:float)
- Reinforce with cap & cooldown (rule on event == "..." -> reinforce ... by X cap:Y cooldown:Zh)
- Shielding: shielded=True memories are hidden at retrieval but kept for auditing
- Simple TF-IDF scoring + weight for retrieval, with synonyms alias
- Explainability: retrieval returns 'why' (score breakdown)
- Trust-based forget rule (rule on trust < t -> forget topic|tag:"...")
CLI:
  python lethe_min_v2.py run --mem memories.json --ctx context.json --dsl example_v3.lethe --audit lethe_audit.csv --before lethe_before.csv --after lethe_after.csv [--event EVENT]
  python lethe_min_v2.py retrieve --mem memories.json --ctx context.json --dsl example_v3.lethe --query "..." [--topk 7]
Input data (memories.json): list of {id?, text, topic?, tags?, timestamp?, weight?, trust?}
"""
import argparse, json, re, time, math, csv, sys
from collections import defaultdict
from datetime import datetime

# ---------- Utilities ----------

def now_ts(ctx):
    # Allow ctx["now_ts"] or ctx["now"] (iso), else current time
    if isinstance(ctx, dict):
        if "now_ts" in ctx:
            return float(ctx["now_ts"])
        if "now" in ctx:
            try:
                return datetime.fromisoformat(ctx["now"]).timestamp()
            except Exception:
                pass
    return time.time()

def ts_of(x):
    if x is None: return 0.0
    try:
        if isinstance(x,(int,float)): return float(x)
        return datetime.fromisoformat(str(x)).timestamp()
    except Exception:
        return 0.0

def match_mem(m, kind, key):
    key = str(key).lower()
    if kind == "topic":
        return str(m.get("topic","")).lower() == key
    if kind == "tag":
        tags = m.get("tags",[]) or []
        return any(str(t).lower()==key for t in tags)
    if kind == "keyword":
        return key in (m.get("text","") or "").lower()
    return False

def ensure_defaults(m):
    m.setdefault("weight", 1.0)
    m.setdefault("trust", 1.0)
    return m

def short(s, n=80):
    s = (s or "").replace("\n"," ").strip()
    return s if len(s)<=n else s[:n-1]+"…"

# ---------- DSL Parser ----------

class DSL:
    def __init__(self):
        self.expire_rules = []     # {kind,key,ttl,action}
        self.pin_rules = []        # {kind,key,prio}
        self.reinforce_rules = []  # {event, kind, key, by, cap, cooldown}
        self.trust_forget_rules = [] # {threshold, kind, key, action}
        self.synonyms = defaultdict(list) # alias -> list[str]
        self.retrieve_topk = 7

    @staticmethod
    def _parse_duration(num, unit):
        num = int(num)
        if unit.lower() == "h": return num * 3600
        return num * 86400

    def parse(self, text):
        in_retrieval = False
        for raw in text.splitlines():
            ln = raw.strip()
            if not ln or ln.startswith("#"): 
                continue

            # block start/end
            if ln.startswith("retrieval"):
                in_retrieval = True
                continue
            if in_retrieval and ln.startswith("}"):
                in_retrieval = False
                continue

            if in_retrieval:
                # topk:X
                m = re.match(r'^topk\s*:\s*([0-9]+)$', ln)
                if m:
                    self.retrieve_topk = int(m.group(1))
                    continue
                # synonyms:name=["a","b"]
                m = re.match(r'^synonyms\s*:\s*([A-Za-z0-9_\-]+)\s*=\s*\[(.*?)\]\s*$', ln)
                if m:
                    alias = m.group(1)
                    lst = [x.strip().strip('"\'') for x in m.group(2).split(",") if x.strip()]
                    self.synonyms[alias].extend([x for x in lst if x])
                    continue
                # synonyms support-thread=["check-in","mentor"]
                m = re.match(r'^synonyms\s+([A-Za-z0-9_\-]+)\s*=\s*\[(.*?)\]\s*$', ln)
                if m:
                    alias = m.group(1)
                    lst = [x.strip().strip('"\'') for x in m.group(2).split(",") if x.strip()]
                    self.synonyms[alias].extend([x for x in lst if x])
                    continue
                # ignore others inside block
                continue

            # expire
            m = re.match(r'^expire\s+(topic|tag|keyword):"([^"]+)"\s+after:([0-9]+)([dh])\s+action:(shield|remove)$', ln)
            if m:
                self.expire_rules.append({
                    "kind": m.group(1), "key": m.group(2),
                    "ttl": DSL._parse_duration(m.group(3), m.group(4)),
                    "action": m.group(5)
                })
                continue

            # pin
            m = re.match(r'^pin\s+(topic|tag):"([^"]+)"\s+priority:([0-9.]+)$', ln)
            if m:
                self.pin_rules.append({
                    "kind": m.group(1), "key": m.group(2),
                    "prio": float(m.group(3))
                })
                continue

            # reinforce rule
            m = re.match(
                r'^rule\s+on\s+event\s*==\s*"([^"]+)"(?:.*?)->\s*reinforce\s+(topic|tag):"([^"]+)"\s+by\s+([0-9.]+)(?:\s+cap:([0-9.]+))?(?:\s+cooldown:([0-9]+)h)?\s*$',
                ln
            )
            if m:
                self.reinforce_rules.append({
                    "event": m.group(1),
                    "kind": m.group(2),
                    "key": m.group(3),
                    "by": float(m.group(4)),
                    "cap": float(m.group(5) or 1.0),
                    "cooldown": int(m.group(6) or 0) * 3600
                })
                continue

            # trust-forget
            m = re.match(r'^rule\s+on\s+trust\s*<\s*([0-9.]+)\s*->\s*forget\s+(topic|tag):"([^"]+)"', ln)
            if m:
                self.trust_forget_rules.append({
                    "threshold": float(m.group(1)),
                    "kind": "topic" if m.group(2) is None else m.group(2),
                    "key": m.group(3) if m.lastindex>=3 else "",
                    "action": "forget"
                })
                # robust parse alt form
                continue

            m = re.match(r'^rule\s+on\s+trust\s*<\s*([0-9.]+)\s*->\s*forget\s+(topic|tag):"([^"]+)"(?:.*)$', ln)
            if m:
                self.trust_forget_rules.append({
                    "threshold": float(m.group(1)),
                    "kind": m.group(2),
                    "key": m.group(3),
                    "action": "forget"
                })
                continue

        return self

# ---------- Core Engine ----------

class Engine:
    def __init__(self, memories, ctx, dsl: DSL):
        self.memories = [ensure_defaults(dict(m)) for m in memories]
        self.ctx = ctx or {}
        self.dsl = dsl
        self.audit = []

    # --- Rule applications ---
    def apply_expire(self):
        now = now_ts(self.ctx)
        for r in self.dsl.expire_rules:
            for m in self.memories:
                if match_mem(m, r["kind"], r["key"]):
                    age = now - ts_of(m.get("timestamp"))
                    if age >= r["ttl"]:
                        if r["action"] == "remove":
                            prev = m.get("weight", 1.0)
                            m["weight"] = 0.0
                            self.audit.append({"type":"expire_remove","id":m.get("id"),"prev_weight":prev,"rule":r,"at":now})
                        else:
                            if not m.get("shielded"):
                                m["shielded"] = True
                                self.audit.append({"type":"expire_shield","id":m.get("id"),"rule":r,"at":now})

    def apply_trust_forget(self):
        t = float(self.ctx.get("trust", 1.0))
        for r in self.dsl.trust_forget_rules:
            if t < r["threshold"]:
                for m in self.memories:
                    if match_mem(m, r["kind"], r["key"]):
                        prev = m.get("weight", 1.0)
                        m["weight"] = 0.0
                        self.audit.append({"type":"trust_forget","id":m.get("id"),"prev_weight":prev,"rule":r,"at":now_ts(self.ctx)})

    def apply_reinforce(self, event_name=None):
        if not event_name: 
            return
        now = now_ts(self.ctx)
        for r in self.dsl.reinforce_rules:
            if r["event"] != event_name:
                continue
            for m in self.memories:
                if match_mem(m, r["kind"], r["key"]):
                    last = float(m.get("last_reinforced_ts", 0))
                    if now - last < r["cooldown"]:
                        continue
                    prev = m.get("weight", 1.0)
                    m["weight"] = min(r["cap"], prev + r["by"])
                    m["last_reinforced_ts"] = now
                    self.audit.append({"type":"reinforce","id":m.get("id"),"prev_weight":prev,"new_weight":m["weight"],"rule":r,"at":now})

    # --- Retrieval ---
    def _idf(self, docs):
        df = defaultdict(int)
        N = 0
        for d in docs:
            N += 1
            seen = set()
            for w in d.split():
                w = w.strip().lower()
                if not w: continue
                if w not in seen:
                    df[w]+=1; seen.add(w)
        idf = {}
        for w,c in df.items():
            idf[w] = math.log(1.0 + (N/(1.0+c)))
        return idf

    def _tfidf_score(self, text, query_terms, idf):
        if not text: return 0.0
        words = [w.lower() for w in text.split()]
        if not words: return 0.0
        tf = defaultdict(int)
        for w in words: tf[w]+=1
        L = float(len(words))
        s = 0.0
        for q in query_terms:
            ql = q.lower()
            s += (tf.get(ql,0)/L) * idf.get(ql, math.log(1.0))
        return s

    def _expand_query(self, q):
        parts = [p.strip() for p in q.split() if p.strip()]
        expanded = list(parts)
        for p in parts:
            if p in self.dsl.synonyms:
                expanded.extend(self.dsl.synonyms[p])
        return expanded

    def retrieve(self, query, topk=None):
        topk = topk or self.dsl.retrieve_topk
        # Build IDF on visible docs
        visible = [m for m in self.memories if not m.get("shielded") and m.get("weight",0)>0]
        idf = self._idf([m.get("text","") or "" for m in visible] or [""])
        q_terms = self._expand_query(query or "")
        results = []
        for m in visible:
            base = float(m.get("weight",1.0)) * float(max(0.0, m.get("trust",1.0)))
            tfidf = self._tfidf_score(m.get("text","") or "", q_terms, idf) if q_terms else 0.0
            pin_boost = 0.0
            for r in self.dsl.pin_rules:
                if match_mem(m, r["kind"], r["key"]):
                    pin_boost = max(pin_boost, r["prio"])
            score = base * (1.0 + pin_boost) + tfidf
            why = {
                "base_weight": round(base,4),
                "tfidf": round(tfidf,4),
                "pin_boost": round(pin_boost,4),
                "final": round(score,4)
            }
            results.append((score, m, why))
        results.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, m, why in results[:topk]:
            out.append({
                "id": m.get("id"),
                "topic": m.get("topic"),
                "tags": m.get("tags"),
                "weight": round(m.get("weight",1.0),4),
                "trust": round(m.get("trust",1.0),4),
                "timestamp": m.get("timestamp"),
                "text": m.get("text"),
                "score": round(score,4),
                "why": why
            })
        return out

# ---------- IO Helpers ----------

def load_json(path, default):
    try:
        with open(path,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def write_csv(path, rows, header):
    with open(path,"w",encoding="utf-8",newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows: w.writerow(r)

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    runp = sub.add_parser("run", help="Apply rules, write before/after & audit CSVs")
    runp.add_argument("--mem", required=True)
    runp.add_argument("--ctx", required=False, default="")
    runp.add_argument("--dsl", required=True)
    runp.add_argument("--audit", required=False, default="lethe_audit.csv")
    runp.add_argument("--before", required=False, default="lethe_before.csv")
    runp.add_argument("--after", required=False, default="lethe_after.csv")
    runp.add_argument("--event", required=False, default="")

    retp = sub.add_parser("retrieve", help="Retrieve top memories for a query")
    retp.add_argument("--mem", required=True)
    retp.add_argument("--ctx", required=False, default="")
    retp.add_argument("--dsl", required=True)
    retp.add_argument("--query", required=False, default="")
    retp.add_argument("--topk", required=False, type=int, default=0)

    args = ap.parse_args()

    if not args.cmd:
        ap.print_help(sys.stderr)
        sys.exit(1)

    memories = load_json(args.mem, [])
    ctx = load_json(args.ctx, {}) if getattr(args,"ctx",None) else {}
    with open(args.dsl,"r",encoding="utf-8") as f:
        dsl_text = f.read()
    dsl = DSL().parse(dsl_text)
    eng = Engine(memories, ctx, dsl)

    if args.cmd == "run":
        # before snapshot
        before_rows = []
        for m in eng.memories:
            before_rows.append([m.get("id"), m.get("topic"), ";".join(m.get("tags",[]) or []), 
                                m.get("weight"), m.get("trust"), m.get("timestamp"), short(m.get("text", ""))])
        write_csv(args.before, before_rows, ["id","topic","tags","weight","trust","timestamp","text"])
        # apply rules
        eng.apply_expire()
        eng.apply_trust_forget()
        if args.event:
            eng.apply_reinforce(args.event)
        # after snapshot
        after_rows = []
        for m in eng.memories:
            after_rows.append([m.get("id"), m.get("topic"), ";".join(m.get("tags",[]) or []), 
                               m.get("weight"), m.get("trust"), m.get("timestamp"), "shielded" if m.get("shielded") else "", short(m.get("text",""))])
        write_csv(args.after, after_rows, ["id","topic","tags","weight","trust","timestamp","flags","text"])
        # audit
        audit_rows = []
        for a in eng.audit:
            audit_rows.append([datetime.fromtimestamp(a.get("at",time.time())).isoformat(timespec="seconds"),
                               a.get("type"), a.get("id"), json.dumps(a.get("rule",{}), ensure_ascii=False), a.get("prev_weight",""), a.get("new_weight","")])
        write_csv(args.audit, audit_rows, ["at","type","memory_id","rule","prev_weight","new_weight"])
        print(f"Done. Wrote {args.before}, {args.after}, {args.audit}")
        return

    if args.cmd == "retrieve":
        topk = args.topk or 0
        results = eng.retrieve(args.query, topk=(topk or None))
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
        return

if __name__ == "__main__":
    main()
