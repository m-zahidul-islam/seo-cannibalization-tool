"""
Professional SEO Audit Tool v2.0
By M Zahidul Islam | SEO & Search Visibility Specialist
─────────────────────────────────────────────────────
pip install streamlit pandas requests beautifulsoup4 thefuzz
            lxml plotly openpyxl anthropic python-Levenshtein
"""

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.express as px
import plotly.graph_objects as go
import io
import json
import time
import logging
import re
import anthropic

# ─────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────
IGNORE_SITEMAP_KEYWORDS = ["image", "video", "attachment", "media", "gallery", "css", "js"]
IGNORE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".webp", ".svg", ".mp4", ".mp3"]
HEADERS = {"User-Agent": "Mozilla/5.0 (SEO Auditor Bot/2.0)"}

# ─────────────────────────────────────────────────────────────────
# 1. SITEMAP FETCHER — Iterative
# ─────────────────────────────────────────────────────────────────
def get_filtered_sitemap_urls(sitemap_url: str) -> list[str]:
    visited, queue, all_urls = set(), [sitemap_url], set()
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        try:
            res = requests.get(current, headers=HEADERS, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.content, "xml")
            for loc in soup.find_all("loc"):
                link = loc.text.strip()
                if link.endswith(".xml"):
                    if not any(kw in link.lower() for kw in IGNORE_SITEMAP_KEYWORDS):
                        queue.append(link)
                elif not any(link.lower().endswith(ext) for ext in IGNORE_EXTENSIONS):
                    all_urls.add(link)
        except Exception as e:
            logger.warning(f"Sitemap error [{current}]: {e}")
            st.warning(f"⚠️ Could not fetch: `{current}`")
    return list(all_urls)


# ─────────────────────────────────────────────────────────────────
# 2. DEEP SEO SCRAPER
# ─────────────────────────────────────────────────────────────────
def detect_page_type(url: str) -> str:
    u = url.lower()
    if any(p in u for p in ["/product/", "/products/"]): return "Product"
    if any(p in u for p in ["/product-category/", "/category/", "/shop/", "/collection/", "/catalog/"]): return "Category"
    if any(p in u for p in ["/blog/", "/post/", "/news/", "/article/", "/insight/"]): return "Blog"
    if u.rstrip("/").count("/") <= 3: return "Static/Core"
    return "Other"

def scrape_seo_data(url: str) -> dict:
    result = {
        "URL": url, "Type": detect_page_type(url),
        "Status Code": "Error", "Response Time (ms)": 0,
        # Title
        "Title": "Missing", "Title Length": 0,
        # Meta
        "Meta Description": "Missing", "Meta Desc Length": 0,
        # Headings
        "H1": "Missing", "H1 Count": 0, "H2 Count": 0, "H3 Count": 0,
        # Technical
        "Canonical": "Not Set", "Robots Meta": "index",
        # Content
        "Word Count": 0,
        # Schema
        "Schema Types": "None",
        # Open Graph
        "OG Title": "Missing", "OG Description": "Missing", "OG Image": "Missing",
        # Images
        "Total Images": 0, "Images Missing Alt": 0,
        # Links
        "Internal Links": 0, "External Links": 0,
        # Score & Issues
        "SEO Score": 100,
        "Issues": [],
    }

    try:
        start = time.time()
        res = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        result["Response Time (ms)"] = round((time.time() - start) * 1000)
        result["Status Code"] = res.status_code

        if res.status_code != 200:
            result["Issues"].append(f"Non-200 Status: {res.status_code}")
            result["SEO Score"] -= 40
            result["Issues"] = "; ".join(result["Issues"])
            return result

        soup = BeautifulSoup(res.text, "html.parser")
        domain = re.findall(r"https?://[^/]+", url)[0] if re.findall(r"https?://[^/]+", url) else ""

        # ── Title ──────────────────────────────────────────────
        title_tag = soup.find("title")
        title = title_tag.string.strip() if title_tag and title_tag.string else ""
        result["Title"] = title if title else "Missing"
        result["Title Length"] = len(title)
        if not title:
            result["Issues"].append("Missing Title"); result["SEO Score"] -= 20
        elif len(title) > 60:
            result["Issues"].append("Title Too Long (>60 chars)"); result["SEO Score"] -= 5
        elif len(title) < 30:
            result["Issues"].append("Title Too Short (<30 chars)"); result["SEO Score"] -= 5

        # ── Meta Description ───────────────────────────────────
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            md = meta_tag.get("content", "").strip()
            result["Meta Description"] = md or "Empty"
            result["Meta Desc Length"] = len(md)
            if not md:
                result["Issues"].append("Empty Meta Description"); result["SEO Score"] -= 10
            elif len(md) > 160:
                result["Issues"].append("Meta Desc Too Long (>160)"); result["SEO Score"] -= 3
            elif len(md) < 70:
                result["Issues"].append("Meta Desc Too Short (<70)"); result["SEO Score"] -= 3
        else:
            result["Issues"].append("Missing Meta Description"); result["SEO Score"] -= 10

        # ── Headings ───────────────────────────────────────────
        h1s = soup.find_all("h1")
        result["H1 Count"] = len(h1s)
        result["H2 Count"] = len(soup.find_all("h2"))
        result["H3 Count"] = len(soup.find_all("h3"))
        if not h1s:
            result["H1"] = "Missing"; result["Issues"].append("Missing H1"); result["SEO Score"] -= 15
        elif len(h1s) > 1:
            result["H1"] = h1s[0].get_text(strip=True)
            result["Issues"].append(f"Multiple H1s ({len(h1s)})"); result["SEO Score"] -= 8
        else:
            result["H1"] = h1s[0].get_text(strip=True)

        # ── Canonical ──────────────────────────────────────────
        can_tag = soup.find("link", rel="canonical")
        if can_tag:
            canonical = can_tag.get("href", "").strip()
            result["Canonical"] = canonical or "Empty"
            if canonical and canonical.rstrip("/") != url.rstrip("/"):
                result["Issues"].append("Canonical → Different URL"); result["SEO Score"] -= 10
        else:
            result["Issues"].append("No Canonical Tag"); result["SEO Score"] -= 5

        # ── Robots Meta ────────────────────────────────────────
        robots_tag = soup.find("meta", attrs={"name": "robots"})
        if robots_tag:
            robots = robots_tag.get("content", "index").lower()
            result["Robots Meta"] = robots
            if "noindex" in robots:
                result["Issues"].append("⚠️ NOINDEX — Excluded from Google"); result["SEO Score"] -= 50

        # ── Word Count ─────────────────────────────────────────
        body = soup.find("body")
        if body:
            result["Word Count"] = len(body.get_text(separator=" ", strip=True).split())
        if result["Word Count"] < 300:
            result["Issues"].append("Thin Content (<300 words)"); result["SEO Score"] -= 8

        # ── Schema / Structured Data ───────────────────────────
        schema_scripts = soup.find_all("script", type="application/ld+json")
        schema_types = []
        for s in schema_scripts:
            try:
                data = json.loads(s.string or "")
                if isinstance(data, list):
                    schema_types.extend([d.get("@type", "") for d in data if isinstance(d, dict)])
                elif isinstance(data, dict):
                    st_val = data.get("@type", "")
                    if isinstance(st_val, list): schema_types.extend(st_val)
                    elif st_val: schema_types.append(st_val)
            except Exception:
                pass
        result["Schema Types"] = ", ".join(schema_types) if schema_types else "None"
        if not schema_types:
            result["Issues"].append("No Schema Markup"); result["SEO Score"] -= 5

        # ── Open Graph ─────────────────────────────────────────
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_img = soup.find("meta", property="og:image")
        result["OG Title"] = og_title["content"].strip() if og_title and og_title.get("content") else "Missing"
        result["OG Description"] = og_desc["content"].strip() if og_desc and og_desc.get("content") else "Missing"
        result["OG Image"] = og_img["content"].strip() if og_img and og_img.get("content") else "Missing"
        if result["OG Title"] == "Missing":
            result["Issues"].append("Missing OG Title"); result["SEO Score"] -= 3
        if result["OG Image"] == "Missing":
            result["Issues"].append("Missing OG Image"); result["SEO Score"] -= 3

        # ── Images Alt Text ────────────────────────────────────
        images = soup.find_all("img")
        result["Total Images"] = len(images)
        missing_alt = sum(1 for img in images if not img.get("alt", "").strip())
        result["Images Missing Alt"] = missing_alt
        if missing_alt > 0:
            result["Issues"].append(f"{missing_alt} Images Missing Alt Text"); result["SEO Score"] -= min(missing_alt * 2, 10)

        # ── Internal / External Links ──────────────────────────
        all_links = soup.find_all("a", href=True)
        internal = sum(1 for a in all_links if domain in a["href"] or a["href"].startswith("/"))
        external = sum(1 for a in all_links if a["href"].startswith("http") and domain not in a["href"])
        result["Internal Links"] = internal
        result["External Links"] = external

        # ── Response Time Warning ──────────────────────────────
        if result["Response Time (ms)"] > 3000:
            result["Issues"].append(f"Slow Response ({result['Response Time (ms)']}ms)"); result["SEO Score"] -= 5

    except requests.exceptions.Timeout:
        result["Issues"].append("Request Timeout"); result["SEO Score"] = 0
    except requests.exceptions.ConnectionError:
        result["Issues"].append("Connection Error"); result["SEO Score"] = 0
    except Exception as e:
        result["Issues"].append(f"Scrape Error: {str(e)[:80]}"); result["SEO Score"] = 0

    result["SEO Score"] = max(0, result["SEO Score"])
    result["Issues"] = "; ".join(result["Issues"]) if result["Issues"] else "✅ None"
    return result


# ─────────────────────────────────────────────────────────────────
# 3. PARALLEL SCRAPER
# ─────────────────────────────────────────────────────────────────
def scrape_all_urls(urls: list[str], max_workers: int = 10) -> list[dict]:
    results = [None] * len(urls)
    progress = st.progress(0)
    status = st.empty()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(scrape_seo_data, url): i for i, url in enumerate(urls)}
        done = 0
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = {"URL": urls[idx], "Issues": f"Thread Error: {e}", "SEO Score": 0}
            done += 1
            progress.progress(done / len(urls))
            status.caption(f"Scanning {done}/{len(urls)} pages...")
    status.empty()
    return [r for r in results if r is not None]


# ─────────────────────────────────────────────────────────────────
# 4. CANNIBALIZATION DETECTION
# ─────────────────────────────────────────────────────────────────
def detect_cannibalization(df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)
    conflict_url = ["None"] * n
    conflict_score = [0] * n
    severity = ["🟢 OK"] * n
    cannibal_action = ["No cannibalization detected."] * n

    for i, j in combinations(range(n), 2):
        score = fuzz.token_sort_ratio(str(df.at[i, "Title"]), str(df.at[j, "Title"]))
        if score > 80:
            if score > conflict_score[i]:
                conflict_score[i] = score
                conflict_url[i] = df.at[j, "URL"]
            if score > conflict_score[j]:
                conflict_score[j] = score
                conflict_url[j] = df.at[i, "URL"]

    for i in range(n):
        if conflict_url[i] != "None":
            s = conflict_score[i]
            if s >= 95:
                severity[i] = "🔴 CRITICAL"
                cannibal_action[i] = f"Consolidate or redirect to: {conflict_url[i]}"
            elif s >= 85:
                severity[i] = "🟠 HIGH"
                cannibal_action[i] = "Rewrite title to target a distinct search intent."
            else:
                severity[i] = "🟡 MEDIUM"
                cannibal_action[i] = "Review content overlap and differentiate focus keywords."

    df["Cannibal URL"] = conflict_url
    df["Cannibal Score"] = conflict_score
    df["Cannibalization"] = severity
    df["Cannibal Action"] = cannibal_action
    return df


# ─────────────────────────────────────────────────────────────────
# 5. AI ACTION PLAN via Anthropic API
# ─────────────────────────────────────────────────────────────────
def generate_ai_action_plan(issues_summary: str, api_key: str) -> str:
    """
    Sends a batch of SEO issues to Claude and gets a prioritized action plan.
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are an expert SEO strategist. Below is a summary of SEO issues found across a website audit.

{issues_summary}

Please provide:
1. Top 5 highest-priority fixes with clear reasoning
2. Quick wins (can fix in <1 hour)
3. Long-term strategy recommendations

Be specific, concise, and actionable. Format with clear headings."""
                }
            ]
        )
        return message.content[0].text
    except anthropic.AuthenticationError:
        return "❌ Invalid API Key. Please check your Anthropic API key."
    except Exception as e:
        return f"❌ AI Error: {str(e)}"


def build_issues_summary(df: pd.DataFrame) -> str:
    total = len(df)
    avg_score = round(df["SEO Score"].mean(), 1) if "SEO Score" in df.columns else "N/A"

    issue_counts = {}
    for issues_str in df["Issues"].dropna():
        for issue in issues_str.split(";"):
            issue = issue.strip()
            if issue and issue != "✅ None":
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

    top_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    issue_lines = "\n".join([f"- {issue}: {count} pages" for issue, count in top_issues])

    noindex = df["Robots Meta"].str.contains("noindex", na=False).sum() if "Robots Meta" in df.columns else 0
    missing_schema = (df["Schema Types"] == "None").sum() if "Schema Types" in df.columns else 0
    missing_h1 = (df["H1"] == "Missing").sum() if "H1" in df.columns else 0

    return f"""Website SEO Audit Summary
Total Pages Audited: {total}
Average SEO Score: {avg_score}/100
Noindex Pages: {noindex}
Pages Missing Schema: {missing_schema}
Pages Missing H1: {missing_h1}

Top Issues Found:
{issue_lines}
"""


# ─────────────────────────────────────────────────────────────────
# 6. CHARTS
# ─────────────────────────────────────────────────────────────────
def render_charts(df: pd.DataFrame):
    col1, col2 = st.columns(2)

    with col1:
        score_bins = pd.cut(df["SEO Score"], bins=[0, 40, 60, 80, 100],
                            labels=["0-40 🔴", "41-60 🟠", "61-80 🟡", "81-100 🟢"])
        score_dist = score_bins.value_counts().sort_index()
        fig = px.bar(x=score_dist.index, y=score_dist.values,
                     color=score_dist.index,
                     color_discrete_map={"0-40 🔴": "#e74c3c", "41-60 🟠": "#e67e22",
                                         "61-80 🟡": "#f1c40f", "81-100 🟢": "#2ecc71"},
                     labels={"x": "SEO Score Range", "y": "Page Count"},
                     title="SEO Score Distribution")
        fig.update_layout(showlegend=False, height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        type_counts = df["Type"].value_counts()
        fig2 = px.pie(values=type_counts.values, names=type_counts.index,
                      title="Pages by Type", hole=0.4)
        fig2.update_layout(height=320)
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        issue_counts = {}
        for issues_str in df["Issues"].dropna():
            for issue in issues_str.split(";"):
                issue = issue.strip()
                if issue and issue != "✅ None":
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1
        if issue_counts:
            top = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:8]
            fig3 = px.bar(x=[t[1] for t in top], y=[t[0] for t in top],
                          orientation="h", title="Top SEO Issues",
                          labels={"x": "# Pages Affected", "y": "Issue"},
                          color_discrete_sequence=["#e74c3c"])
            fig3.update_layout(height=340, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig3, use_container_width=True)

    with col4:
        if "Response Time (ms)" in df.columns:
            fig4 = px.histogram(df, x="Response Time (ms)", nbins=20,
                                title="Page Response Time Distribution",
                                color_discrete_sequence=["#3498db"])
            fig4.add_vline(x=1000, line_dash="dash", line_color="orange", annotation_text="1s target")
            fig4.add_vline(x=3000, line_dash="dash", line_color="red", annotation_text="3s warning")
            fig4.update_layout(height=340)
            st.plotly_chart(fig4, use_container_width=True)


# ─────────────────────────────────────────────────────────────────
# 7. STREAMLIT UI
# ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="SEO Audit Tool v2 | Zahidul Islam", layout="wide", page_icon="🛡️")

# Header
st.markdown("""
<div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
     padding: 2rem; border-radius: 12px; margin-bottom: 1.5rem;'>
    <h1 style='color: white; margin: 0; font-size: 2rem;'>🛡️ Professional SEO Audit Tool</h1>
    <p style='color: #a0aec0; margin: 0.5rem 0 0 0;'>
        Deep Technical + On-Page + Schema + OG Audit · AI-Powered Action Plan
    </p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar Config ──────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    sitemap_input = st.text_input("Sitemap URL", placeholder="https://example.com/sitemap_index.xml")
    max_urls = st.number_input("Max Pages to Audit", 50, 2000, 500, 50)
    max_workers = st.slider("Parallel Requests", 3, 20, 8)

    st.divider()
    st.subheader("🤖 AI Action Plan")
    st.caption("Optional: Provide your Anthropic API key to generate an AI-powered priority action plan.")
    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
    enable_ai = st.checkbox("Enable AI Action Plan", value=bool(api_key))

    st.divider()
    st.subheader("🔍 Filters")
    filter_severity = st.multiselect(
        "Filter by Cannibalization",
        options=["🔴 CRITICAL", "🟠 HIGH", "🟡 MEDIUM", "🟢 OK"],
        default=[]
    )
    filter_type = st.multiselect("Filter by Page Type", options=["Product", "Category", "Blog", "Static/Core", "Other"], default=[])
    min_score = st.slider("Minimum SEO Score", 0, 100, 0)

    run_audit = st.button("🚀 Run Audit", type="primary", use_container_width=True)

# ── Main Logic ──────────────────────────────────────────────────
if run_audit:
    if not sitemap_input.strip():
        st.error("Please enter a sitemap URL.")
        st.stop()

    # Fetch sitemap
    with st.spinner("📡 Fetching sitemap..."):
        all_links = get_filtered_sitemap_urls(sitemap_input.strip())

    if not all_links:
        st.error("❌ No pages found in sitemap. Please verify the URL.")
        st.stop()

    urls_to_audit = all_links[:max_urls]
    st.success(f"✅ Found **{len(all_links)}** pages. Auditing **{len(urls_to_audit)}**.")

    # Scrape
    st.subheader("⏳ Auditing Pages...")
    raw_results = scrape_all_urls(urls_to_audit, max_workers=max_workers)
    df = pd.DataFrame(raw_results)

    # Cannibalization
    with st.spinner("🔍 Detecting cannibalization..."):
        df = detect_cannibalization(df)

    # Score label
    def score_label(s):
        if s >= 80: return "🟢 Good"
        if s >= 60: return "🟡 Needs Work"
        if s >= 40: return "🟠 Poor"
        return "🔴 Critical"
    df["Score Label"] = df["SEO Score"].apply(score_label)

    # Apply sidebar filters
    filtered_df = df.copy()
    if filter_severity:
        filtered_df = filtered_df[filtered_df["Cannibalization"].isin(filter_severity)]
    if filter_type:
        filtered_df = filtered_df[filtered_df["Type"].isin(filter_type)]
    filtered_df = filtered_df[filtered_df["SEO Score"] >= min_score]

    # ── Summary Metrics ────────────────────────────────────────
    st.subheader("📊 Audit Overview")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total Pages", len(df))
    m2.metric("Avg SEO Score", f"{df['SEO Score'].mean():.0f}/100")
    m3.metric("🔴 Critical Issues", len(df[df["Cannibalization"] == "🔴 CRITICAL"]))
    m4.metric("⚠️ Noindex", df["Robots Meta"].str.contains("noindex", na=False).sum())
    m5.metric("No Schema", (df["Schema Types"] == "None").sum())
    m6.metric("Missing H1", (df["H1"] == "Missing").sum())

    # ── Charts ────────────────────────────────────────────────
    render_charts(df)

    # ── Tabbed Data ───────────────────────────────────────────
    st.subheader("📋 Detailed Results")
    tab1, tab2, tab3, tab4 = st.tabs(["Full Audit", "⚠️ Issues Only", "🔁 Cannibalization", "🧠 Schema & OG"])

    # Column sets
    core_cols = ["Type", "Score Label", "SEO Score", "URL", "Status Code", "Title",
                 "Title Length", "Meta Description", "Meta Desc Length",
                 "H1", "H1 Count", "H2 Count", "Word Count",
                 "Canonical", "Robots Meta", "Response Time (ms)", "Issues"]

    schema_og_cols = ["URL", "Type", "Schema Types", "OG Title", "OG Description",
                      "OG Image", "Total Images", "Images Missing Alt",
                      "Internal Links", "External Links"]

    cannibal_cols = ["URL", "Title", "Cannibalization", "Cannibal Score",
                     "Cannibal URL", "Cannibal Action"]

    with tab1:
        show_df = filtered_df[[c for c in core_cols if c in filtered_df.columns]]
        st.dataframe(show_df, use_container_width=True, height=500)

    with tab2:
        issues_df = filtered_df[filtered_df["Issues"] != "✅ None"]
        st.info(f"{len(issues_df)} pages have at least one issue.")
        st.dataframe(issues_df[[c for c in core_cols if c in issues_df.columns]],
                     use_container_width=True, height=500)

    with tab3:
        cannibal_df = df[df["Cannibalization"] != "🟢 OK"]
        st.info(f"{len(cannibal_df)} pages have title cannibalization.")
        st.dataframe(cannibal_df[[c for c in cannibal_cols if c in cannibal_df.columns]],
                     use_container_width=True, height=500)

    with tab4:
        st.dataframe(filtered_df[[c for c in schema_og_cols if c in filtered_df.columns]],
                     use_container_width=True, height=500)

    # ── AI Action Plan ─────────────────────────────────────────
    if enable_ai and api_key:
        st.subheader("🤖 AI-Powered Action Plan")
        with st.spinner("Claude is analyzing your audit data..."):
            summary = build_issues_summary(df)
            ai_plan = generate_ai_action_plan(summary, api_key)
        st.markdown(ai_plan)
    elif enable_ai and not api_key:
        st.warning("🔑 Please enter your Anthropic API key in the sidebar to enable AI analysis.")

    # ── Excel Export ───────────────────────────────────────────
    st.subheader("📥 Export Report")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Full Audit")
        df[df["Issues"] != "✅ None"].to_excel(writer, index=False, sheet_name="On-Page Issues")
        df[df["Cannibalization"] != "🟢 OK"].to_excel(writer, index=False, sheet_name="Cannibalization")
        df[[c for c in schema_og_cols if c in df.columns]].to_excel(writer, index=False, sheet_name="Schema & OG")
    output.seek(0)

    st.download_button(
        label="📥 Download Full Report (4 Sheets)",
        data=output.getvalue(),
        file_name="SEO_Audit_Pro_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ── Footer ─────────────────────────────────────────────────────
st.markdown("---")
st.caption("© M Zahidul Islam | SEO & Search Visibility Specialist | v2.0")
