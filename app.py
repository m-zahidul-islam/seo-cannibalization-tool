import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io
import re

# --- 1. Universal Sitemap Fetcher ---
def get_all_urls(url):
    urls = []
    ignore = ['image', 'video', 'attachment', 'media', 'css', 'js']
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
            if not any(link.lower().endswith(ext) for ext in ['.jpg', '.png', '.webp', '.pdf', '.svg']):
                urls.append(link)
    except: pass
    return list(set(urls))

# --- 2. Smart Keyword & Data Scraper ---
def scrape_universal_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        words = len(soup.get_text().split())
        
        # Keyword Extraction: টাইটেলের প্রথম ৩টি শব্দ
        clean_title = re.sub(r'[|,\-–—]', ' ', title).strip()
        kw = " ".join(clean_title.split()[:3]) if clean_title else "N/A"
        
        # Page Type Detection
        l = url.lower()
        if any(x in l for x in ['/product', '/item']): pt = "Product"
        elif any(x in l for x in ['/category', '/shop']): pt = "Category"
        elif any(x in l for x in ['/blog', '/post']): pt = "Blog"
        else: pt = "General Page"
        
        return title, words, pt, kw
    except: return "Error", 0, "Unknown", "N/A"

# --- 3. UI Setup ---
st.set_page_config(page_title="Zahidul's Universal Auditor", layout="wide")
st.title("🛡️ Universal SEO Cannibalization Tool")

target_url = st.text_input("Enter Sitemap URL:", value="https://sareemela.com/sitemap_index.xml")

if st.button("Run Professional Audit"):
    if target_url:
        with st.spinner("Analyzing site structure..."):
            all_links = get_all_urls(target_url)
            if all_links:
                st.info(f"Total Pages Found: {len(all_links)}")
                results = []
                p_bar = st.progress(0)
                
                # Processing links (Safety limit 500)
                process_limit = all_links[:500]
                for i, url in enumerate(process_limit):
                    t, w, pt, kw = scrape_universal_data(url)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt, "Keyword": kw})
                    p_bar.progress((i + 1) / len(process_limit))
                
                df_raw = pd.DataFrame(results)
                final_data = []
                for i, row in df_raw.iterrows():
                    status, pri, act, conf = "🟢 OK", "🟢 Maintain", "Keep Content.", "None"
                    for j, other in df_raw.iterrows():
                        if i != j and fuzz.token_sort_ratio(row['Title'], other['Title']) > 80:
                            conf = other['URL']
                            if row['Words'] < other['Words']:
                                status, pri, act = "🔴 CRITICAL", "🔴 P1 - Immediate", f"301 Redirect to: {other['URL']}"
                            else:
                                status, pri, act = "🟡 HIGH", "🟡 P2 - Weekly", "Rewrite Title/H1."
                            break
                    
                    final_data.append({
                        "Type": row['Type'], "Severity": status, "Primary Keyword": row['Keyword'],
                        "URL": row['URL'], "Conflicting URL": conf, "Title": row['Title'],
                        "Words": row['Words'], "Action Plan": act, "Priority": pri
                    })

                complete_df = pd.DataFrame(final_data)
                action_df = complete_df[complete_df['Severity'] != "🟢 OK"].copy()

                # --- Excel Output ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Full Audit')
                    action_df.to_excel(writer, index=False, sheet_name='Action Plan')

                st.success("Audit Complete!")
                st.dataframe(complete_df, use_container_width=True)
                st.download_button("📥 Download Styled Excel", output.getvalue(), "Universal_SEO_Audit.xlsx")
