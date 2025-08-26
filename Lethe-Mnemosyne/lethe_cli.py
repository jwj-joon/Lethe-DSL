#!/usr/bin/env python3
import argparse
import json
from lethe_min import LetheEngine

def main():
    parser = argparse.ArgumentParser(description="Lethe CLI: Memory control with DSL")
    parser.add_argument("--dsl", type=str, required=True, help="Path to Lethe DSL rules file")
    parser.add_argument("--memories", type=str, required=True, help="Path to memories JSON")
    parser.add_argument("--context", type=str, required=True, help="Path to context JSON")
    parser.add_argument("--query", type=str, required=True, help="Search query")
    args = parser.parse_args()

    with open(args.dsl, "r") as f:
        dsl_rules = f.read()

    with open(args.memories, "r") as f:
        memories = json.load(f)

    with open(args.context, "r") as f:
        context = json.load(f)

    engine = LetheEngine(dsl_rules)
    print("=== BEFORE RULES ===")
    before = engine.search(memories, args.query)
    for m in before:
        print(f"- {m['content']}")

    print("\n=== APPLYING RULES ===")
    after = engine.apply_rules(memories, context)
    for log in engine.audit_log:
        print(f"[RULE] {log}")

    print("\n=== AFTER RULES ===")
    after_results = engine.search(after, args.query)
    for m in after_results:
        print(f"- {m['content']}")

if __name__ == "__main__":
    main()
