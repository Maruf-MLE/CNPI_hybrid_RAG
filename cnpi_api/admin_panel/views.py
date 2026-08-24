from __future__ import annotations

import os
import json
import logging

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import services

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_error(message: str, status: int = 400, **extra) -> JsonResponse:
    payload = {"error": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def _read_json_body(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}


def _is_logged_in(request: HttpRequest) -> bool:
    return request.session.get("admin_logged_in") is True


@csrf_exempt
@api_view(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        data = _read_json_body(request)
        entered = (data.get("password") or request.POST.get("password", "")).strip()
        correct = os.getenv("ADMIN_PANEL_PASSWORD", "").strip()
        if not correct:
            return JsonResponse({"success": False, "error": "ADMIN_PANEL_PASSWORD .env তে সেট নেই।"}, status=500)
        if entered == correct:
            request.session["admin_logged_in"] = True
            request.session.set_expiry(60 * 60 * 8)
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "error": "ভুল পাসওয়ার্ড।"}, status=401)
    return HttpResponse(_LOGIN_PAGE, content_type="text/html; charset=utf-8")


@api_view(["GET"])
def logout_view(request: HttpRequest) -> HttpResponse:
    request.session.flush()
    return redirect("/admin-panel/login/")


@api_view(["GET"])
def index_view(request: HttpRequest) -> HttpResponse:
    if not _is_logged_in(request):
        return redirect("/admin-panel/login/")
    return HttpResponse(_HTML_PAGE, content_type="text/html; charset=utf-8")


# ---------------------------------------------------------------------------
# API: search
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["POST", "GET"])
def search_view(request: HttpRequest) -> JsonResponse:
    """Semantic search: embed the question, return top-k document chunks.

    Accepts JSON body: {"query": "...", "top_k": 5}
    Also accepts query params for GET: ?query=...&top_k=5
    """
    if request.method == "GET":
        query = request.GET.get("query", "").strip()
        try:
            top_k = int(request.GET.get("top_k", "5"))
        except ValueError:
            top_k = 5
    else:
        data = _read_json_body(request)
        query = str(data.get("query", "")).strip()
        try:
            top_k = int(data.get("top_k", 5))
        except (TypeError, ValueError):
            top_k = 5

    if not query:
        return _json_error("query is required.", query=query)

    try:
        results = services.semantic_search(query, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        logger.exception("semantic_search failed")
        return _json_error(f"Search failed: {exc}", status=500, query=query)

    return JsonResponse({"query": query, "count": len(results), "results": results})


# ---------------------------------------------------------------------------
# API: get a single document
# ---------------------------------------------------------------------------

@api_view(["GET"])
def document_view(request: HttpRequest) -> JsonResponse:
    """Fetch one document by doc_id or chunk_id."""
    doc_id = request.GET.get("doc_id", "").strip()
    chunk_id = request.GET.get("chunk_id", "").strip()

    if not doc_id and not chunk_id:
        return _json_error("Provide doc_id or chunk_id as a query parameter.")

    try:
        doc = services.get_document(doc_id=doc_id or None, chunk_id=chunk_id or None)
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_document failed")
        return _json_error(f"Fetch failed: {exc}", status=500)

    if doc is None:
        return _json_error("Document not found.", status=404)

    return JsonResponse({"document": doc})


# ---------------------------------------------------------------------------
# API: update
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["POST"])
def update_view(request: HttpRequest) -> JsonResponse:
    """Update a document row and regenerate its embedding.

    JSON body:
        {
            "doc_id": 12,            // OR "chunk_id": "teachers_cst_1"
            "content": "new text...",
            "doc_type": "teachers_info",   // optional
            "topic": "...",                // optional
            "department": "CST",           // optional
            "regenerate_embedding": true   // optional, default true
        }
    """
    data = _read_json_body(request)
    if not data:
        return _json_error("Expected a JSON body.")

    doc_id = data.get("doc_id")
    chunk_id = data.get("chunk_id")
    content = data.get("content")
    doc_type = data.get("doc_type")
    topic = data.get("topic")
    department = data.get("department")
    regenerate = data.get("regenerate_embedding", True)
    if isinstance(regenerate, str):
        regenerate = regenerate.lower() in ("true", "1", "yes")

    try:
        result = services.update_document(
            doc_id=doc_id,
            chunk_id=chunk_id,
            content=content,
            doc_type=doc_type,
            topic=topic,
            department=department,
            regenerate_embedding=bool(regenerate),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("update_document failed")
        return _json_error(f"Update failed: {exc}", status=500)

    if "error" in result:
        return _json_error(result["error"])

    return JsonResponse(result)


# ---------------------------------------------------------------------------
# API: create (add a brand-new document)
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["POST"])
def create_view(request: HttpRequest) -> JsonResponse:
    """Insert a new document row with an auto-generated embedding.

    JSON body:
        {
            "chunk_id": "manual_cst_1",   // required, must be unique
            "content": "text...",          // required, >= 11 chars
            "doc_type": "general",         // optional, default "general"
            "topic": "...",                // optional
            "department": "CST",           // optional
            "meta": {"key": "val"},        // optional, dict or JSON string
            "source_file": "admin_panel"   // optional
        }
    """
    data = _read_json_body(request)
    if not data:
        return _json_error("Expected a JSON body.")

    chunk_id = data.get("chunk_id")
    content = data.get("content")
    doc_type = data.get("doc_type", "general")
    topic = data.get("topic")
    department = data.get("department")
    meta = data.get("meta")
    source_file = data.get("source_file", "admin_panel")

    try:
        result = services.create_document(
            chunk_id=chunk_id,
            content=content,
            doc_type=doc_type,
            topic=topic,
            department=department,
            meta=meta,
            source_file=source_file,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_document failed")
        return _json_error(f"Create failed: {exc}", status=500)

    if "error" in result:
        return _json_error(result["error"])

    return JsonResponse(result, status=201)


# ---------------------------------------------------------------------------
# API: stats
# ---------------------------------------------------------------------------

@api_view(["GET"])
def stats_view(request: HttpRequest) -> JsonResponse:
    """Return document counts for the dashboard."""
    try:
        stats = services.document_stats()
    except Exception as exc:  # noqa: BLE001
        logger.exception("document_stats failed")
        return _json_error(f"Stats failed: {exc}", status=500)
    return JsonResponse(stats)


# ---------------------------------------------------------------------------
# API: captains — list
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["GET", "POST"])
def captains_list_view(request: HttpRequest) -> JsonResponse:
    """List captains with optional filters.

    GET params: department, shift, semester, captain_rank, active_only (default true)
    """
    if request.method == "POST":
        data = _read_json_body(request)
    else:
        data = request.GET

    department = (data.get("department") or "").strip() or None
    shift = (data.get("shift") or "").strip() or None
    semester_raw = data.get("semester")
    rank_raw = data.get("captain_rank")
    active_only_raw = data.get("active_only", "true")

    semester = None
    if semester_raw:
        try:
            semester = int(semester_raw)
        except ValueError:
            return _json_error("semester must be an integer.")

    captain_rank = None
    if rank_raw:
        try:
            captain_rank = int(rank_raw)
        except ValueError:
            return _json_error("captain_rank must be 1 or 2.")

    active_only = str(active_only_raw).lower() not in ("false", "0", "no")

    try:
        captains = services.list_captains(
            department=department,
            shift=shift,
            semester=semester,
            captain_rank=captain_rank,
            active_only=active_only,
        )
    except Exception as exc:
        logger.exception("list_captains failed")
        return _json_error(f"List failed: {exc}", status=500)

    # Serialize datetime fields
    for c in captains:
        for k in ("created_at", "updated_at"):
            if c.get(k) and hasattr(c[k], "isoformat"):
                c[k] = c[k].isoformat()

    return JsonResponse({"count": len(captains), "captains": captains})


# ---------------------------------------------------------------------------
# API: captains — create
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["POST"])
def captain_create_view(request: HttpRequest) -> JsonResponse:
    """Create a new captain.

    JSON body:
        {
            "department": "CST",    // required
            "shift": "Day",         // required: "Day" or "Morning"
            "semester": 5,          // required: 1–7
            "captain_rank": 1,      // required: 1 (1st Captain) or 2 (2nd Captain)
            "captain_name": "...",  // required
            "student_id": "...",    // optional
            "phone": "01...",       // optional
            "email": "...",         // optional
            "session_year": "2024-25" // optional
        }
    """
    data = _read_json_body(request)
    if not data:
        return _json_error("Expected a JSON body.")

    try:
        result = services.create_captain(
            department=data.get("department", ""),
            shift=data.get("shift", ""),
            semester=data.get("semester"),
            captain_rank=data.get("captain_rank", 1),
            captain_name=data.get("captain_name", ""),
            student_id=data.get("student_id"),
            phone=data.get("phone"),
            email=data.get("email"),
            session_year=data.get("session_year"),
        )
    except Exception as exc:
        logger.exception("create_captain failed")
        return _json_error(f"Create failed: {exc}", status=500)

    if "error" in result:
        return _json_error(result["error"])

    # Serialize datetime
    if result.get("captain"):
        for k in ("created_at", "updated_at"):
            if result["captain"].get(k) and hasattr(result["captain"][k], "isoformat"):
                result["captain"][k] = result["captain"][k].isoformat()

    return JsonResponse(result, status=201)


# ---------------------------------------------------------------------------
# API: captains — update
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["POST"])
def captain_update_view(request: HttpRequest) -> JsonResponse:
    """Update editable fields of a captain.

    JSON body: { "captain_id": 3, "phone": "...", "captain_name": "...", ... }
    """
    data = _read_json_body(request)
    if not data:
        return _json_error("Expected a JSON body.")

    captain_id = data.get("captain_id")
    if captain_id is None:
        return _json_error("captain_id is required.")
    try:
        captain_id = int(captain_id)
    except (TypeError, ValueError):
        return _json_error("captain_id must be an integer.")

    try:
        result = services.update_captain(
            captain_id=captain_id,
            captain_name=data.get("captain_name"),
            student_id=data.get("student_id"),
            phone=data.get("phone"),
            email=data.get("email"),
            session_year=data.get("session_year"),
        )
    except Exception as exc:
        logger.exception("update_captain failed")
        return _json_error(f"Update failed: {exc}", status=500)

    if "error" in result:
        return _json_error(result["error"])

    if result.get("captain"):
        for k in ("created_at", "updated_at"):
            if result["captain"].get(k) and hasattr(result["captain"][k], "isoformat"):
                result["captain"][k] = result["captain"][k].isoformat()

    return JsonResponse(result)


# ---------------------------------------------------------------------------
# API: captains — deactivate
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["POST"])
def captain_deactivate_view(request: HttpRequest) -> JsonResponse:
    """Deactivate a captain (set is_active=FALSE).

    JSON body: { "captain_id": 3 }
    """
    data = _read_json_body(request)
    captain_id = data.get("captain_id")
    if captain_id is None:
        return _json_error("captain_id is required.")
    try:
        captain_id = int(captain_id)
    except (TypeError, ValueError):
        return _json_error("captain_id must be an integer.")

    try:
        result = services.deactivate_captain(captain_id=captain_id)
    except Exception as exc:
        logger.exception("deactivate_captain failed")
        return _json_error(f"Deactivate failed: {exc}", status=500)

    if "error" in result:
        return _json_error(result["error"])

    return JsonResponse(result)


# ---------------------------------------------------------------------------
# API: captains — stats
# ---------------------------------------------------------------------------

@api_view(["GET"])
def captain_stats_view(request: HttpRequest) -> JsonResponse:
    """Return captain counts grouped by department and shift."""
    try:
        stats = services.captain_stats()
    except Exception as exc:
        logger.exception("captain_stats failed")
        return _json_error(f"Stats failed: {exc}", status=500)
    return JsonResponse(stats)


# ---------------------------------------------------------------------------
# The admin panel HTML page (self-contained, no external build step)
# ---------------------------------------------------------------------------

_HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CNPI RAG â€” Admin Panel</title>
<style>
  :root{
    --bg:#0f172a; --panel:#1e293b; --panel2:#273449; --border:#334155;
    --text:#e2e8f0; --muted:#94a3b8; --accent:#38bdf8; --accent2:#818cf8;
    --ok:#22c55e; --warn:#f59e0b; --err:#ef4444;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--text)}
  header{display:flex;align-items:center;gap:14px;padding:14px 20px;border-bottom:1px solid var(--border);background:var(--panel)}
  header h1{font-size:18px;margin:0;font-weight:600}
  header .badge{font-size:12px;color:var(--muted);background:var(--panel2);padding:3px 8px;border-radius:6px;border:1px solid var(--border)}
  #stats{display:flex;gap:10px;margin-left:auto;font-size:13px;color:var(--muted)}
  #stats b{color:var(--text)}
  .layout{display:grid;grid-template-columns:1.1fr 1fr;gap:16px;padding:16px;height:calc(100vh - 58px)}
  .pane{background:var(--panel);border:1px solid var(--border);border-radius:12px;display:flex;flex-direction:column;overflow:hidden}
  .pane h2{font-size:15px;margin:0;padding:12px 16px;border-bottom:1px solid var(--border);background:var(--panel2);display:flex;align-items:center;gap:8px}
  .tabs{display:flex;border-bottom:1px solid var(--border);background:var(--panel2)}
  .tab{flex:1;padding:10px;border:0;background:transparent;color:var(--muted);font-size:14px;font-weight:600;cursor:pointer;border-bottom:2px solid transparent}
  .tab.active{color:var(--text);border-bottom-color:var(--accent)}
  .tabpane{flex:1;overflow:auto;display:flex;flex-direction:column}
  .pane .body{padding:16px;overflow:auto}
  .row{display:flex;gap:10px;margin-bottom:12px}
  input,textarea,select{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:9px 11px;font-size:14px;font-family:inherit}
  textarea{min-height:120px;resize:vertical;font-family:var(--mono);font-size:13px}
  input:focus,textarea:focus,select:focus{outline:none;border-color:var(--accent)}
  button{cursor:pointer;border:0;border-radius:8px;padding:9px 16px;font-size:14px;font-weight:600;background:var(--accent);color:#0b1220}
  button.secondary{background:var(--panel2);color:var(--text);border:1px solid var(--border)}
  button:disabled{opacity:.5;cursor:wait}
  .hint{font-size:12px;color:var(--muted);margin-top:-6px;margin-bottom:10px}
  .result{background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:12px;margin-bottom:10px;cursor:pointer;transition:border-color .15s}
  .result:hover{border-color:var(--accent)}
  .result.active{border-color:var(--accent2);box-shadow:0 0 0 2px rgba(129,140,248,.25)}
  .result .top{display:flex;justify-content:space-between;gap:8px;font-size:12px;color:var(--muted);margin-bottom:6px}
  .result .ids{font-family:var(--mono);color:var(--text)}
  .result .score{color:var(--accent);font-weight:600}
  .result .content{font-size:13px;line-height:1.5;white-space:pre-wrap;word-break:break-word;max-height:120px;overflow:auto;font-family:var(--mono)}
  .result .tags{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
  .tag{font-size:11px;background:var(--bg);border:1px solid var(--border);padding:2px 7px;border-radius:6px;color:var(--muted)}
  .meta{font-size:11px;color:var(--muted);font-family:var(--mono);margin-top:6px;white-space:pre-wrap;word-break:break-word}
  .field label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px;font-weight:600}
  .field{margin-bottom:12px}
  .two{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  #toast{position:fixed;bottom:18px;right:18px;z-index:50;display:flex;flex-direction:column;gap:8px}
  .toast{padding:10px 14px;border-radius:8px;font-size:13px;max-width:360px;box-shadow:0 6px 20px rgba(0,0,0,.4)}
  .toast.ok{background:#064e3b;color:#bbf7d0;border:1px solid #10b981}
  .toast.err{background:#450a0a;color:#fecaca;border:1px solid #ef4444}
  .toast.info{background:#0c4a6e;color:#bae6fd;border:1px solid #0ea5e9}
  .loader{display:inline-block;width:14px;height:14px;border:2px solid var(--muted);border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite;vertical-align:-2px;margin-right:6px}
  @keyframes spin{to{transform:rotate(360deg)}}
  .empty{color:var(--muted);text-align:center;padding:30px;font-size:13px}
  .before-after{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
  .ba-box{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;font-size:12px;font-family:var(--mono);white-space:pre-wrap;word-break:break-word;max-height:160px;overflow:auto}
  .ba-box h4{margin:0 0 6px;font-size:11px;color:var(--muted);font-family:inherit;text-transform:uppercase}
  details{margin-top:10px}
  summary{cursor:pointer;font-size:12px;color:var(--muted)}
</style>
</head>
<body>
<header>
  <h1>CNPI RAG â€” Admin Panel</h1>
  <span class="badge">documents table</span>
  <div id="stats"></div>
</header>

<div class="layout">
  <!-- LEFT: search -->
  <section class="pane">
    <h2>ðŸ” Semantic Search</h2>
    <div class="body">
      <div class="row">
        <input id="query" type="text" placeholder="Ask a question / search contentâ€¦" />
        <select id="topk" style="width:90px">
          <option>5</option><option>10</option><option>15</option><option>20</option>
        </select>
        <button id="searchBtn">Search</button>
      </div>
      <div class="hint">Embeds your question and finds the closest document chunks by cosine similarity (pgvector).</div>
      <div id="results"><div class="empty">Results will appear here.</div></div>
    </div>
  </section>

  <!-- RIGHT: update / add tabs -->
  <section class="pane">
    <div class="tabs">
      <button class="tab active" data-tab="update">âœï¸ Update</button>
      <button class="tab" data-tab="add">âž• Add New</button>
    </div>

    <!-- TAB: update -->
    <div class="tabpane" id="tab-update">
      <div class="body">
        <div class="row">
          <input id="lookupKey" type="text" placeholder="doc_id or chunk_id" />
          <button id="loadBtn" class="secondary">Load</button>
        </div>
        <div class="hint">Enter a doc_id (number) or chunk_id (string) to load the current row, then edit &amp; save.</div>

        <div class="field">
          <label>Content <span style="color:var(--muted)">(min 11 chars â€” embedding regenerated on save)</span></label>
          <textarea id="content" placeholder="Document contentâ€¦"></textarea>
        </div>
        <div class="two">
          <div class="field"><label>doc_type</label><input id="docType" type="text" placeholder="general" /></div>
          <div class="field"><label>department</label>
            <select id="department">
              <option value="">(none)</option>
              <option>CST</option><option>ET</option><option>ENT</option><option>RAC</option>
              <option>FT</option><option>MT</option><option>Non-Tech</option><option>General</option>
            </select>
          </div>
        </div>
        <div class="field"><label>topic</label><input id="topic" type="text" placeholder="topic" /></div>

        <div class="row" style="align-items:center">
          <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--muted)">
            <input id="regen" type="checkbox" checked style="width:auto" /> Regenerate embedding
          </label>
          <div style="margin-left:auto;display:flex;gap:8px">
            <button id="clearBtn" class="secondary">Clear</button>
            <button id="saveBtn">Update Row</button>
          </div>
        </div>
        <div id="updateResult"></div>
      </div>
    </div>

    <!-- TAB: add -->
    <div class="tabpane" id="tab-add" style="display:none">
      <div class="body">
        <div class="field" id="chunkIdField">
          <label>chunk_id <span style="color:var(--warn)" id="chunkIdLabel">(required, must be unique)</span></label>
          <input id="newChunkId" type="text" placeholder="e.g. manual_cst_1" />
          <div id="chunkIdAutoInfo" style="display:none;color:var(--ok);font-size:0.85em;margin-top:4px">&#10003; Auto-generated: <b>notice-{ID}</b> (assigned after save)</div>
        </div>
        <div class="field">
          <label>Content <span style="color:var(--muted)">(min 11 chars â€" Bengali auto-translated → English + entity normalised + date/time stamp added)</span></label>
          <textarea id="newContent" placeholder="New document contentâ€¦"></textarea>
        </div>
        <div class="two">
          <div class="field"><label>doc_type (Table Name)</label>
            <select id="newDocType" onchange="onDocTypeChange(this.value)">
              <option value="documents">documents (default)</option>
              <option value="notices">notices</option>
              <option value="buildings">buildings</option>
              <option value="departments">departments</option>
              <option value="designations">designations</option>
              <option value="exam_routines">exam_routines</option>
              <option value="facilities">facilities</option>
              <option value="future_plans">future_plans</option>
              <option value="institutions">institutions</option>
              <option value="lab_assignments">lab_assignments</option>
              <option value="labs">labs</option>
              <option value="people">people</option>
              <option value="rooms">rooms</option>
              <option value="routine_classes">routine_classes</option>
              <option value="routines">routines</option>
              <option value="subjects">subjects</option>
            </select>
          </div>
          <div class="field"><label>department</label>
            <select id="newDepartment">
              <option value="">(none)</option>
              <option>CST</option><option>ET</option><option>ENT</option><option>RAC</option>
              <option>FT</option><option>MT</option><option>Non-Tech</option><option>General</option>
            </select>
          </div>
        </div>
        <div class="field"><label>topic</label><input id="newTopic" type="text" placeholder="topic" /></div>
        <div class="field">
          <label>meta <span style="color:var(--muted)">(JSON, optional)</span></label>
          <input id="newMeta" type="text" placeholder='{"key":"value"}' />
        </div>
        <div class="row" style="justify-content:flex-end">
          <button id="addClearBtn" class="secondary">Clear</button>
          <button id="addBtn">Create Document</button>
        </div>
        <div id="addResult"></div>
      </div>
    </div>
  </section>
</div>

<div id="toast"></div>

<script>
const $ = (id) => document.getElementById(id);
const API = window.location.pathname.replace(/\/$/, "");
const j = (url, opts) => fetch(url, opts).then(r => r.json().then(d => ({ok:r.ok, d})));

function toast(msg, kind="info"){
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.textContent = msg;
  $("toast").appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function setLoading(btn, on){
  btn.disabled = on;
  if(on && !btn.dataset.label) btn.dataset.label = btn.textContent;
  btn.textContent = on ? "â€¦" : (btn.dataset.label || btn.textContent);
}

// ---- stats ----
async function loadStats(){
  try{
    const {ok,d} = await j(`${API}/api/stats/`);
    if(!ok) return;
    $("stats").innerHTML = `<span>Total: <b>${d.total}</b></span>` +
      (d.by_doc_type||[]).slice(0,3).map(t=>`<span>${t.doc_type}: <b>${t.cnt}</b></span>`).join("");
  }catch(e){}
}

// ---- search ----
let lastResults = [];
async function doSearch(){
  const query = $("query").value.trim();
  if(!query) return toast("Enter a search query.", "err");
  const btn = $("searchBtn"); setLoading(btn,true);
  try{
    const {ok,d} = await j(`${API}/api/search/`, {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({query, top_k: parseInt($("topk").value,10)||5})});
    if(!ok) return toast(d.error||"Search failed", "err");
    lastResults = d.results||[];
    renderResults();
  }catch(e){ toast("Network error: "+e, "err"); }
  finally{ setLoading(btn,false); }
}

function renderResults(){
  const box = $("results");
  if(!lastResults.length){ box.innerHTML = `<div class="empty">No results.</div>`; return; }
  box.innerHTML = lastResults.map((r,i)=>{
    const meta = r.meta ? (typeof r.meta==="string"?JSON.parse(r.meta||"{}"):r.meta) : {};
    const metaStr = Object.keys(meta).length ? JSON.stringify(meta,null,2) : "";
    return `<div class="result" data-i="${i}">
      <div class="top">
        <span class="ids">doc_id: ${r.doc_id} Â· chunk_id: <b>${r.chunk_id}</b></span>
        <span class="score">score: ${(r.score||0).toFixed(4)}</span>
      </div>
      <div class="content">${esc(r.content||"")}</div>
      <div class="tags">
        ${r.doc_type?`<span class="tag">type: ${esc(r.doc_type)}</span>`:""}
        ${r.department?`<span class="tag">dept: ${esc(r.department)}</span>`:""}
        ${r.topic?`<span class="tag">topic: ${esc(r.topic)}</span>`:""}
      </div>
      ${metaStr?`<details><summary>meta</summary><div class="meta">${esc(metaStr)}</div></details>`:""}
    </div>`;
  }).join("");
  box.querySelectorAll(".result").forEach(el=>{
    el.onclick = () => selectResult(parseInt(el.dataset.i,10));
  });
}

function selectResult(i){
  document.querySelectorAll(".result").forEach(e=>e.classList.remove("active"));
  const el = document.querySelector(`.result[data-i="${i}"]`);
  if(el) el.classList.add("active");
  const r = lastResults[i]; if(!r) return;
  $("lookupKey").value = r.chunk_id;
  loadDoc();
}

// ---- load single doc ----
async function loadDoc(){
  const key = $("lookupKey").value.trim();
  if(!key) return toast("Enter doc_id or chunk_id.", "err");
  const isNum = /^\d+$/.test(key);
  const qs = isNum ? `doc_id=${encodeURIComponent(key)}` : `chunk_id=${encodeURIComponent(key)}`;
  try{
    const {ok,d} = await j(`${API}/api/document/?${qs}`);
    if(!ok) return toast(d.error||"Not found", "err");
    const doc = d.document;
    $("content").value = doc.content||"";
    $("docType").value = doc.doc_type||"";
    $("department").value = doc.department||"";
    $("topic").value = doc.topic||"";
    toast("Loaded "+(isNum?`doc_id=${doc.doc_id}`:`chunk_id=${doc.chunk_id}`), "info");
  }catch(e){ toast("Network error: "+e, "err"); }
}

// ---- update ----
async function doUpdate(){
  const key = $("lookupKey").value.trim();
  if(!key) return toast("Enter doc_id or chunk_id first.", "err");
  const content = $("content").value.trim();
  if(content.length < 11) return toast("Content must be at least 11 characters.", "err");
  const isNum = /^\d+$/.test(key);
  const body = {
    content,
    doc_type: $("docType").value.trim() || null,
    topic: $("topic").value.trim() || null,
    department: $("department").value || null,
    regenerate_embedding: $("regen").checked,
  };
  if(isNum) body.doc_id = parseInt(key,10); else body.chunk_id = key;

  const btn = $("saveBtn"); setLoading(btn,true);
  $("updateResult").innerHTML = "";
  try{
    const {ok,d} = await j(`${API}/api/update/`, {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(body)});
    if(!ok) return toast(d.error||"Update failed", "err");
    toast(`Updated ${d.embedding_regenerated?"(embedding regenerated)":""}`, "ok");
    renderUpdateResult(d);
  }catch(e){ toast("Network error: "+e, "err"); }
  finally{ setLoading(btn,false); }
}

function renderUpdateResult(d){
  const fmt = (doc)=> doc ? `doc_id: ${doc.doc_id}\nchunk_id: ${doc.chunk_id}\ndoc_type: ${doc.doc_type}\ndepartment: ${doc.department}\ntopic: ${doc.topic}\n\n${doc.content}` : "(none)";
  $("updateResult").innerHTML = `
    <div class="before-after">
      <div class="ba-box"><h4>Before</h4>${esc(fmt(d.before))}</div>
      <div class="ba-box"><h4>After</h4>${esc(fmt(d.after))}</div>
    </div>`;
}

// ---- doc_type change handler ----
function onDocTypeChange(val){
  const isNotice = val === "notices";
  const chunkInput = $("newChunkId");
  const autoInfo = $("chunkIdAutoInfo");
  const chunkLabel = $("chunkIdLabel");
  if(isNotice){
    chunkInput.value = "";
    chunkInput.disabled = true;
    chunkInput.style.opacity = "0.4";
    chunkInput.placeholder = "Auto-generated (notice-ID)";
    autoInfo.style.display = "block";
    chunkLabel.textContent = "(auto-generated for notices)";
    chunkLabel.style.color = "var(--ok)";
  } else {
    chunkInput.disabled = false;
    chunkInput.style.opacity = "1";
    chunkInput.placeholder = "e.g. manual_cst_1";
    autoInfo.style.display = "none";
    chunkLabel.textContent = "(required, must be unique)";
    chunkLabel.style.color = "var(--warn)";
  }
}

// ---- create (add new) ----
async function doCreate(){
  const docType = $("newDocType").value || "documents";
  const isNotice = docType === "notices";
  const chunk_id = isNotice ? "" : $("newChunkId").value.trim();
  if(!isNotice && !chunk_id) return toast("chunk_id is required.", "err");
  const content = $("newContent").value.trim();
  if(content.length < 11) return toast("Content must be at least 11 characters.", "err");
    const body = {
      chunk_id,
      content,
      doc_type: docType,
      topic: $("newTopic").value.trim() || null,
      department: $("newDepartment").value || null,
      meta: $("newMeta").value.trim() || null,
      source_file: "admin_panel",
    };
  const btn = $("addBtn"); setLoading(btn,true);
  $("addResult").innerHTML = '<div class="empty"><span class="loader"></span>Translating &amp; processing\u2026 (this may take a few seconds)</div>';
  try{
    const {ok,d} = await j(`${API}/api/create/`, {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(body)});
    if(!ok) return toast(d.error||"Create failed", "err");
    const xlat = d.translation_performed ? " · translated Bengali→English" : "";
    const dateInfo = d.context_added_date ? ` · ${d.context_added_date} ${d.context_added_time} BST` : "";
    const noticeInfo = d.inserted_into_notices ? ` · notice_id=${d.notice_id}` : "";
    toast(`Created doc_id=${d.doc_id}${xlat}${dateInfo}${noticeInfo}`, "ok");
    const xlBadge = d.translation_performed
      ? `<span class="tag" style="color:var(--ok);border-color:var(--ok)">translated Bengali→EN</span>`
      : `<span class="tag">no translation needed</span>`;
    const dateBadge = d.context_added_date
      ? `<span class="tag">added: ${esc(d.context_added_date)} ${esc(d.context_added_time)} BST</span>`
      : "";
    const noticeBadge = d.inserted_into_notices
      ? `<span class="tag" style="color:var(--accent);border-color:var(--accent)">✓ inserted into notices table (notice_id: ${d.notice_id})</span>`
      : "";
    $("addResult").innerHTML = `<div class="result active"><div class="top"><span class="ids">doc_id: ${d.doc_id} · chunk_id: <b>${d.chunk_id}</b></span><span class="score">✔ created</span></div><div class="content">${esc(d.document?.content||"")}</div><div class="tags">${xlBadge}${dateBadge}${noticeBadge}</div></div>`;
    loadStats();
  }catch(e){ toast("Network error: "+e, "err"); }
  finally{ setLoading(btn,false); }
}

// ---- tabs ----
function switchTab(name){
  document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("active", t.dataset.tab===name));
  document.querySelectorAll(".tabpane").forEach(p=>p.style.display = p.id===`tab-${name}`?"flex":"none");
}

function esc(s){ return (s==null?"":String(s)).replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }

// ---- events ----
$("searchBtn").onclick = doSearch;
$("query").addEventListener("keydown", e=>{ if(e.key==="Enter") doSearch(); });
$("loadBtn").onclick = loadDoc;
$("lookupKey").addEventListener("keydown", e=>{ if(e.key==="Enter") loadDoc(); });
$("saveBtn").onclick = doUpdate;
$("clearBtn").onclick = ()=>{ ["lookupKey","content","docType","topic","department"].forEach(id=>$(id).value=""); $("updateResult").innerHTML=""; };
$("addBtn").onclick = doCreate;
$("addClearBtn").onclick = ()=>{ ["newChunkId","newContent","newDocType","newTopic","newDepartment","newMeta"].forEach(id=>$(id).value=""); $("addResult").innerHTML=""; };
document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>switchTab(t.dataset.tab));

loadStats();
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Login page HTML
# ---------------------------------------------------------------------------

_LOGIN_PAGE = """<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login â€” CNPI RAG</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{min-height:100vh;display:flex;align-items:center;justify-content:center;
       background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 100%);font-family:system-ui,sans-serif}
  .card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:40px;width:100%;max-width:400px;box-shadow:0 25px 50px rgba(0,0,0,.5)}
  h1{color:#f1f5f9;font-size:22px;font-weight:700;margin-bottom:6px;text-align:center}
  .sub{color:#94a3b8;font-size:14px;text-align:center;margin-bottom:28px}
  label{display:block;font-size:13px;color:#94a3b8;font-weight:600;margin-bottom:6px}
  input{width:100%;padding:11px 14px;background:#0f172a;color:#f1f5f9;border:1px solid #334155;
        border-radius:8px;font-size:15px;margin-bottom:18px}
  input:focus{outline:none;border-color:#38bdf8}
  button{width:100%;padding:12px;background:#38bdf8;color:#0b1220;border:none;border-radius:8px;
         font-size:15px;font-weight:700;cursor:pointer}
  button:hover{background:#7dd3fc}
  button:disabled{opacity:.5;cursor:wait}
  .err{background:#450a0a;color:#fca5a5;border:1px solid #ef4444;border-radius:8px;
       padding:10px 14px;font-size:13px;margin-bottom:16px;display:none}
</style>
</head>
<body>
<div class="card">
  <h1>ðŸ”’ CNPI Admin Panel</h1>
  <p class="sub">Password à¦¦à¦¿à¦¯à¦¼à§‡ à¦²à¦—à¦‡à¦¨ à¦•à¦°à§à¦¨</p>
  <div class="err" id="err">__ERROR__</div>
  <form id="form">
    <label for="pw">Password</label>
    <input type="password" id="pw" placeholder="Enter password" required autofocus>
    <button type="submit" id="btn">Login</button>
  </form>
</div>
<script>
  const err = document.getElementById('err');
  if(err.textContent.trim()) err.style.display='block';

  document.getElementById('form').addEventListener('submit', async function(e){
    e.preventDefault();
    const pw = document.getElementById('pw').value;
    const btn = document.getElementById('btn');
    err.style.display='none';
    btn.disabled=true; btn.textContent='...';
    try{
      const r = await fetch('/admin-panel/login/', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({password: pw})
      });
      const d = await r.json();
      if(d.success){ window.location.href='/admin-panel/'; }
      else{ err.textContent = d.error || 'à¦­à§à¦² à¦ªà¦¾à¦¸à¦“à¦¯à¦¼à¦¾à¦°à§à¦¡'; err.style.display='block'; }
    }catch(e){ err.textContent='Network error'; err.style.display='block'; }
    finally{ btn.disabled=false; btn.textContent='Login'; }
  });
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# API: Priority Documents
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["GET"])
def priority_docs_list_view(request: HttpRequest) -> JsonResponse:
    """
    Get list of all priority documents.
    Query params:
        - active_only: true/false (default: true)
    """
    active_only = request.GET.get("active_only", "true").lower() == "true"
    
    try:
        priority_docs = services.get_priority_documents(active_only=active_only)
        return JsonResponse({
            "success": True,
            "count": len(priority_docs),
            "priority_documents": priority_docs
        })
    except Exception as e:
        logger.exception("Error fetching priority documents")
        return _json_error(str(e), status=500)


@csrf_exempt
@api_view(["POST"])
def priority_docs_add_view(request: HttpRequest) -> JsonResponse:
    """
    Add a document to priority list.
    JSON body:
        - doc_id: int (required)
        - priority_order: int (optional, default: 0)
        - reason: str (optional)
    """
    data = _read_json_body(request)
    doc_id = data.get("doc_id")
    
    if not doc_id:
        return _json_error("doc_id is required")
    
    try:
        doc_id = int(doc_id)
    except (ValueError, TypeError):
        return _json_error("doc_id must be an integer")
    
    priority_order = data.get("priority_order", 0)
    reason = data.get("reason")
    
    try:
        priority_order = int(priority_order)
    except (ValueError, TypeError):
        priority_order = 0
    
    try:
        result = services.add_priority_document(
            doc_id=doc_id,
            priority_order=priority_order,
            reason=reason
        )
        return JsonResponse({
            "success": True,
            "message": "Document added to priority list successfully",
            "priority_document": result
        })
    except ValueError as e:
        return _json_error(str(e), status=400)
    except Exception as e:
        logger.exception("Error adding priority document")
        return _json_error(str(e), status=500)


@csrf_exempt
@api_view(["POST"])
def priority_docs_remove_view(request: HttpRequest) -> JsonResponse:
    """
    Remove a document from priority list.
    JSON body:
        - priority_id: int (preferred)
        OR
        - doc_id: int
    """
    data = _read_json_body(request)
    priority_id = data.get("priority_id")
    doc_id = data.get("doc_id")
    
    if not priority_id and not doc_id:
        return _json_error("Either priority_id or doc_id is required")
    
    try:
        if priority_id:
            priority_id = int(priority_id)
        if doc_id:
            doc_id = int(doc_id)
    except (ValueError, TypeError):
        return _json_error("priority_id and doc_id must be integers")
    
    try:
        result = services.remove_priority_document(
            priority_id=priority_id,
            doc_id=doc_id
        )
        return JsonResponse({
            "success": True,
            "message": result["message"]
        })
    except ValueError as e:
        return _json_error(str(e), status=404)
    except Exception as e:
        logger.exception("Error removing priority document")
        return _json_error(str(e), status=500)


@csrf_exempt
@api_view(["POST"])
def priority_docs_update_order_view(request: HttpRequest) -> JsonResponse:
    """
    Update the priority order of a priority document.
    JSON body:
        - priority_id: int (required)
        - priority_order: int (required)
    """
    data = _read_json_body(request)
    priority_id = data.get("priority_id")
    priority_order = data.get("priority_order")
    
    if not priority_id or priority_order is None:
        return _json_error("priority_id and priority_order are required")
    
    try:
        priority_id = int(priority_id)
        priority_order = int(priority_order)
    except (ValueError, TypeError):
        return _json_error("priority_id and priority_order must be integers")
    
    try:
        result = services.update_priority_order(
            priority_id=priority_id,
            new_order=priority_order
        )
        return JsonResponse({
            "success": True,
            "message": "Priority order updated successfully",
            "priority_document": result
        })
    except ValueError as e:
        return _json_error(str(e), status=404)
    except Exception as e:
        logger.exception("Error updating priority order")
        return _json_error(str(e), status=500)


@csrf_exempt
@api_view(["GET"])
def priority_docs_stats_view(request: HttpRequest) -> JsonResponse:
    """
    Get statistics about priority documents.
    """
    try:
        stats = services.priority_documents_stats()
        return JsonResponse({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        logger.exception("Error fetching priority documents stats")
        return _json_error(str(e), status=500)