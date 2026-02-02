import json
import csv
import time
import requests
from statistics import mean
import re

BASE_URL = "http://localhost:8000/chat"
TEST_QUESTIONS_PATH = "qa_chat_kb_v1.jsonl"
OUTPUT_CSV_PATH = "test_results.csv"

def load_jsonl(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items

def call_model(question: str):
    payload = {"question": question}
    headers = {"Content-Type": "application/json"}
    t0 = time.time()
    resp = requests.post(BASE_URL, headers=headers, data=json.dumps(payload), timeout=30)
    t1 = time.time()
    resp.raise_for_status()
    data = resp.json()
    latency_ms = (t1 - t0) * 1000.0
    answer = data.get("answer", "")
    return answer, latency_ms, data

def extract_ints(text: str):
    nums = re.findall(r"\d[\d\.]*", text)
    cleaned = []
    for n in nums:
        try:
            cleaned.append(int(n.replace(".", "")))
        except ValueError:
            continue
    return cleaned

def simple_score(model_answer: str, golden_answer: str) -> float:
    ma = model_answer.lower()
    ga = golden_answer.lower()

    golden_nums = extract_ints(ga)
    model_nums = extract_ints(ma)

    if not golden_nums:
        return 1.0 if ma.strip() else 0.0

    if not model_nums:
        return 0.0

    matched = sum(1 for n in golden_nums if n in model_nums)
    return matched / len(golden_nums)

def main():
    items = load_jsonl(TEST_QUESTIONS_PATH)

    latencies = []
    scores = []
    per_diff = {}

    with open(OUTPUT_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "difficulty", "question", "golden_answer", "model_answer", "score", "latency_ms"])

        for item in items:
            qid = item["id"]
            diff = item.get("difficulty", "unknown")
            question = item["question"]
            golden_answer = item["answer"]

            try:
                model_answer, latency_ms, _ = call_model(question)
                score = simple_score(model_answer, golden_answer)

                latencies.append(latency_ms)
                scores.append(score)
                per_diff.setdefault(diff, []).append(score)

                writer.writerow([
                    qid, diff, question,
                    golden_answer, model_answer,
                    score, round(latency_ms, 2)
                ])

                print(f"[OK] id={qid} diff={diff} score={score:.2f} latency={latency_ms:.1f}ms")
            except Exception as e:
                writer.writerow([
                    qid, diff, question,
                    golden_answer, f"ERROR: {e}",
                    0.0, ""
                ])
                print(f"[ERR] id={qid} diff={diff} -> {e}")

    def p95(values):
        if not values:
            return 0
        s = sorted(values)
        k = int(0.95 * (len(s) - 1))
        return s[k]

    print("\n=== SUMMARY ===")
    if scores:
        print(f"Overall avg score: {mean(scores):.3f}")
    for diff, scs in per_diff.items():
        print(f"{diff} avg score: {mean(scs):.3f}")
    if latencies:
        print(f"Avg latency: {mean(latencies):.1f} ms")
        print(f"p95 latency: {p95(latencies):.1f} ms")

if __name__ == "__main__":
    main()
