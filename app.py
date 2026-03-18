import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io
import re

# --- ১. স্মার্ট সাইটম্যাপ ফেচার ---
def get_all_links(url):
    urls = []
    ignore_list = ['image', 'video', 'attachment', 'media', 'css', 'js']
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            if link.endswith('.xml'):
                if not any(x in link.lower() for x in ignore_list):
                    urls.extend(get_all_links(link))
                continue
            if not any(link.lower().endswith(ext) for ext in ['.jpg', '.png', '.webp', '.pdf', '.svg']):
                urls.append(link)
    except: pass
    return list(set(urls))

# --- ২. ডাটা স্ক্র্যাপার এবং কিওয়ার্ড এক্সট্রাক্টর ---
def scrape_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title Found"
        words = len(soup.get_text().split())
        
        # কিওয়ার্ড: টাইটেলের প্রথম ৩টি শব্দ
        clean_title = re.sub(r'[|,\-–—]', ' ', title).strip()
        kw = " ".join(clean_title.split()[:3]) if clean_title else "N/A"
        
        # পেজ টাইপ নির্ধারণ
        l = url.lower()
        if any(x in l for x in ['/product', '/item']): pt = "Product"
        elif any(x in l for x in ['/category', '/shop', '/collections']): pt = "Category"
        elif any(x in l for x in ['/blog', '/post', '/article']): pt = "Blog"
        else: pt = "General Page"
        
        return title, words, pt, kw
    except: return "Error", 0, "Unknown", "N/A"

# --- ৩. ইউজার ইন্টারফেস (UI) ---
st.set_page_config(page_title="Zahidul's Pro SEO Auditor", layout="wide")
st.title("🛡️ SEO Cannibalization & Keyword Auditor")
st.markdown("Developed by **M Zahidul Islam** | SEO & Search Visibility Specialist")

target_sitemap = st.text_input("Enter Sitemap URL:", placeholder="https://sareemela.com/sitemap_index.xml")

if st.button("Generate Professional Report"):
    if target_sitemap:
        with st.spinner("Analyzing pages... This may take a moment."):
            all_links = get_all_links(target_sitemap)
            if all_links:
                st.success(f"Total Pages Identified: {len(all_links)}")
                results = []
                p_bar = st.progress(0)
                process_limit = all_links[:500] 
                
                for i, url in enumerate(process_limit):
                    t, w, pt, kw = scrape_data(url)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt, "Keyword": kw})
                    p_bar.progress((i + 1) / len(process_limit))
                
                df_raw = pd.DataFrame(results)
                final_output = []
                
                for i, row in df_raw.iterrows():
                    # স্ট্যাটাস ইমোজি লজিক (ভিতরের বৃত্ত কালার)
                    status, pri, act, conf = "🟢 OK", "🟢 Maintain", "Keep.", "None"
                    
                    for j, other in df_raw.iterrows():
                        if i != j and fuzz.token_sort_ratio(row['Title'], other['Title']) > 80:
                            conf = other['URL']
                            if row['Words'] < other['Words']:
                                status, pri, act = "🔴 CRITICAL", "🔴 P1 - Immediate", f"301 Redirect to: {other['URL']}"
                            else:
                                status, pri, act = "🟡 HIGH", "🟡 P2 - Weekly", "Rewrite Title/Meta."
                            break
                    
                    final_output.append({
                        "Page Type": row['Type'], "Severity": status, "Primary Keyword": row['Keyword'],
                        "URL": row['URL'], "Conflicting URL": conf, "Page Title": row['Title'],
                        "Words": row['Words'], "Action Plan": act, "Priority": pri
                    })

                complete_df = pd.DataFrame(final_output)
                action_df = complete_df[complete_df['Severity'] != "🟢 OK"].copy()
                
                # --- এক্সেল ফাইল জেনারেশন ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Full Audit')
                    action_df.to_excel(writer, index=False, sheet_name='Action Plan')
                
                st.dataframe(complete_df, use_container_width=True)
                st.download_button("📥 Download Styled Excel Report", output.getvalue(), "SEO_Audit_Report.xlsx")
            else:
                st.error("Invalid Sitemap or No Links Found.")
