import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io
import re

# --- 1. Sitemap Fetcher (Strict Filter) ---
def get_all_urls(url):
    urls = []
    ignore = ['image', 'video', 'attachment', 'media', 'gallery']
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            if link.endswith('.xml'):
                if not any(x in link.lower() for x in ignore):
                    urls.extend(get_all_urls(link))
                continue
            if not any(link.lower().endswith(ext) for ext in ['.jpg', '.png', '.webp', '.svg', '.pdf']):
                urls.append(link)
    except: pass
    return list(set(urls))

# --- 2. Keyword & Data Scraper ---
def scrape_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title Found"
        words = len(soup.get_text().split())
        
        # Categorization
        l = url.lower()
        if "/product/" in l: p_type = "Product"
        elif "/category/" in l or "/product-category/" in l: p_type = "Category"
        elif "/blog/" in l: p_type = "Blog"
        else: p_type = "Static Page"
        
        # Primary Keyword Extraction
        clean_kw = re.sub(r'[|,\-–—]|Saree Mela|SareeMela', '', title, flags=re.IGNORECASE).strip()
        kw = " ".join(clean_kw.split()[:3]) if clean_kw else "N/A"
        
        return title, words, p_type, kw
    except: return "Error", 0, "Unknown", "N/A"

# --- UI Layout ---
st.set_page_config(page_title="Zahidul's Pro Auditor", layout="wide")
st.title("🛡️ Professional SEO Auditor")

sitemap_url = st.text_input("Sitemap URL:", value="https://sareemela.com/sitemap_index.xml")

if st.button("Run Complete 138+ Page Audit"):
    if sitemap_url:
        with st.spinner("Processing... Please wait."):
            links = get_all_urls(sitemap_url)
            if links:
                results = []
                p_bar = st.progress(0)
                # Processing links
                for i, url in enumerate(links[:500]):
                    t, w, pt, kw = scrape_data(url)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt, "Keyword": kw})
                    p_bar.progress((i + 1) / len(links[:500]))
                
                df_raw = pd.DataFrame(results)
                final_audit = []
                for i, row in df_raw.iterrows():
                    # Default Status
                    status, pri, act, conf = "🟢 OK", "🟢 Maintain", "Keep.", "None"
                    
                    for j, other in df_raw.iterrows():
                        if i != j and fuzz.token_sort_ratio(row['Title'], other['Title']) > 80:
                            conf = other['URL']
                            if row['Words'] < other['Words']:
                                status, pri, act = "🔴 CRITICAL", "🔴 P1 - Today", f"Redirect to: {other['URL']}"
                            else:
                                status, pri, act = "🟡 HIGH", "🟡 P2 - This Week", "Rewrite Title."
                            break
                    
                    final_audit.append({
                        "Page Type": row['Type'], "Severity": status, "Primary Keyword": row['Keyword'],
                        "URL": row['URL'], "Conflicting URL": conf, "Page Title": row['Title'],
                        "Words": row['Words'], "Action Plan": act, "Priority": pri
                    })

                complete_df = pd.DataFrame(final_audit)
                action_plan_df = complete_df[complete_df['Severity'] != "🟢 OK"].copy()
                
                # --- Excel Download with Two Sheets ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Full Audit')
                    action_plan_df.to_excel(writer, index=False, sheet_name='Action Plan')
                
                st.success(f"Audit Complete! {len(links)} links found.")
                st.dataframe(complete_df, use_container_width=True)
                st.download_button("📥 Download Excel Report (Styled Circles)", output.getvalue(), "SEO_Report.xlsx")
