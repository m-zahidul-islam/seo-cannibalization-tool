import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io
import re

# --- 1. Smart Sitemap Fetcher ---
def get_all_urls(url):
    urls = []
    ignore = ['image', 'video', 'attachment', 'media']
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
            if not any(link.lower().endswith(ext) for ext in ['.jpg', '.png', '.webp', '.pdf']):
                urls.append(link)
    except: pass
    return list(set(urls))

# --- 2. Professional Scraper & Categorizer ---
def scrape_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        words = len(soup.get_text().split())
        
        l = url.lower()
        if "/product/" in l: p_type = "Product"
        elif "/category/" in l or "/product-category/" in l: p_type = "Category"
        elif "/blog/" in l: p_type = "Blog"
        else: p_type = "Static Page"
        
        # Keyword Extraction from Title
        clean = re.sub(r'[|,\-–—]|Saree Mela|SareeMela|Home|Shop', '', title, flags=re.IGNORECASE).strip()
        kw = " ".join(clean.split()[:3]) if clean else "N/A"
        
        return title, words, p_type, kw
    except: return "Error", 0, "Unknown", "N/A"

# --- UI Setup ---
st.set_page_config(page_title="Zahidul's Professional SEO Auditor", layout="wide")
st.title("🛡️ SEO Auditor (Three-Color Status Icons)")

sitemap_input = st.text_input("Enter Sitemap URL:", value="https://sareemela.com/sitemap_index.xml")

if st.button("Run SEO Audit"):
    if sitemap_input:
        with st.spinner("Analyzing pages and applying status icons..."):
            links = get_all_urls(sitemap_input)
            if links:
                results = []
                p_bar = st.progress(0)
                process_limit = links[:500] 
                
                for i, url in enumerate(process_limit):
                    t, w, pt, kw = scrape_data(url)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt, "Keyword": kw})
                    p_bar.progress((i + 1) / len(process_limit))
                
                df_raw = pd.DataFrame(results)
                final_list = []
                for i, row in df_raw.iterrows():
                    # ডিফল্ট সবুজ বৃত্ত (OK)
                    sev, pri, act, conf = "🟢 OK", "🟢 Maintain", "Keep.", "None"
                    
                    for j, other in df_raw.iterrows():
                        if i != j and fuzz.token_sort_ratio(row['Title'], other['Title']) > 80:
                            conf = other['URL']
                            if row['Words'] < other['Words']:
                                # লাল বৃত্ত (CRITICAL)
                                sev, pri, act = "🔴 CRITICAL", "🔴 P1 - Today", f"Redirect to: {other['URL']}"
                            else:
                                # হলুদ/কমলা বৃত্ত (HIGH)
                                sev, pri, act = "🟡 HIGH", "🟡 P2 - This Week", "Rewrite Title to differentiate."
                            break
                    
                    final_list.append({
                        "Page Type": row['Type'], 
                        "Severity": sev, # এখানে বৃত্তের কালার চেঞ্জ হবে
                        "Primary Keyword": row['Keyword'],
                        "URL": row['URL'], 
                        "Conflicting URL": conf, 
                        "Page Title": row['Title'],
                        "Words": row['Words'], 
                        "Action Plan": act, 
                        "Priority": pri
                    })

                complete_df = pd.DataFrame(final_list)
                action_plan_df = complete_df[complete_df['Severity'] != "🟢 OK"].copy()
                
                # --- Excel Generation ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Full Audit')
                    action_plan_df.to_excel(writer, index=False, sheet_name='Action Plan')
                    
                    # কলাম উইডথ ফিক্স করা (ঐচ্ছিক কিন্তু সুন্দর দেখায়)
                    for sheet in ['Full Audit', 'Action Plan']:
                        ws = writer.sheets[sheet]
                        for col in ws.columns:
                            ws.column_dimensions[col[0].column_letter].width = 25

                st.success("Analysis Complete! Action Plan separated.")
                st.dataframe(complete_df, use_container_width=True)
                st.download_button("📥 Download Styled Excel (Red/Yellow/Green Icons)", output.getvalue(), "SEO_Report_Zahidul.xlsx")
