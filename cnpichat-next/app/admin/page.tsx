"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";

// Django backend base URL.
// CORS is already enabled on Django (CORS_ALLOW_ALL_ORIGINS=True), so the browser
// can call the backend directly without going through a Next.js proxy.
// NEXT_PUBLIC_API_URL is inlined at build time by Next.js (must be set in .env.local).
const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// All admin-panel endpoints live under /admin-panel/api/ on Django
const API = `${BACKEND}/admin-panel/api`;
const MAIN_API = `${BACKEND}/admin-panel/api`;

// ─── Types ───────────────────────────────────────────────────────────────────

interface StatsEntry {
  doc_type: string;
  cnt: number;
}
interface Stats {
  total: number;
  by_doc_type: StatsEntry[];
}

interface DocResult {
  doc_id: number;
  chunk_id: string;
  content: string;
  doc_type: string;
  department: string;
  topic: string;
  score?: number;
  meta?: Record<string, unknown> | string;
}

interface Captain {
  captain_id: number;
  department: string;
  shift: string;
  semester: number;
  captain_rank: 1 | 2;
  captain_name: string;
  student_id?: string;
  phone?: string;
  email?: string;
  session_year?: string;
  is_active: boolean;
}

type Tab = "update" | "add" | "captain";
type ToastKind = "ok" | "err" | "info";

interface Toast {
  id: number;
  msg: string;
  kind: ToastKind;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function esc(s: unknown): string {
  return String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[
        c
      ] ?? c)
  );
}

async function apiFetch(
  url: string,
  opts?: RequestInit
): Promise<{ ok: boolean; d: Record<string, unknown> }> {
  const r = await fetch(url, opts);
  const d = await r.json();
  return { ok: r.ok, d };
}

// ─── Toast component ─────────────────────────────────────────────────────────

function Toaster({ toasts }: { toasts: Toast[] }) {
  const colors: Record<ToastKind, React.CSSProperties> = {
    ok: {
      background: "#064e3b",
      color: "#bbf7d0",
      border: "1px solid #10b981",
    },
    err: {
      background: "#450a0a",
      color: "#fecaca",
      border: "1px solid #ef4444",
    },
    info: {
      background: "#0c4a6e",
      color: "#bae6fd",
      border: "1px solid #0ea5e9",
    },
  };
  return (
    <div
      style={{
        position: "fixed",
        bottom: 18,
        right: 18,
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          style={{
            padding: "10px 14px",
            borderRadius: 8,
            fontSize: 13,
            maxWidth: 360,
            boxShadow: "0 6px 20px rgba(0,0,0,.4)",
            ...colors[t.kind],
          }}
        >
          {t.msg}
        </div>
      ))}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("update");
  const toastIdRef = useRef(0);
  const [toasts, setToasts] = useState<Toast[]>([]);

  // Stats
  const [stats, setStats] = useState<Stats | null>(null);

  // Search
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [searchBusy, setSearchBusy] = useState(false);
  const [results, setResults] = useState<DocResult[]>([]);
  const [activeResult, setActiveResult] = useState<number | null>(null);

  // Update tab
  const [lookupKey, setLookupKey] = useState("");
  const [content, setContent] = useState("");
  const [docType, setDocType] = useState("");
  const [department, setDepartment] = useState("");
  const [topic, setTopic] = useState("");
  const [regen, setRegen] = useState(true);
  const [updateBusy, setUpdateBusy] = useState(false);
  const [updateResult, setUpdateResult] = useState<{
    before: DocResult | null;
    after: DocResult | null;
  } | null>(null);

  // Add tab
  const [newChunkId, setNewChunkId] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newDocType, setNewDocType] = useState("documents");
  const [newDepartment, setNewDepartment] = useState("");
  const [newTopic, setNewTopic] = useState("");
  const [newMeta, setNewMeta] = useState("");
  const [addBusy, setAddBusy] = useState(false);
  const [addResult, setAddResult] = useState<string>("");

  // Captain tab
  const [capDept, setCapDept] = useState("");
  const [capShift, setCapShift] = useState("Day");
  const [capSemester, setCapSemester] = useState("1");
  const [capRank, setCapRank] = useState<1 | 2>(1);
  const [capName, setCapName] = useState("");
  const [capStudentId, setCapStudentId] = useState("");
  const [capPhone, setCapPhone] = useState("");
  const [capEmail, setCapEmail] = useState("");
  const [capSession, setCapSession] = useState("");
  const [capEditId, setCapEditId] = useState<number | null>(null);
  const [capSaveBusy, setCapSaveBusy] = useState(false);

  const [filterDept, setFilterDept] = useState("");
  const [filterShift, setFilterShift] = useState("");
  const [filterSemester, setFilterSemester] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [captainsBusy, setCaptainsBusy] = useState(false);
  const [captains, setCaptains] = useState<Captain[]>([]);
  const [captainsLoaded, setCaptainsLoaded] = useState(false);

  // ── toast helper ─────────────────────────────────────────────────────────

  const toast = useCallback((msg: string, kind: ToastKind = "info") => {
    const id = ++toastIdRef.current;
    setToasts((prev) => [...prev, { id, msg, kind }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  // ── stats ─────────────────────────────────────────────────────────────────

  const loadStats = useCallback(async () => {
    try {
      const { ok, d } = await apiFetch(`${MAIN_API}/stats/`);
      if (ok) setStats(d as unknown as Stats);
    } catch (_) {}
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // ── search ────────────────────────────────────────────────────────────────

  const doSearch = useCallback(async () => {
    if (!query.trim()) return toast("Enter a search query.", "err");
    setSearchBusy(true);
    try {
      const { ok, d } = await apiFetch(`${MAIN_API}/search/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim(), top_k: topK }),
      });
      if (!ok) return toast((d.error as string) || "Search failed", "err");
      setResults((d.results as DocResult[]) || []);
      setActiveResult(null);
    } catch (e) {
      toast("Network error: " + e, "err");
    } finally {
      setSearchBusy(false);
    }
  }, [query, topK, toast]);

  // ── load doc ──────────────────────────────────────────────────────────────

  const loadDoc = useCallback(async () => {
    const key = lookupKey.trim();
    if (!key) return toast("Enter doc_id or chunk_id.", "err");
    const isNum = /^\d+$/.test(key);
    const qs = isNum
      ? `doc_id=${encodeURIComponent(key)}`
      : `chunk_id=${encodeURIComponent(key)}`;
    try {
      const { ok, d } = await apiFetch(`${MAIN_API}/document/?${qs}`);
      if (!ok) return toast((d.error as string) || "Not found", "err");
      const doc = d.document as DocResult;
      setContent(doc.content || "");
      setDocType(doc.doc_type || "");
      setDepartment(doc.department || "");
      setTopic(doc.topic || "");
      toast(
        "Loaded " + (isNum ? `doc_id=${doc.doc_id}` : `chunk_id=${doc.chunk_id}`),
        "info"
      );
    } catch (e) {
      toast("Network error: " + e, "err");
    }
  }, [lookupKey, toast]);

  // ── update ────────────────────────────────────────────────────────────────

  const doUpdate = useCallback(async () => {
    const key = lookupKey.trim();
    if (!key) return toast("Enter doc_id or chunk_id first.", "err");
    if (content.trim().length < 11)
      return toast("Content must be at least 11 characters.", "err");
    const isNum = /^\d+$/.test(key);
    const body: Record<string, unknown> = {
      content: content.trim(),
      doc_type: docType.trim() || null,
      topic: topic.trim() || null,
      department: department || null,
      regenerate_embedding: regen,
    };
    if (isNum) body.doc_id = parseInt(key, 10);
    else body.chunk_id = key;

    setUpdateBusy(true);
    setUpdateResult(null);
    try {
      const { ok, d } = await apiFetch(`${MAIN_API}/update/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!ok) return toast((d.error as string) || "Update failed", "err");
      toast(
        `Updated ${(d.embedding_regenerated as boolean) ? "(embedding regenerated)" : ""}`,
        "ok"
      );
      setUpdateResult({
        before: d.before as DocResult,
        after: d.after as DocResult,
      });
    } catch (e) {
      toast("Network error: " + e, "err");
    } finally {
      setUpdateBusy(false);
    }
  }, [lookupKey, content, docType, topic, department, regen, toast]);

  // ── create ────────────────────────────────────────────────────────────────

  const doCreate = useCallback(async () => {
    const isNotice = newDocType === "notices";
    const chunk_id = isNotice ? "" : newChunkId.trim();
    if (!isNotice && !chunk_id)
      return toast("chunk_id is required.", "err");
    if (newContent.trim().length < 11)
      return toast("Content must be at least 11 characters.", "err");
    const body = {
      chunk_id,
      content: newContent.trim(),
      doc_type: newDocType,
      topic: newTopic.trim() || null,
      department: newDepartment || null,
      meta: newMeta.trim() || null,
      source_file: "admin_panel",
    };
    setAddBusy(true);
    setAddResult(
      '<div style="color:#94a3b8;text-align:center;padding:20px">⏳ Translating & processing…</div>'
    );
    try {
      const { ok, d } = await apiFetch(`${MAIN_API}/create/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!ok) {
        setAddResult("");
        return toast((d.error as string) || "Create failed", "err");
      }
      const xlat = d.translation_performed ? " · translated Bengali→English" : "";
      const dateInfo = d.context_added_date
        ? ` · ${d.context_added_date} ${d.context_added_time} BST`
        : "";
      const noticeInfo = d.inserted_into_notices
        ? ` · notice_id=${d.notice_id}`
        : "";
      toast(`Created doc_id=${d.doc_id}${xlat}${dateInfo}${noticeInfo}`, "ok");
      setAddResult(
        `<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px">
          <div style="font-size:12px;color:#94a3b8;margin-bottom:6px">doc_id: ${esc(d.doc_id)} · chunk_id: <b>${esc(d.chunk_id)}</b></div>
          <div style="font-size:13px;white-space:pre-wrap;font-family:monospace;max-height:120px;overflow:auto">${esc((d.document as { content?: string })?.content ?? "")}</div>
        </div>`
      );
      loadStats();
    } catch (e) {
      toast("Network error: " + e, "err");
      setAddResult("");
    } finally {
      setAddBusy(false);
    }
  }, [newDocType, newChunkId, newContent, newTopic, newDepartment, newMeta, toast, loadStats]);

  // ── captains ──────────────────────────────────────────────────────────────

  const loadCaptains = useCallback(async () => {
    setCaptainsBusy(true);
    try {
      const params = new URLSearchParams();
      params.set("active_only", showInactive ? "false" : "true");
      if (filterDept) params.set("department", filterDept);
      if (filterShift) params.set("shift", filterShift);
      if (filterSemester) params.set("semester", filterSemester);
      const { ok, d } = await apiFetch(
        `${API}/captains/?${params.toString()}`
      );
      if (!ok) return toast((d.error as string) || "Load failed", "err");
      setCaptains((d.captains as Captain[]) || []);
      setCaptainsLoaded(true);
    } catch (e) {
      toast("Network error: " + e, "err");
    } finally {
      setCaptainsBusy(false);
    }
  }, [filterDept, filterShift, filterSemester, showInactive, toast]);

  const saveCaptain = useCallback(async () => {
    if (!capName.trim()) return toast("captain_name is required.", "err");
    setCapSaveBusy(true);
    try {
      if (capEditId !== null) {
        // Update
        const body: Record<string, unknown> = { captain_id: capEditId };
        if (capName.trim()) body.captain_name = capName.trim();
        if (capStudentId.trim()) body.student_id = capStudentId.trim();
        if (capPhone.trim()) body.phone = capPhone.trim();
        if (capEmail.trim()) body.email = capEmail.trim();
        if (capSession.trim()) body.session_year = capSession.trim();
        const { ok, d } = await apiFetch(`${API}/captains/update/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!ok) return toast((d.error as string) || "Update failed", "err");
        toast("Captain updated!", "ok");
      } else {
        // Create
        if (!capDept) return toast("Department is required.", "err");
        const body: Record<string, unknown> = {
          department: capDept,
          shift: capShift,
          semester: parseInt(capSemester, 10),
          captain_rank: capRank,
          captain_name: capName.trim(),
        };
        if (capStudentId.trim()) body.student_id = capStudentId.trim();
        if (capPhone.trim()) body.phone = capPhone.trim();
        if (capEmail.trim()) body.email = capEmail.trim();
        if (capSession.trim()) body.session_year = capSession.trim();
        const { ok, d } = await apiFetch(`${API}/captains/create/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!ok) return toast((d.error as string) || "Create failed", "err");
        toast("Captain saved!", "ok");
      }
      // Reset form
      setCapEditId(null);
      setCapName("");
      setCapStudentId("");
      setCapPhone("");
      setCapEmail("");
      setCapSession("");
      setCapDept("");
      setCapShift("Day");
      setCapSemester("1");
      setCapRank(1);
      loadCaptains();
    } catch (e) {
      toast("Network error: " + e, "err");
    } finally {
      setCapSaveBusy(false);
    }
  }, [
    capEditId, capDept, capShift, capSemester, capRank, capName,
    capStudentId, capPhone, capEmail, capSession, toast, loadCaptains,
  ]);

  const editCaptain = useCallback((c: Captain) => {
    setCapEditId(c.captain_id);
    setCapDept(c.department);
    setCapShift(c.shift);
    setCapSemester(String(c.semester));
    setCapRank(c.captain_rank ?? 1);
    setCapName(c.captain_name);
    setCapStudentId(c.student_id || "");
    setCapPhone(c.phone || "");
    setCapEmail(c.email || "");
    setCapSession(c.session_year || "");
  }, []);

  const deactivateCaptain = useCallback(
    async (captain_id: number, name: string) => {
      if (!window.confirm(`Deactivate "${name}"?`)) return;
      try {
        const { ok, d } = await apiFetch(`${API}/captains/deactivate/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ captain_id }),
        });
        if (!ok) return toast((d.error as string) || "Failed", "err");
        toast("Captain deactivated.", "ok");
        loadCaptains();
      } catch (e) {
        toast("Network error: " + e, "err");
      }
    },
    [toast, loadCaptains]
  );

  // Auto-load captains when switching to captain tab
  const switchTab = (t: Tab) => {
    setTab(t);
    if (t === "captain") loadCaptains();
  };

  // ── styling constants ─────────────────────────────────────────────────────

  const S = {
    panel: {
      background: "#1e293b",
      border: "1px solid #334155",
      borderRadius: 12,
      display: "flex",
      flexDirection: "column" as const,
      overflow: "hidden",
    },
    paneH2: {
      fontSize: 15,
      margin: 0,
      padding: "12px 16px",
      borderBottom: "1px solid #334155",
      background: "#273449",
      display: "flex",
      alignItems: "center",
      gap: 8,
    },
    body: { padding: 16, overflow: "auto" as const, flex: 1 },
    field: { marginBottom: 12 },
    label: {
      display: "block",
      fontSize: 12,
      color: "#94a3b8",
      marginBottom: 4,
      fontWeight: 600,
    },
    input: {
      width: "100%",
      background: "#0f172a",
      color: "#e2e8f0",
      border: "1px solid #334155",
      borderRadius: 8,
      padding: "9px 11px",
      fontSize: 14,
      fontFamily: "inherit",
      outline: "none",
    },
    select: {
      width: "100%",
      background: "#0f172a",
      color: "#e2e8f0",
      border: "1px solid #334155",
      borderRadius: 8,
      padding: "9px 11px",
      fontSize: 14,
      fontFamily: "inherit",
      outline: "none",
    },
    textarea: {
      width: "100%",
      background: "#0f172a",
      color: "#e2e8f0",
      border: "1px solid #334155",
      borderRadius: 8,
      padding: "9px 11px",
      fontSize: 13,
      fontFamily: "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace",
      minHeight: 100,
      resize: "vertical" as const,
      outline: "none",
    },
    btn: {
      cursor: "pointer",
      border: "none",
      borderRadius: 8,
      padding: "9px 16px",
      fontSize: 14,
      fontWeight: 600,
      background: "#38bdf8",
      color: "#0b1220",
    },
    btnSecondary: {
      cursor: "pointer",
      border: "1px solid #334155",
      borderRadius: 8,
      padding: "9px 16px",
      fontSize: 14,
      fontWeight: 600,
      background: "#273449",
      color: "#e2e8f0",
    },
    btnDanger: {
      cursor: "pointer",
      border: "1px solid #7f1d1d",
      borderRadius: 8,
      padding: "6px 12px",
      fontSize: 12,
      fontWeight: 600,
      background: "#450a0a",
      color: "#fca5a5",
    },
    btnEdit: {
      cursor: "pointer",
      border: "1px solid #334155",
      borderRadius: 8,
      padding: "6px 12px",
      fontSize: 12,
      fontWeight: 600,
      background: "#273449",
      color: "#e2e8f0",
    },
    row: { display: "flex", gap: 10, marginBottom: 12, alignItems: "flex-end" },
    two: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 },
    three: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 },
    muted: { color: "#94a3b8" },
  };

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* HEADER */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "14px 20px",
          borderBottom: "1px solid #334155",
          background: "#1e293b",
          flexShrink: 0,
        }}
      >
        <h1 style={{ fontSize: 18, margin: 0, fontWeight: 600 }}>
          CNPI RAG – Admin Panel
        </h1>
        <span
          style={{
            fontSize: 12,
            color: "#94a3b8",
            background: "#273449",
            padding: "3px 8px",
            borderRadius: 6,
            border: "1px solid #334155",
          }}
        >
          documents table
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 10, fontSize: 13, color: "#94a3b8" }}>
          {stats && (
            <>
              <span>
                Total: <b style={{ color: "#e2e8f0" }}>{stats.total}</b>
              </span>
              {(stats.by_doc_type || []).slice(0, 3).map((t) => (
                <span key={t.doc_type}>
                  {t.doc_type}: <b style={{ color: "#e2e8f0" }}>{t.cnt}</b>
                </span>
              ))}
            </>
          )}
        </div>
      </header>

      {/* LAYOUT */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.1fr 1fr",
          gap: 16,
          padding: 16,
          flex: 1,
          overflow: "hidden",
        }}
      >
        {/* ── LEFT: Search ── */}
        <section style={S.panel}>
          <h2 style={S.paneH2}>🔍 Semantic Search</h2>
          <div style={S.body}>
            <div style={S.row}>
              <input
                style={{ ...S.input, flex: 1 }}
                type="text"
                placeholder="Ask a question / search content…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && doSearch()}
              />
              <select
                style={{ ...S.select, width: 90 }}
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value, 10))}
              >
                {[5, 10, 15, 20].map((n) => (
                  <option key={n}>{n}</option>
                ))}
              </select>
              <button
                style={{ ...S.btn, opacity: searchBusy ? 0.5 : 1 }}
                onClick={doSearch}
                disabled={searchBusy}
              >
                {searchBusy ? "…" : "Search"}
              </button>
            </div>
            <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 12, marginTop: -6 }}>
              Embeds your question and finds the closest document chunks by cosine similarity (pgvector).
            </p>

            {/* Results */}
            {results.length === 0 ? (
              <div style={{ color: "#94a3b8", textAlign: "center", padding: 30, fontSize: 13 }}>
                Results will appear here.
              </div>
            ) : (
              results.map((r, i) => {
                const metaObj =
                  r.meta
                    ? typeof r.meta === "string"
                      ? JSON.parse(r.meta || "{}")
                      : r.meta
                    : {};
                const metaStr = Object.keys(metaObj).length
                  ? JSON.stringify(metaObj, null, 2)
                  : "";
                return (
                  <div
                    key={i}
                    onClick={() => {
                      setActiveResult(i);
                      setLookupKey(r.chunk_id);
                      setTab("update");
                      // load doc
                      const key = r.chunk_id;
                      apiFetch(`${MAIN_API}/document/?chunk_id=${encodeURIComponent(key)}`).then(
                        ({ ok, d }) => {
                          if (!ok) return;
                          const doc = d.document as DocResult;
                          setContent(doc.content || "");
                          setDocType(doc.doc_type || "");
                          setDepartment(doc.department || "");
                          setTopic(doc.topic || "");
                        }
                      );
                    }}
                    style={{
                      background: "#273449",
                      border: `1px solid ${activeResult === i ? "#818cf8" : "#334155"}`,
                      borderRadius: 10,
                      padding: 12,
                      marginBottom: 10,
                      cursor: "pointer",
                      boxShadow: activeResult === i ? "0 0 0 2px rgba(129,140,248,.25)" : "none",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: 12,
                        color: "#94a3b8",
                        marginBottom: 6,
                      }}
                    >
                      <span style={{ fontFamily: "monospace", color: "#e2e8f0" }}>
                        doc_id: {r.doc_id} · chunk_id: <b>{r.chunk_id}</b>
                      </span>
                      <span style={{ color: "#38bdf8", fontWeight: 600 }}>
                        score: {(r.score || 0).toFixed(4)}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: 13,
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        maxHeight: 100,
                        overflow: "auto",
                        fontFamily: "monospace",
                        lineHeight: 1.5,
                      }}
                    >
                      {r.content}
                    </div>
                    <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
                      {r.doc_type && (
                        <span style={{ fontSize: 11, background: "#0f172a", border: "1px solid #334155", padding: "2px 7px", borderRadius: 6, color: "#94a3b8" }}>
                          type: {r.doc_type}
                        </span>
                      )}
                      {r.department && (
                        <span style={{ fontSize: 11, background: "#0f172a", border: "1px solid #334155", padding: "2px 7px", borderRadius: 6, color: "#94a3b8" }}>
                          dept: {r.department}
                        </span>
                      )}
                      {r.topic && (
                        <span style={{ fontSize: 11, background: "#0f172a", border: "1px solid #334155", padding: "2px 7px", borderRadius: 6, color: "#94a3b8" }}>
                          topic: {r.topic}
                        </span>
                      )}
                    </div>
                    {metaStr && (
                      <details style={{ marginTop: 8 }}>
                        <summary style={{ cursor: "pointer", fontSize: 12, color: "#94a3b8" }}>meta</summary>
                        <div style={{ fontSize: 11, color: "#94a3b8", fontFamily: "monospace", marginTop: 6, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                          {metaStr}
                        </div>
                      </details>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </section>

        {/* ── RIGHT: Tabs ── */}
        <section style={S.panel}>
          {/* Tab bar */}
          <div
            style={{
              display: "flex",
              borderBottom: "1px solid #334155",
              background: "#273449",
              flexShrink: 0,
            }}
          >
            {(["update", "add", "captain"] as Tab[]).map((t) => {
              const labels: Record<Tab, string> = {
                update: "✏️ Update",
                add: "➕ Add New",
                captain: "🎖️ Captain",
              };
              return (
                <button
                  key={t}
                  onClick={() => switchTab(t)}
                  style={{
                    flex: 1,
                    padding: 10,
                    border: "none",
                    background: "transparent",
                    color: tab === t ? "#e2e8f0" : "#94a3b8",
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: "pointer",
                    borderBottom: tab === t ? "2px solid #38bdf8" : "2px solid transparent",
                  }}
                >
                  {labels[t]}
                </button>
              );
            })}
          </div>

          {/* ── TAB: Update ── */}
          {tab === "update" && (
            <div style={{ ...S.body, display: "flex", flexDirection: "column" }}>
              <div style={S.row}>
                <input
                  style={{ ...S.input, flex: 1 }}
                  type="text"
                  placeholder="doc_id or chunk_id"
                  value={lookupKey}
                  onChange={(e) => setLookupKey(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && loadDoc()}
                />
                <button style={S.btnSecondary} onClick={loadDoc}>
                  Load
                </button>
              </div>
              <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 12, marginTop: -6 }}>
                Enter a doc_id (number) or chunk_id (string) to load the current row, then edit & save.
              </p>

              <div style={S.field}>
                <label style={S.label}>
                  Content{" "}
                  <span style={{ color: "#94a3b8", fontWeight: 400 }}>
                    (min 11 chars – embedding regenerated on save)
                  </span>
                </label>
                <textarea
                  style={S.textarea}
                  placeholder="Document content…"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </div>

              <div style={S.two}>
                <div style={S.field}>
                  <label style={S.label}>doc_type</label>
                  <input
                    style={S.input}
                    type="text"
                    placeholder="general"
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                  />
                </div>
                <div style={S.field}>
                  <label style={S.label}>department</label>
                  <select
                    style={S.select}
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                  >
                    <option value="">(none)</option>
                    {["CST", "ET", "ENT", "RAC", "FT", "MT", "Non-Tech", "General"].map(
                      (d) => <option key={d}>{d}</option>
                    )}
                  </select>
                </div>
              </div>

              <div style={S.field}>
                <label style={S.label}>topic</label>
                <input
                  style={S.input}
                  type="text"
                  placeholder="topic"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#94a3b8", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={regen}
                    onChange={(e) => setRegen(e.target.checked)}
                    style={{ width: "auto" }}
                  />
                  Regenerate embedding
                </label>
                <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                  <button
                    style={S.btnSecondary}
                    onClick={() => {
                      setLookupKey(""); setContent(""); setDocType("");
                      setTopic(""); setDepartment(""); setUpdateResult(null);
                    }}
                  >
                    Clear
                  </button>
                  <button
                    style={{ ...S.btn, opacity: updateBusy ? 0.5 : 1 }}
                    onClick={doUpdate}
                    disabled={updateBusy}
                  >
                    {updateBusy ? "…" : "Update Row"}
                  </button>
                </div>
              </div>

              {updateResult && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
                  {["before", "after"].map((k) => {
                    const doc = updateResult[k as "before" | "after"];
                    return (
                      <div
                        key={k}
                        style={{
                          background: "#0f172a",
                          border: "1px solid #334155",
                          borderRadius: 8,
                          padding: 10,
                          fontSize: 12,
                          fontFamily: "monospace",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          maxHeight: 160,
                          overflow: "auto",
                        }}
                      >
                        <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 6, textTransform: "uppercase" }}>
                          {k}
                        </div>
                        {doc
                          ? `doc_id: ${doc.doc_id}\nchunk_id: ${doc.chunk_id}\ndoc_type: ${doc.doc_type}\ndepartment: ${doc.department}\ntopic: ${doc.topic}\n\n${doc.content}`
                          : "(none)"}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ── TAB: Add New ── */}
          {tab === "add" && (
            <div style={{ ...S.body, display: "flex", flexDirection: "column" }}>
              <div style={S.field}>
                <label style={S.label}>
                  chunk_id{" "}
                  <span style={{ color: newDocType === "notices" ? "#22c55e" : "#f59e0b", fontWeight: 400 }}>
                    {newDocType === "notices"
                      ? "(auto-generated for notices)"
                      : "(required, must be unique)"}
                  </span>
                </label>
                <input
                  style={{ ...S.input, opacity: newDocType === "notices" ? 0.4 : 1 }}
                  type="text"
                  placeholder={newDocType === "notices" ? "Auto-generated (notice-ID)" : "e.g. manual_cst_1"}
                  value={newChunkId}
                  onChange={(e) => setNewChunkId(e.target.value)}
                  disabled={newDocType === "notices"}
                />
              </div>

              <div style={S.field}>
                <label style={S.label}>
                  Content{" "}
                  <span style={{ color: "#94a3b8", fontWeight: 400 }}>
                    (min 11 chars – Bengali auto-translated → English)
                  </span>
                </label>
                <textarea
                  style={S.textarea}
                  placeholder="New document content…"
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                />
              </div>

              <div style={S.two}>
                <div style={S.field}>
                  <label style={S.label}>doc_type (Table Name)</label>
                  <select
                    style={S.select}
                    value={newDocType}
                    onChange={(e) => {
                      setNewDocType(e.target.value);
                      if (e.target.value !== "notices") {
                        /* reset chunk id lock */
                      }
                    }}
                  >
                    {[
                      "documents", "notices", "buildings", "departments",
                      "designations", "exam_routines", "facilities", "future_plans",
                      "institutions", "lab_assignments", "labs", "people",
                      "rooms", "routine_classes", "routines", "subjects",
                    ].map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={S.field}>
                  <label style={S.label}>department</label>
                  <select
                    style={S.select}
                    value={newDepartment}
                    onChange={(e) => setNewDepartment(e.target.value)}
                  >
                    <option value="">(none)</option>
                    {["CST", "ET", "ENT", "RAC", "FT", "MT", "Non-Tech", "General"].map(
                      (d) => <option key={d}>{d}</option>
                    )}
                  </select>
                </div>
              </div>

              <div style={S.field}>
                <label style={S.label}>topic</label>
                <input
                  style={S.input}
                  type="text"
                  placeholder="topic"
                  value={newTopic}
                  onChange={(e) => setNewTopic(e.target.value)}
                />
              </div>

              <div style={S.field}>
                <label style={S.label}>meta (JSON, optional)</label>
                <input
                  style={S.input}
                  type="text"
                  placeholder='{"key":"value"}'
                  value={newMeta}
                  onChange={(e) => setNewMeta(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 12 }}>
                <button
                  style={S.btnSecondary}
                  onClick={() => {
                    setNewChunkId(""); setNewContent(""); setNewDocType("documents");
                    setNewTopic(""); setNewDepartment(""); setNewMeta(""); setAddResult("");
                  }}
                >
                  Clear
                </button>
                <button
                  style={{ ...S.btn, opacity: addBusy ? 0.5 : 1 }}
                  onClick={doCreate}
                  disabled={addBusy}
                >
                  {addBusy ? "…" : "Create Document"}
                </button>
              </div>

              {addResult && (
                <div dangerouslySetInnerHTML={{ __html: addResult }} />
              )}
            </div>
          )}

          {/* ── TAB: Captain ── */}
          {tab === "captain" && (
            <div style={{ ...S.body, display: "flex", flexDirection: "column", gap: 0 }}>
              {/* Section 1: Form */}
              <div
                style={{
                  background: "#273449",
                  border: "1px solid #334155",
                  borderRadius: 10,
                  padding: 14,
                  marginBottom: 16,
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "#94a3b8",
                    marginBottom: 12,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  {capEditId !== null ? (
                    <>
                      ✏️ Edit Captain{" "}
                      <span style={{ fontSize: 11, fontFamily: "monospace", color: "#38bdf8" }}>
                        #{capEditId}
                      </span>
                      <span style={{
                        fontSize: 11, fontWeight: 700, marginLeft: 6,
                        padding: "1px 6px", borderRadius: 4,
                        background: capRank === 1 ? "#0c4a6e" : "#2e1065",
                        border: capRank === 1 ? "1px solid #38bdf8" : "1px solid #a78bfa",
                        color: capRank === 1 ? "#38bdf8" : "#a78bfa",
                      }}>
                        {capRank === 1 ? "1st Captain" : "2nd Captain"}
                      </span>
                    </>
                  ) : (
                    "➕ Add Captain"
                  )}
                </div>

                {/* Row 1: dept / shift / semester / rank */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10 }}>
                  <div style={S.field}>
                    <label style={S.label}>department</label>
                    <select
                      style={S.select}
                      value={capDept}
                      onChange={(e) => setCapDept(e.target.value)}
                      disabled={capEditId !== null}
                    >
                      <option value="">— select —</option>
                      {["CST", "ET", "ENT", "RAC", "FT", "MT"].map((d) => (
                        <option key={d}>{d}</option>
                      ))}
                    </select>
                  </div>
                  <div style={S.field}>
                    <label style={S.label}>shift</label>
                    <select
                      style={S.select}
                      value={capShift}
                      onChange={(e) => setCapShift(e.target.value)}
                      disabled={capEditId !== null}
                    >
                      <option>Day</option>
                      <option>Morning</option>
                    </select>
                  </div>
                  <div style={S.field}>
                    <label style={S.label}>semester</label>
                    <select
                      style={S.select}
                      value={capSemester}
                      onChange={(e) => setCapSemester(e.target.value)}
                      disabled={capEditId !== null}
                    >
                      {["1","2","3","4","5","6","7"].map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                  <div style={S.field}>
                    <label style={S.label}>rank <span style={{ color: "#ef4444" }}>*</span></label>
                    <select
                      style={{
                        ...S.select,
                        borderColor: capRank === 1 ? "#38bdf8" : "#a78bfa",
                        color: capRank === 1 ? "#38bdf8" : "#a78bfa",
                        fontWeight: 700,
                      }}
                      value={capRank}
                      onChange={(e) => setCapRank(Number(e.target.value) as 1 | 2)}
                      disabled={capEditId !== null}
                    >
                      <option value={1}>1st Captain</option>
                      <option value={2}>2nd Captain</option>
                    </select>
                  </div>
                </div>

                {/* Row 2: name + student_id */}
                <div style={S.two}>
                  <div style={S.field}>
                    <label style={S.label}>captain_name <span style={{ color: "#ef4444" }}>*</span></label>
                    <input
                      style={S.input}
                      type="text"
                      placeholder="Full name"
                      value={capName}
                      onChange={(e) => setCapName(e.target.value)}
                    />
                  </div>
                  <div style={S.field}>
                    <label style={S.label}>student_id</label>
                    <input
                      style={S.input}
                      type="text"
                      placeholder="optional"
                      value={capStudentId}
                      onChange={(e) => setCapStudentId(e.target.value)}
                    />
                  </div>
                </div>

                {/* Row 3: phone + email + session */}
                <div style={S.three}>
                  <div style={S.field}>
                    <label style={S.label}>phone</label>
                    <input
                      style={S.input}
                      type="text"
                      placeholder="01XXXXXXXXX"
                      value={capPhone}
                      onChange={(e) => setCapPhone(e.target.value)}
                    />
                  </div>
                  <div style={S.field}>
                    <label style={S.label}>email</label>
                    <input
                      style={S.input}
                      type="text"
                      placeholder="optional"
                      value={capEmail}
                      onChange={(e) => setCapEmail(e.target.value)}
                    />
                  </div>
                  <div style={S.field}>
                    <label style={S.label}>session_year</label>
                    <input
                      style={S.input}
                      type="text"
                      placeholder="2024-25"
                      value={capSession}
                      onChange={(e) => setCapSession(e.target.value)}
                    />
                  </div>
                </div>

                {/* Buttons */}
                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button
                    style={S.btnSecondary}
                    onClick={() => {
                      setCapEditId(null);
                      setCapName(""); setCapStudentId(""); setCapPhone("");
                      setCapEmail(""); setCapSession(""); setCapDept("");
                      setCapShift("Day"); setCapSemester("1"); setCapRank(1);
                    }}
                  >
                    Clear
                  </button>
                  <button
                    style={{ ...S.btn, opacity: capSaveBusy ? 0.5 : 1 }}
                    onClick={saveCaptain}
                    disabled={capSaveBusy}
                  >
                    {capSaveBusy ? "…" : "Save Captain"}
                  </button>
                </div>
              </div>

              {/* Section 2: Filter bar */}
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  marginBottom: 12,
                  flexWrap: "wrap",
                  alignItems: "flex-end",
                  flexShrink: 0,
                }}
              >
                <div>
                  <div style={{ ...S.label, marginBottom: 4 }}>Dept</div>
                  <select
                    style={{ ...S.select, width: 90, padding: "7px 8px" }}
                    value={filterDept}
                    onChange={(e) => setFilterDept(e.target.value)}
                  >
                    <option value="">All</option>
                    {["CST","ET","ENT","RAC","FT","MT"].map((d) => (
                      <option key={d}>{d}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <div style={{ ...S.label, marginBottom: 4 }}>Shift</div>
                  <select
                    style={{ ...S.select, width: 100, padding: "7px 8px" }}
                    value={filterShift}
                    onChange={(e) => setFilterShift(e.target.value)}
                  >
                    <option value="">All</option>
                    <option>Day</option>
                    <option>Morning</option>
                  </select>
                </div>
                <div>
                  <div style={{ ...S.label, marginBottom: 4 }}>Sem</div>
                  <select
                    style={{ ...S.select, width: 70, padding: "7px 8px" }}
                    value={filterSemester}
                    onChange={(e) => setFilterSemester(e.target.value)}
                  >
                    <option value="">All</option>
                    {["1","2","3","4","5","6","7"].map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 12,
                    color: "#94a3b8",
                    cursor: "pointer",
                    paddingBottom: 8,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={showInactive}
                    onChange={(e) => setShowInactive(e.target.checked)}
                    style={{ width: "auto" }}
                  />
                  Show Inactive
                </label>
                <button
                  style={{ ...S.btn, padding: "7px 16px", opacity: captainsBusy ? 0.5 : 1 }}
                  onClick={loadCaptains}
                  disabled={captainsBusy}
                >
                  {captainsBusy ? "…" : "Load"}
                </button>
              </div>

              {/* Captain cards */}
              <div style={{ flex: 1, overflow: "auto" }}>
                {!captainsLoaded ? (
                  <div style={{ color: "#94a3b8", textAlign: "center", padding: 30, fontSize: 13 }}>
                    Click Load to fetch captains.
                  </div>
                ) : captains.length === 0 ? (
                  <div style={{ color: "#94a3b8", textAlign: "center", padding: 30, fontSize: 13 }}>
                    No captains found.
                  </div>
                ) : (
                  captains.map((c) => (
                    <div
                      key={c.captain_id}
                      style={{
                        background: "#273449",
                        border: "1px solid #334155",
                        borderRadius: 10,
                        padding: 12,
                        marginBottom: 10,
                      }}
                    >
                      {/* Top row */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                        <div>
                          {/* Rank label before name */}
                          <span style={{
                            fontSize: 11,
                            fontWeight: 700,
                            padding: "1px 7px",
                            borderRadius: 5,
                            marginRight: 6,
                            background: c.captain_rank === 1 ? "#0c4a6e" : "#2e1065",
                            border: c.captain_rank === 1 ? "1px solid #38bdf8" : "1px solid #a78bfa",
                            color: c.captain_rank === 1 ? "#38bdf8" : "#a78bfa",
                          }}>
                            {c.captain_rank === 1 ? "1st" : "2nd"}
                          </span>
                          <span style={{ fontWeight: 700, fontSize: 14, color: "#e2e8f0" }}>
                            {c.captain_name}
                          </span>
                          {/* Badges */}
                          <span style={{ marginLeft: 8, fontSize: 11, background: "#0f172a", border: "1px solid #334155", padding: "2px 6px", borderRadius: 5, color: "#38bdf8" }}>
                            {c.department}
                          </span>
                          <span style={{ marginLeft: 4, fontSize: 11, background: "#0f172a", border: "1px solid #334155", padding: "2px 6px", borderRadius: 5, color: "#818cf8" }}>
                            {c.shift}
                          </span>
                          <span style={{ marginLeft: 4, fontSize: 11, background: "#0f172a", border: "1px solid #334155", padding: "2px 6px", borderRadius: 5, color: "#94a3b8" }}>
                            Sem {c.semester}
                          </span>
                        </div>
                        {/* Active badge */}
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 600,
                            padding: "2px 8px",
                            borderRadius: 6,
                            border: c.is_active ? "1px solid #10b981" : "1px solid #ef4444",
                            color: c.is_active ? "#bbf7d0" : "#fecaca",
                            background: c.is_active ? "#064e3b" : "#450a0a",
                          }}
                        >
                          {c.is_active ? "active" : "inactive"}
                        </span>
                      </div>

                      {/* Details */}
                      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8, display: "flex", flexWrap: "wrap", gap: "4px 12px" }}>
                        {c.student_id && <span>🪪 {c.student_id}</span>}
                        {c.phone && <span>📞 {c.phone}</span>}
                        {c.email && <span>✉️ {c.email}</span>}
                        {c.session_year && <span>📅 {c.session_year}</span>}
                      </div>

                      {/* ID + buttons */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: 11, fontFamily: "monospace", color: "#64748b" }}>
                          #{c.captain_id}
                        </span>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            style={S.btnEdit}
                            onClick={() => editCaptain(c)}
                          >
                            Edit
                          </button>
                          {c.is_active && (
                            <button
                              style={S.btnDanger}
                              onClick={() => deactivateCaptain(c.captain_id, c.captain_name)}
                            >
                              Deactivate
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      <Toaster toasts={toasts} />
    </div>
  );
}
