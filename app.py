import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io
import re
from openpyxl.styles import PatternFill, Font, Alignment

# --- 1. Smart Sitemap Fetcher (Strict & Non-Recursive for Media) ---
def get_filtered_urls(sitemap_url):
    urls = []
    ignore_list = ['image', 'video', 'attachment', 'media', 'gallery']
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(sitemap_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            # If index sitemap, go deeper only for non-media ones
            if link.endswith('.xml'):
                if not any(word in link.lower() for word in ignore_list):
                    urls.extend(get_filtered_urls(link))
                continue
            # Skip media files
            if not any(link.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.svg', '.pdf']):
                urls.append(link)
    except: pass
    return list(set(urls))

# --- 2. Primary Keyword Extractor ---
def extract_keyword(url, title):
    # Extracting from Title (removing common brand/stop words)
    clean_title = re.sub(r'[|,\-–—]|Saree Mela|SareeMela|Home|Shop', '', title, flags=re.IGNORECASE).strip()
    words = clean_title.split()
    if words:
        return " ".join(words[:3]) # Taking first 3 words as Primary Keyword
    
    # Fallback: Extract from URL slug
    slug = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
    keyword = slug.replace('-', ' ').title()
    return keyword

# --- 3. SEO Data Scraper ---
def scrape_seo_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        words = len(soup.get_text().split())
        
        # Categorization
        link_low = url.lower()
        if "/product/" in link_low: p_type = "Product"
        elif "/category/" in link_low or "/shop/" in link_low: p_type = "Category"
        elif "/blog/" in link_low or "/post/" in link_low: p_type = "Blog"
        else: p_type = "Static/Core"
        
        return title, words, p_type
    except: return "Error", 0, "Unknown"

# --- 4. Streamlit UI ---
st.set_page_config(page_title="Zahidul's Pro SEO Auditor", layout="wide")
st.title("🛡️ Advanced SEO Auditor (Keywords & Color-Coded Excel)")
st.write("This version includes **Primary Keyword** extraction and **Styled Excel** downloads.")

sitemap_input = st.text_input("Enter Sitemap URL:", placeholder="https://sareemela.com/sitemap_index.xml")

if st.button("Generate Pro Report"):
    if sitemap_input:
        with st.spinner("Analyzing sitemap and extracting keywords..."):
            all_links = get_filtered_urls(sitemap_input)
            if all_links:
                results = []
                p_bar = st.progress(0)
                # Limit to 500 for performance stability
                process_limit = all_links[:500]
                
                for i, url in enumerate(process_limit):
                    t, w, pt = scrape_seo_data(url)
                    pk = extract_keyword(url, t)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt, "Keyword": pk})
                    p_bar.progress((i + 1) / len(process_limit))
                
                df_raw = pd.DataFrame(results)
                final_audit = []
                
                for i, row in df_raw.iterrows():
                    sev, pri, act, conf = "🟢 OK", "🟢 Maintain", "Keep.", "None"
                    for j, other in df_raw.iterrows():
                        if i != j and fuzz.token_sort_ratio(row['Title'], other['Title']) > 80:
                            conf = other['URL']
                            if row['Words'] < other['Words']:
                                sev, pri, act = "🔴 CRITICAL", "🔴 P1 - Today", f"Redirect to: {other['URL']}"
                            else:
                                sev, pri, act = "🟠 HIGH", "🟠 P2 - This Week", "Rewrite Title."
                            break
                    
                    final_audit.append({
                        "Page Type": row['Type'],
                        "Severity": sev,
                        "Primary Keyword": row['Keyword'],
                        "URL": row['URL'],
                        "Conflicting URL": conf,
                        "Page Title": row['Title'],
                        "Words": row['Words'],
                        "Action Plan": act,
                        "Priority": pri
                    })

                complete_df = pd.DataFrame(final_audit)

                # --- 5. Excel Styling Logic ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='SEO Audit')
                    ws = writer.sheets['SEO Audit']
                    
                    # Defining Fills
                    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                    orange_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                    
                    # Applying Column Formatting
                    for row_idx in range(2, ws.max_row + 1):
                        sev_cell = ws.cell(row=row_idx, column=2) # Severity Column
                        if "CRITICAL" in str(sev_cell.value):
                            sev_cell.fill = red_fill
                        elif "HIGH" in str(sev_cell.value):
                            sev_cell.fill = orange_fill
                
                st.success("Audit Complete!")
                st.dataframe(complete_df, use_container_width=True)
                st.download_button(
                    label="📥 Download Styled Excel Report",
                    data=output.getvalue(),
                    file_name="Zahidul_SEO_Audit.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
