import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io
import re
from openpyxl.styles import PatternFill, Font

# --- 1. Smart Sitemap Fetcher ---
def get_filtered_urls(sitemap_url):
    urls = []
    ignore_list = ['image', 'video', 'attachment', 'media', 'gallery']
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(sitemap_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            if link.endswith('.xml'):
                if not any(word in link.lower() for word in ignore_list):
                    urls.extend(get_filtered_urls(link))
                continue
            if not any(link.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.svg']):
                urls.append(link)
    except: pass
    return list(set(urls))

# --- 2. Keyword Extractor (Simple NLP Logic) ---
def extract_primary_keyword(title):
    # টাইটেল থেকে অপ্রয়োজনীয় শব্দ বা ব্র্যান্ড নেম বাদ দিয়ে মেইন কিওয়ার্ড বের করা
    clean_title = re.sub(r'[|,\-–—]|Saree Mela|SareeMela', '', title, flags=re.IGNORECASE).strip()
    words = clean_title.split()
    # প্রথম ৩-৪টি শব্দকে সাধারণত মেইন কিওয়ার্ড ধরা হয়
    return " ".join(words[:4]) if words else "N/A"

# --- 3. Data Scraper ---
def scrape_seo_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        words = len(soup.get_text().split())
        
        link_low = url.lower()
        if "/product/" in link_low: p_type = "Product"
        elif "/category/" in link_low or "/shop/" in link_low: p_type = "Category"
        elif "/blog/" in link_low: p_type = "Blog"
        else: p_type = "Static/Core"
        
        return title, words, p_type
    except: return "Error", 0, "Unknown"

# --- 4. UI Setup ---
st.set_page_config(page_title="Zahidul's SEO Auditor Pro", layout="wide")
st.title("🛡️ Advanced SEO Auditor (Keyword & Color Coding)")

sitemap_input = st.text_input("Sitemap URL:", placeholder="https://sareemela.com/sitemap_index.xml")

if st.button("Generate Enhanced Report"):
    if sitemap_input:
        with st.spinner("Analyzing pages and extracting keywords..."):
            all_links = get_filtered_urls(sitemap_input)
            if all_links:
                results = []
                p_bar = st.progress(0)
                # Processing limit for stability (up to 500)
                process_links = all_links[:500]
                
                for i, url in enumerate(process_links):
                    t, w, pt = scrape_seo_data(url)
                    pk = extract_primary_keyword(t)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt, "Keyword": pk})
                    p_bar.progress((i + 1) / len(process_links))
                
                df_raw = pd.DataFrame(results)
                final_data = []
                
                for i, row in df_raw.iterrows():
                    sev, pri, act = "🟢 OK", "🟢 Maintain", "Keep."
                    conf = "None"
                    for j, other in df_raw.iterrows():
                        if i != j and fuzz.token_sort_ratio(row['Title'], other['Title']) > 80:
                            conf = other['URL']
                            if row['Words'] < other['Words']:
                                sev, pri, act = "🔴 CRITICAL", "🔴 P1 - Today", f"Redirect to: {other['URL']}"
                            else:
                                sev, pri, act = "🟠 HIGH", "🟠 P2 - This Week", "Rewrite Title."
                            break
                    
                    final_data.append({
                        "Page Type": row['Type'], 
                        "Severity": sev,
                        "Primary Keyword": row['Keyword'], # নতুন কলাম
                        "URL": row['URL'],
                        "Conflicting URL": conf, 
                        "Page Title": row['Title'], 
                        "Words": row['Words'],
                        "Action Plan": act, 
                        "Priority": pri
                    })

                complete_df = pd.DataFrame(final_data)
                
                # Excel Export with Colors
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Audit Report')
                    ws = writer.sheets['Audit Report']
                    
                    # Formatting Colors
                    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                    orange_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                    
                    for r_idx in range(2, ws.max_row + 1):
                        sev_cell = ws.cell(row=r_idx, column=2) # Severity Column
                        if "CRITICAL" in str(sev_cell.value):
                            sev_cell.fill = red_fill
                        elif "HIGH" in str(sev_cell.value):
                            sev_cell.fill = orange_fill
                
                st.success("Report Generated with Primary Keywords!")
                st.dataframe(complete_df, use_container_width=True)
                st.download_button("📥 Download Styled Excel", output.getvalue(), "SEO_Keyword_Audit.xlsx")
