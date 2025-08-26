# Lethe / Mnemosyne  
*A Lightweight DSL for Emotional Memory, Forgetting, and Reconstruction*

---

## 🌊 Overview
**Lethe** models *forgetting, decay, and reinforcement* of memories through affective rules.  
**Mnemosyne** provides a DSL for *analysis, tracing, and reconstruction* of emotional memory patterns.  

Together, they form a **lightweight, dependency-free framework** for managing memory in AI agents with *privacy, trust, and emotional salience* at the core.

---

## ✨ Key Features
- **Emotional Decay Kernels** — sadness, anxiety, calm, gratitude (configurable λ, floor, decay functions)  
- **Selective Forgetting** — trust-based, TTL expiration, sensitive keyword shielding  
- **Reinforcement Rules** — boost positive/support memories on milestone events (cap + cooldown)  
- **Explainability** — retrieval returns a score breakdown (`base_weight`, `tfidf`, `pin_boost`, `final`)  
- **Privacy-Aware** — shield/remove personal or sensitive data automatically  
- **DSL Integration** — human-readable rules for forgetting and remembering

---


---

## 🚀 Quickstart

### 1) Run demo
```bash
python demo_lethe.py
```

### 2) Apply rules & generate audit logs
```bash
python lethe_min_v2.py run \
  --mem memories.json \
  --ctx context.json \
  --dsl examples/example_v3.lethe \
  --audit lethe_audit.csv \
  --before lethe_before.csv \
  --after lethe_after.csv \
  --event milestone
```

### 3) Retrieval
```bash
python lethe_min_v2.py retrieve \
  --mem memories.json \
  --ctx context.json \
  --dsl examples/example_v3.lethe \
  --query "support-thread" \
  --topk 7
```

---

## 🧩 Example DSL
```text
# emotions
emotion sadness   { lambda=0.35, floor=0.10, decay="power_law", k=1.2 }
emotion gratitude { lambda=0.05, floor=0.20, decay="tanh", k=0.3, t0=7 }

# expiration & shielding
expire tag:"suicidal_thoughts" after:30d action:shield
expire keyword:"credit card number" after:24h action:remove

# trust-based forgetting
rule on trust < 0.4 -> forget topic:"ex-relationship"

# event reinforcement
rule on event == "milestone" with E=gratitude -> reinforce tag:"support-thread" by 0.2 cap:0.8 cooldown:24h

# retrieval policy
retrieval {
  topk:7
  synonyms support-thread=["check-in","mentor","encourage"]
}
```

---

## 🛡️ License
- **Academic & Nonprofit Use**: Free under [LICENSE-ACADEMIC](LICENSE-ACADEMIC.md)  
- **Commercial Use**: Requires a paid license. See [LICENSE-COMMERCIAL](LICENSE-COMMERCIAL.md).  

> Contact: dnjswns11228@gmail.com

---

## ✍️ Citation
If you use Lethe/Mnemosyne in research, please cite:

```
@misc{jung2025lethe,
  author       = {Wonjun Jung},
  title        = {Lethe & Mnemosyne: Lightweight DSL for Emotional Memory and Forgetting},
  year         = {2025},
  howpublished = {GitHub},
  url          = {https://github.com/jwj-joon/Lethe-Mnemosyne}
}
```

---

## 🌱 Acknowledgments
Inspired by the rivers of Greek mythology:  
- **Lethe (Λήθη)** — forgetting  
- **Mnemosyne (Μνημοσύνη)** — memory  

This project started as a personal exploration of how machines might *forget* like humans — not as a flaw, but as a **design principle**.
