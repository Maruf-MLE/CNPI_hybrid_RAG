"""
upload_morning_shift.py
-----------------------
Uploads class-routine_1st_shift.json (morning/1st shift) to the create API.

Key difference from previous script:
  skip_llm=True  →  NO Gemini question generation.
                    Embedding uses raw content directly.
                    Much faster, no Gemini rate-limit risk.

Delay between calls: 5s (safe without Gemini, just for embedding API).
"""

import json
import time
import uuid
import requests

# ── Config ───────────────────────────────────────────────────────────────────
BASE_URL        = "https://cnpi-hybrid-rag-1.onrender.com"
API_ENDPOINT    = f"{BASE_URL}/admin-panel/api/create/"
JSON_FILE       = r"G:\CNPI_Hybrid_RAG\cnpi_api\Document\class-routine_1st_shift.json"
RESULT_FILE     = r"G:\CNPI_Hybrid_RAG\morning_shift_results.json"

DOC_TYPE        = "documents"
NUM_QUESTIONS   = 7           # irrelevant when skip_llm=True, but required by API
TOPIC           = "class routine"
SKIP_LLM        = True        # ← bypass Gemini question generation
DELAY_SEC       = 5           # shorter delay — no Gemini rate limit concern
REQUEST_TIMEOUT = 60
# ─────────────────────────────────────────────────────────────────────────────


def load_data(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def upload_chunk(index: int, total: int, content: str) -> dict:
    chunk_id = f"class_routine_ms_{uuid.uuid4().hex[:12]}"

    payload = {
        "chunk_id":      chunk_id,
        "content":       content,
        "doc_type":      DOC_TYPE,
        "num_questions": NUM_QUESTIONS,
        "topic":         TOPIC,
        "skip_llm":      "true" if SKIP_LLM else "false",
        "source_file":   "class-routine_1st_shift.json",
    }

    print(f"\n[{index + 1:>3}/{total}]  chunk_id = {chunk_id}")
    print(f"             content  = {content[:100].strip()!r}...")

    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        print("  ERROR: request timed out!")
        return {"error": "timeout"}
    except requests.exceptions.RequestException as exc:
        print(f"  ERROR: {exc}")
        return {"error": str(exc)}

    if response.ok:
        print(f"  Status  : {response.status_code} OK")
        try:
            resp_data = response.json()
        except Exception:
            resp_data = {"raw": response.text}
        doc_id = resp_data.get("doc_id", "?")
        emb = resp_data.get("embedding_generated", "?")
        llm = resp_data.get("metadata_extraction_success", "?")
        print(f"  doc_id={doc_id}  embedding={emb}  llm_extraction={llm}")
        return resp_data
    else:
        print(f"  ERROR {response.status_code}: {response.text[:300]}")
        return {"error": response.status_code, "detail": response.text}


def main():
    data  = load_data(JSON_FILE)
    total = len(data)

    print("=" * 65)
    print(f"  File     : {JSON_FILE}")
    print(f"  Endpoint : {API_ENDPOINT}")
    print(f"  Total    : {total} objects")
    print(f"  skip_llm : {SKIP_LLM}  ← NO Gemini question generation")
    print(f"  delay    : {DELAY_SEC}s between calls")
    print("=" * 65)

    results = []

    for i, obj in enumerate(data):
        content = obj.get("content", "").strip()
        if not content:
            print(f"\n[{i + 1:>3}/{total}]  SKIP – empty content")
            results.append({"index": i, "skipped": True})
            continue

        result = upload_chunk(i, total, content)
        results.append({
            "index":    i,
            "chunk_id": result.get("chunk_id"),
            "result":   result,
        })

        if i < total - 1:
            print(f"  Sleeping {DELAY_SEC}s ...")
            time.sleep(DELAY_SEC)

    success = sum(1 for r in results if "error" not in r.get("result", {}))
    print("\n" + "=" * 65)
    print(f"  Done!  Successful: {success}/{total}")
    print("=" * 65)

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Results saved → {RESULT_FILE}")


if __name__ == "__main__":
    main()
