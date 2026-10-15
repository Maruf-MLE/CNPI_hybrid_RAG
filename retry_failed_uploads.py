"""
retry_failed_uploads.py
-----------------------
Retries only the failed uploads from upload_results.json using the
renamed file: class_routine_2nd_shift.json
"""

import json
import time
import uuid
import requests

# ── Config ───────────────────────────────────────────────────────────────────
BASE_URL       = "https://cnpi-hybrid-rag-1.onrender.com"
API_ENDPOINT   = f"{BASE_URL}/admin-panel/api/create/"
JSON_FILE      = r"G:\CNPI_Hybrid_RAG\cnpi_api\Document\class_routine_2nd_shift.json"
RESULTS_FILE   = r"G:\CNPI_Hybrid_RAG\upload_results.json"
RETRY_OUTPUT   = r"G:\CNPI_Hybrid_RAG\retry_results.json"

DOC_TYPE       = "documents"
NUM_QUESTIONS  = 7
TOPIC          = "class routine"
DELAY_SEC      = 15          # seconds between consecutive API calls
REQUEST_TIMEOUT = 120        # seconds to wait for a single response
# ─────────────────────────────────────────────────────────────────────────────


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def upload_chunk(index: int, content: str) -> dict:
    """POST one chunk to the create endpoint. Returns parsed response dict."""
    chunk_id = f"class_routine_{uuid.uuid4().hex[:12]}"

    payload = {
        "chunk_id":      chunk_id,
        "content":       content,
        "doc_type":      DOC_TYPE,
        "num_questions": NUM_QUESTIONS,
        "topic":         TOPIC,
        "source_file":   "class_routine_2nd_shift.json",
    }

    print(f"\n[Retry index {index}]  chunk_id = {chunk_id}")
    print(f"             content  = {content[:100].strip()!r}...")

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
    # Load original data and previous results
    source_data = load_json(JSON_FILE)
    prev_results = load_json(RESULTS_FILE)

    # Find failed indices
    failed_entries = [
        r for r in prev_results
        if "error" in r.get("result", {})
    ]

    failed_indices = [entry["index"] for entry in failed_entries]

    print("=" * 60)
    print(f"  Source file  : {JSON_FILE}")
    print(f"  Results file : {RESULTS_FILE}")
    print(f"  Endpoint     : {API_ENDPOINT}")
    print(f"  Total failed : {len(failed_indices)} out of {len(prev_results)}")
    print(f"  Retry delay  : {DELAY_SEC}s")
    print("=" * 60)

    if not failed_indices:
        print("\n  No failed entries to retry. All done!")
        return

    print(f"\n  Failed indices: {failed_indices[:10]}{'...' if len(failed_indices) > 10 else ''}")

    retry_results = []

    for i, idx in enumerate(failed_indices):
        obj = source_data[idx]
        content = obj.get("content", "").strip()

        if not content:
            print(f"\n[{i + 1}/{len(failed_indices)}] Index {idx}: SKIP – empty content")
            retry_results.append({"index": idx, "skipped": True})
            continue

        result = upload_chunk(idx, content)
        retry_results.append({
            "index": idx,
            "chunk_id": result.get("chunk_id"),
            "result": result
        })

        # Wait between calls (skip wait after last item)
        if i < len(failed_indices) - 1:
            print(f"  Sleeping {DELAY_SEC}s ...")
            time.sleep(DELAY_SEC)

    # ── Summary ─────────────────────────────────────────────────────────────
    success = sum(1 for r in retry_results if "error" not in r.get("result", {}))
    print("\n" + "=" * 60)
    print(f"  Done!  Successful: {success}/{len(failed_indices)}")
    print("=" * 60)

    with open(RETRY_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(retry_results, f, ensure_ascii=False, indent=2)
    print(f"  Retry results saved → {RETRY_OUTPUT}")


if __name__ == "__main__":
    main()
