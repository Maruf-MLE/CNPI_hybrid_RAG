"""
Interactive Graph Visualizer for CNPI Hybrid RAG
Generates:
1. graph.png - High resolution diagram image
2. view_graph.html - Interactive zoomable/pannable diagram with node details and phase highlights
"""

import os
import sys
import webbrowser
from pathlib import Path

# Setup paths
project_root = Path(__file__).resolve().parent
cnpi_rag_path = project_root / "Cnpi_RAG"
plan_path = project_root / "plan"

for p in [str(project_root), str(cnpi_rag_path), str(plan_path)]:
    if p not in sys.path:
        sys.path.insert(0, p)

print("Compiling CNPI Hybrid RAG LangGraph...")
from Cnpi_RAG.graph import app

compiled = app.compile()
graph_mermaid = compiled.get_graph().draw_mermaid()

# 1. Generate PNG
png_path = project_root / "graph.png"
try:
    png_data = compiled.get_graph().draw_mermaid_png()
    with open(png_path, "wb") as f:
        f.write(png_data)
    print(f"✓ PNG graph saved to: {png_path}")
except Exception as e:
    print(f"⚠ Could not generate PNG directly: {e}")

# 2. Node documentation metadata for interactive viewer
NODE_INFO = {
    "rewrite_query": {
        "title": "Query Rewrite (Phase 1)",
        "phase": "Phase 1 - Entry & Router",
        "color": "#3b82f6",
        "description": "ব্যবহারকারীর প্রশ্নকে প্রজেক্টের কনটেক্সটে পরিষ্কার ও সঠিক রূপ দেয়।"
    },
    "entity_normalizer": {
        "title": "Entity Normalizer (Phase 1)",
        "phase": "Phase 1 - Entry & Router",
        "color": "#3b82f6",
        "description": "নাম, ডিপার্টমেন্ট, সেমিস্টার ও টার্মগুলো ডেটাবেজ স্কিমার সাথে সামঞ্জস্যপূর্ণ স্ট্যান্ডার্ড ফরম্যাটে রূপান্তর করে।"
    },
    "llm_decide_path": {
        "title": "LLM Path Router (Phase 1)",
        "phase": "Phase 1 - Entry & Router",
        "color": "#3b82f6",
        "description": "প্রশ্ন অ্যানালাইসিস করে সঠিক পাথে পাঠায় (sql_query, sql_retrieve, web_search, বা hybrid)। কনফিডেন্স < 0.7 হলে hybrid-এ যায়।"
    },
    "sql_query_info_check": {
        "title": "SQL Query Info Check (Phase 2)",
        "phase": "Phase 2 - SQL Query Path",
        "color": "#10b981",
        "description": "রুটিন ও টেবুলার প্রশ্নের জন্য শিফট, সেমিস্টার বা ডিপার্টমেন্ট পর্যাপ্ত কিনা যাচাই করে।"
    },
    "sql_query_short_info_response": {
        "title": "Short Info Response",
        "phase": "Clarification",
        "color": "#f59e0b",
        "description": "প্রয়োজনীয় তথ্য মিসিং থাকলে ব্যবহারকারীকে স্পষ্ট করার জন্য প্রশ্ন জিজ্ঞেস করে।"
    },
    "context_retrieve": {
        "title": "Context Retrieve / SQL Exec (Phase 2)",
        "phase": "Phase 2 - SQL Query Path",
        "color": "#10b981",
        "description": "SQL জেনারেট করে সরাসরি ডেটাবেজে এক্সিকিউট করে তথ্য নিয়ে আসে।"
    },
    "context_format": {
        "title": "Context Format (Phase 2)",
        "phase": "Phase 2 - SQL Query Path",
        "color": "#10b981",
        "description": "ডেটাবেজ থেকে পাওয়া রুটিন ও টেবুলার ডেটাকে সুন্দর ও সুগঠিত ফরম্যাটে রূপান্তর করে।"
    },
    "fallback_dispatcher": {
        "title": "Fallback Dispatcher (Phase 2 -> Phase 3)",
        "phase": "Fallback Bridge",
        "color": "#ef4444",
        "description": "SQL কুয়েরিতে ০ রো পাওয়া গেলে স্বয়ংক্রিয়ভাবে SQL Retrieve (ভেক্টর/সেমান্টিক) পাথে সুইচ করে।"
    },
    "sql_retrieve_check": {
        "title": "SQL Retrieve Check (Phase 3)",
        "phase": "Phase 3 - SQL Retrieve",
        "color": "#8b5cf6",
        "description": "ডকুমেন্ট সার্চের যোগ্যতা এবং কোনো মিসিং ইনফরমেশন আছে কিনা যাচাই করে।"
    },
    "sql_retrieve_create": {
        "title": "SQL Retrieve Query Creator (Phase 3)",
        "phase": "Phase 3 - SQL Retrieve",
        "color": "#8b5cf6",
        "description": "হাইব্রিড সার্চের (BM25 + Semantic) জন্য কীওয়ার্ড এবং অপ্টিমাইজড সার্চ স্ট্রিং তৈরি করে।"
    },
    "sql_retrieve_context": {
        "title": "SQL Retrieve Context (Phase 3)",
        "phase": "Phase 3 - SQL Retrieve",
        "color": "#8b5cf6",
        "description": "PostgreSQL documents টেবিলে ভেক্টর এম্বেডিং এবং BM25 হাইব্রিড সার্চ চালিয়ে প্রাসঙ্গিক ডকুমেন্ট খুঁজে আনে।"
    },
    "evidence_verification": {
        "title": "Evidence Verification & Reasoning",
        "phase": "Verification Guardrail",
        "color": "#06b6d4",
        "description": "উত্তর তৈরির পূর্বে সংগৃহীত কনটেক্সটের প্রমাণ, সময় এবং সত্যতা নিখুঁতভাবে যাচাই করে।"
    },
    "sub_query_router_node": {
        "title": "Central Query Router & Fallback",
        "phase": "Central Routing",
        "color": "#6366f1",
        "description": "কনটেক্সট পাওয়া গেলে রেসপন্স নোডে পাঠায়। আর SQL Retrieve-এ কোনো তথ্য না পাওয়া গেলে সরাসরি Web Search-এ ফলব্যাক করে!"
    },
    "sql_retrieve_response": {
        "title": "SQL Retrieve Response (Phase 3)",
        "phase": "Phase 3 - SQL Retrieve",
        "color": "#8b5cf6",
        "description": "যাচাইকৃত কনটেক্সটের উপর ভিত্তি করে LLM দিয়ে নির্ভুল উত্তর প্রস্তুত করে।"
    },
    "sql_retrieve_support_check": {
        "title": "Support & Hallucination Check (Phase 3)",
        "phase": "Phase 3 - SQL Retrieve",
        "color": "#8b5cf6",
        "description": "উত্তরে কোনো হ্যালুসিনেশন আছে কিনা যাচাই করে। সাপোর্ট না পেলে বা রিট্রাই শেষ হলে স্বয়ংক্রিয়ভাবে Web Search-এ চলে যায়।"
    },
    "web_search_rewrite": {
        "title": "Web Search Query Rewrite (Phase 4)",
        "phase": "Phase 4 - Web Search",
        "color": "#f97316",
        "description": "DuckDuckGo বা বাইরের ওয়েবে অনুসন্ধানের জন্য অপ্টিমাইজড ইংরেজি কুয়েরি তৈরি করে।"
    },
    "web_search_docs": {
        "title": "Web Search Docs (Phase 4)",
        "phase": "Phase 4 - Web Search",
        "color": "#f97316",
        "description": "ইন্টারনেট/ওয়েব সার্চ চালিয়ে রিয়েল-টাইম প্রাসঙ্গিক ওয়েব পেজ ও স্নsnippet সংগ্রহ করে।"
    },
    "web_search_response": {
        "title": "Web Search Response (Phase 4)",
        "phase": "Phase 4 - Web Search",
        "color": "#f97316",
        "description": "ওয়েব থেকে প্রাপ্ত তথ্যের ভিত্তিতে ব্যবহারকারীর মূল ভাষায় পূর্ণাঙ্গ উত্তর তৈরি করে।"
    },
    "web_search_support_check": {
        "title": "Web Search Support Check (Phase 4)",
        "phase": "Phase 4 - Web Search",
        "color": "#f97316",
        "description": "ওয়েব সার্চের উত্তর সংগৃহীত তথ্যের সাথে সামঞ্জস্যপূর্ণ কিনা যাচাই করে।"
    },
    "hybrid_depth_check": {
        "title": "Hybrid Depth Check (Phase 5)",
        "phase": "Phase 5 - Hybrid / Map-Reduce",
        "color": "#ec4899",
        "description": "সাব-কুয়েরির গভীরতা যেন লিমিট অতিক্রম না করে তা নিশ্চিত করে।"
    },
    "create_sub_questions": {
        "title": "Create Sub Questions (Phase 5)",
        "phase": "Phase 5 - Hybrid / Map-Reduce",
        "color": "#ec4899",
        "description": "জটিল প্রশ্নকে একাধিক ছোট ছোট স্বাধীন প্রশ্নে বিভক্ত করে।"
    },
    "append_sub_answer": {
        "title": "Append Sub Answer (Phase 5)",
        "phase": "Phase 5 - Hybrid / Map-Reduce",
        "color": "#ec4899",
        "description": "প্যারালাল সাব-কুয়েরিগুলো থেকে প্রাপ্ত উত্তরগুলো সংগ্রহ করে যোগ করে।"
    },
    "merge_sub_answers": {
        "title": "Merge Sub Answers (Phase 5)",
        "phase": "Phase 5 - Hybrid / Map-Reduce",
        "color": "#ec4899",
        "description": "সকল সাব-উত্তরকে একত্রিত করে একটি সমন্বিত পূর্ণাঙ্গ উত্তর তৈরি করে।"
    },
    "merge_support_check": {
        "title": "Merge Support Check (Phase 5)",
        "phase": "Phase 5 - Hybrid / Map-Reduce",
        "color": "#ec4899",
        "description": "একত্রিত উত্তরের সত্যতা ও প্রাসঙ্গিকতা যাচাই করে।"
    },
    "merge_retry_check": {
        "title": "Merge Retry Check (Phase 5)",
        "phase": "Phase 5 - Hybrid / Map-Reduce",
        "color": "#ec4899",
        "description": "প্রয়োজনে পুনরায় মার্জ করার সুযোগ দেয় বা উত্তর চূড়ান্ত করে।"
    },
    "no_answer_found": {
        "title": "No Answer Found",
        "phase": "Final State",
        "color": "#64748b",
        "description": "কোনো উৎসেই তথ্য পাওয়া না গেলে মার্জিতভাবে উত্তর পাওয়া যায়নি বলে জানায়।"
    }
}

import json

html_content = f"""<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CNPI Hybrid RAG - Live Architecture Graph</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #3b82f6;
            --success: #10b981;
            --purple: #8b5cf6;
            --orange: #f97316;
            --pink: #ec4899;
            --cyan: #06b6d4;
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
        body {{
            background: var(--bg-color);
            color: var(--text-main);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }}
        header {{
            background: rgba(30, 41, 59, 0.9);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 10;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .brand-badge {{
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            color: white;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 20px;
            letter-spacing: 0.5px;
        }}
        .brand h1 {{
            font-size: 18px;
            font-weight: 600;
        }}
        .controls {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        button {{
            background: var(--card-bg);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        button:hover {{
            background: #334155;
            border-color: #475569;
        }}
        .main-container {{
            flex: 1;
            display: flex;
            position: relative;
            overflow: hidden;
        }}
        #graph-container {{
            flex: 1;
            height: 100%;
            overflow: hidden;
            display: flex;
            justify-content: center;
            align-items: center;
            background: radial-gradient(#1e293b 1px, transparent 1px);
            background-size: 24px 24px;
        }}
        #graph-svg {{
            width: 100%;
            height: 100%;
        }}
        .sidebar {{
            width: 360px;
            background: var(--card-bg);
            border-left: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            padding: 20px;
            gap: 16px;
            z-index: 5;
        }}
        .legend {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .legend-title {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
            padding: 6px 10px;
            border-radius: 6px;
            background: rgba(15, 23, 42, 0.4);
        }}
        .legend-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            flex-shrink: 0;
        }}
        .fallback-banner {{
            background: rgba(249, 115, 22, 0.12);
            border: 1px solid rgba(249, 115, 22, 0.35);
            padding: 12px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.5;
            color: #fdba74;
        }}
        .fallback-banner strong {{
            color: #ffedd5;
            display: block;
            margin-bottom: 4px;
        }}
        .node-details-card {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
            font-size: 13px;
        }}
        .node-details-card h3 {{
            font-size: 15px;
            margin-bottom: 6px;
            color: #60a5fa;
        }}
        .node-details-card .node-phase {{
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        .node-details-card p {{
            line-height: 1.5;
            color: #cbd5e1;
        }}
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <span class="brand-badge">LANGGRAPH</span>
            <h1>CNPI Hybrid RAG - Architecture Graph</h1>
        </div>
        <div class="controls">
            <button onclick="panZoomInstance.zoomIn()">🔍 Zoom In</button>
            <button onclick="panZoomInstance.zoomOut()">🔍 Zoom Out</button>
            <button onclick="panZoomInstance.resetZoom(); panZoomInstance.center();">↺ Reset</button>
            <button onclick="window.open('graph.png', '_blank')">🖼 Open PNG</button>
        </div>
    </header>

    <div class="main-container">
        <div id="graph-container">
            <div id="graph-svg" class="mermaid">
{graph_mermaid}
            </div>
        </div>

        <aside class="sidebar">
            <div class="fallback-banner">
                <strong>⚡ Dynamic Fallback Active:</strong>
                SQL Retrieve পাথে কনটেক্সট বা উত্তর না পাওয়া গেলে এখন সরাসরি <code>web_search_rewrite</code> নোডে চলে যাবে।
            </div>

            <div class="legend">
                <div class="legend-title">Path Architecture Phases</div>
                <div class="legend-item"><span class="legend-dot" style="background:#3b82f6;"></span>Phase 1: Entry & Router</div>
                <div class="legend-item"><span class="legend-dot" style="background:#10b981;"></span>Phase 2: SQL Query Path</div>
                <div class="legend-item"><span class="legend-dot" style="background:#8b5cf6;"></span>Phase 3: SQL Retrieve (Hybrid DB)</div>
                <div class="legend-item"><span class="legend-dot" style="background:#f97316;"></span>Phase 4: Web Search (External)</div>
                <div class="legend-item"><span class="legend-dot" style="background:#ec4899;"></span>Phase 5: Hybrid / Map-Reduce</div>
                <div class="legend-item"><span class="legend-dot" style="background:#06b6d4;"></span>Guardrail: Evidence Verification</div>
            </div>

            <div id="node-info-container">
                <div class="legend-title">Node Inspector</div>
                <div class="node-details-card" id="node-details">
                    <p style="color:var(--text-muted); font-style:italic;">গ্রাফের যেকোনো নোডে ক্লিক করুন তার দায়িত্ব ও বিস্তারিত দেখার জন্য।</p>
                </div>
            </div>
        </aside>
    </div>

    <script>
        const nodeMetadata = {json.dumps(NODE_INFO, ensure_ascii=False)};
        let panZoomInstance = null;

        mermaid.initialize({{
            startOnLoad: true,
            theme: 'dark',
            securityLevel: 'loose',
            flowchart: {{
                useMaxWidth: false,
                htmlLabels: true,
                curve: 'basis'
            }}
        }});

        window.addEventListener('load', () => {{
            setTimeout(() => {{
                const svgElement = document.querySelector('#graph-svg svg');
                if (svgElement) {{
                    svgElement.style.width = '100%';
                    svgElement.style.height = '100%';
                    panZoomInstance = svgPanZoom(svgElement, {{
                        zoomEnabled: true,
                        controlIconsEnabled: false,
                        fit: true,
                        center: true,
                        minZoom: 0.2,
                        maxZoom: 10
                    }});

                    // Attach click events on nodes
                    document.querySelectorAll('g.node').forEach(node => {{
                        const id = node.id.replace(/^flowchart-/, '').split('-')[0];
                        node.style.cursor = 'pointer';
                        node.addEventListener('click', () => {{
                            showNodeDetails(id);
                        }});
                    }});
                }}
            }}, 800);
        }});

        function showNodeDetails(nodeId) {{
            const card = document.getElementById('node-details');
            const info = nodeMetadata[nodeId];
            if (info) {{
                card.innerHTML = `
                    <div class="node-phase" style="color:${{info.color}};">${{info.phase}}</div>
                    <h3>${{info.title}}</h3>
                    <p>${{info.description}}</p>
                    <div style="margin-top:10px; font-size:11px; color:#94a3b8;">
                        <code>ID: ${{nodeId}}</code>
                    </div>
                `;
            }} else {{
                card.innerHTML = `
                    <div class="node-phase">NODE</div>
                    <h3>${{nodeId}}</h3>
                    <p>Standard workflow execution node in LangGraph.</p>
                `;
            }}
        }}
    </script>
</body>
</html>
"""

html_path = project_root / "view_graph.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✓ Interactive HTML graph saved to: {html_path}")

# Open in browser if running interactively
if len(sys.argv) > 1 and sys.argv[1] == "--no-browser":
    pass
else:
    print("Opening graph in default web browser...")
    webbrowser.open(str(html_path.resolve()))
