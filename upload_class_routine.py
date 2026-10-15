"""
upload_class_routine.py
-----------------------
Reads class_routine_1st_shift.json and uploads each entry one by one
to the admin-panel document-create API.

  • chunk_id  : auto-generated UUID per entry
  • doc_type  : "documents"
  • num_questions: 7
  • topic     : "class routine"
  • Delay between calls: 15 s  (Gemini rate-limit safe)
"""

import json
import time
import uuid
import requests

# ── Config ───────────────────────────────────────────────────────────────────
BASE_URL       = "https://cnpi-hybrid-rag-1.onrender.com"
API_ENDPOINT   = f"{BASE_URL}/admin-panel/api/create/"
JSON_FILE      = r"G:\CNPI_Hybrid_RAG\cnpi_api\Document\class_routine_1st_shift.json"
RESULT_FILE    = r"G:\CNPI_Hybrid_RAG\upload_results.json"

DOC_TYPE       = "documents"
NUM_QUESTIONS  = 7
TOPIC          = "class routine"
DELAY_SEC      = 15          # seconds between consecutive API calls
REQUEST_TIMEOUT = 120        # seconds to wait for a single response
# ─────────────────────────────────────────────────────────────────────────────


def load_data(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def upload_chunk(index: int, total: int, content: str) -> dict:
    """POST one chunk to the create endpoint. Returns parsed response dict."""
    chunk_id = f"class_routine_{uuid.uuid4().hex[:12]}"

    payload = {
        "chunk_id":      chunk_id,
        "content":       content,
        "doc_type":      DOC_TYPE,
        "num_questions": NUM_QUESTIONS,
        "topic":         TOPIC,
        "source_file":   "class_routine_1st_shift.json",
    }

    print(f"\n[{index + 1:>3}/{total}]  chunk_id = {chunk_id}")
    print(f"          content  = {content[:100].strip()!r}...")

    try:
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
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
        print(f"  Response: {str(resp_data)[:120]}")
        return resp_data
    else:
        print(f"  ERROR {response.status_code}: {response.text[:300]}")
        return {"error": response.status_code, "detail": response.text}


def main():
    data  = load_data(JSON_FILE)
    total = len(data)

    print("=" * 60)
    print(f"  Source   : {JSON_FILE}")
    print(f"  Endpoint : {API_ENDPOINT}")
    print(f"  Total    : {total} objects")
    print(f"  doc_type : {DOC_TYPE}")
    print(f"  topic    : {TOPIC}")
    print(f"  n_q      : {NUM_QUESTIONS} questions per chunk")
    print(f"  delay    : {DELAY_SEC}s between calls")
    print("=" * 60)

    results = []

    for i, obj in enumerate(data):
        content = obj.get("content", "").strip()
        if not content:
            print(f"\n[{i + 1:>3}/{total}]  SKIP – empty content")
            results.append({"index": i, "skipped": True})
            continue

        result = upload_chunk(i, total, content)
        results.append({"index": i, "chunk_id": result.get("chunk_id"), "result": result})

        # Wait between calls (skip wait after last item)
        if i < total - 1:
            print(f"  Sleeping {DELAY_SEC}s ...")
            time.sleep(DELAY_SEC)

    # ── Summary ─────────────────────────────────────────────────────────────
    success = sum(1 for r in results if "error" not in r.get("result", {}))
    print("\n" + "=" * 60)
    print(f"  Done!  Successful: {success}/{total}")
    print("=" * 60)

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Results saved → {RESULT_FILE}")


if __name__ == "__main__":
    main()
