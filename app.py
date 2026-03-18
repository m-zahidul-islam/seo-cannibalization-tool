import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io
import re

# --- 1. Universal Sitemap Fetcher ---
def get_all_links(url):
    urls = []
    # জঞ্জাল বা মিডিয়া ফাইল এড়িয়ে চলার জন্য ফিল্টার
    ignore_list = ['image', 'video', 'attachment', 'media', 'css', 'js']
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            # যদি এটি আরেকটি সাইটম্যাপ ফাইল হয়
            if link.endswith('.xml'):
                if not any(x in link.lower() for x in ignore_list):
                    urls.extend(get_all_links(link))
                continue
            # পেজ লিঙ্ক হলে মিডিয়া ফাইল বাদ দিয়ে যুক্ত করা
            if not any(link.lower().endswith(ext) for ext in ['.jpg', '.png', '.webp', '.pdf', '.svg']):
                urls.append(link)
    except: pass
    return list(set(urls))

# --- 2. Dynamic Keyword & Data Scraper ---
def scrape_site_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # টাইটেল সংগ্রহ
        title = soup.title.string.strip() if soup.title else "No Title Found"
        
        # ওয়ার্ড কাউন্ট
        words = len(soup.get_text().split())
        
        # প্রাইমারি কিওয়ার্ড এক্সট্রাকশন (টাইটেলের প্রথম ৩টি গুরুত্বপূর্ণ শব্দ)
        clean_title = re.sub(r'[|,\-–—]', ' ', title).strip()
        kw = " ".join(clean_title.split()[:3]) if clean_title else "N/A"
        
        # পেজ টাইপ ক্যাটাগরি (Universal Logic)
        l = url.lower()
        if any(x in l for x in ['/product', '/item']): p_type = "Product"
        elif any(x in l for x in ['/category', '/collections']): p_type = "Category"
        elif any(x in l for x in ['/blog', '/post', '/article']): p_type = "Blog"
        else: p_type = "General Page"
        
        return title, words, p_type, kw
    except: return "Error", 0, "Unknown", "N/A"

# --- UI Layout ---
st.set_page_config(page_title="Universal SEO Auditor", layout="wide")
st.title("🛡️ Universal SEO Cannibalization Auditor")
st.write("যেকোনো ওয়েবসাইটের সাইটম্যাপ ইউআরএল দিয়ে ফুল অডিট রিপোর্ট জেনারেট করুন।")

target_sitemap = st.text_input("Enter Sitemap URL:", placeholder="https://example.com/sitemap.xml")

if st.button("Run Professional Audit"):
    if target_sitemap:
        with st.spinner("Scanning pages and analyzing content..."):
            all_urls = get_all_links(target_sitemap)
            if all_urls:
                st.info(f"Total Pages Found: {len(all_urls)}")
                
                results = []
                p_bar = st.progress(0)
                # Performance Safety: প্রথম ৫০০ লিঙ্ক প্রসেস করবে
                process_links = all_urls[:500] 
                
                for i, url in enumerate(process_links):
                    t, w, pt, kw = scrape_site_data(url)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt, "Keyword": kw})
                    p_bar.progress((i + 1) / len(process_links))
                
                df_raw = pd.DataFrame(results)
                final_output = []
                
                for i, row in df_raw.iterrows():
                    # Default Symbols
                    status, pri, act, conf = "🟢 OK", "🟢 Maintain", "Keep Content.", "None"
                    
                    for j, other in df_raw.iterrows():
                        if i != j and fuzz.token_sort_ratio(row['Title'], other['Title']) > 80:
                            conf = other['URL']
                            if row['Words'] < other['Words']:
                                status, pri, act = "🔴 CRITICAL", "🔴 P1 - Immediate", f"301 Redirect to: {other['URL']}"
                            else:
                                status, pri, act = "🟡 HIGH", "🟡 P2 - Weekly", "Rewrite title/meta to differentiate."
                            break
                    
                    final_output.append({
                        "Page Type": row['Type'], 
                        "Severity": status, 
                        "Primary Keyword": row['Keyword'],
                        "URL": row['URL'], 
                        "Conflicting URL": conf, 
                        "Page Title": row['Title'],
                        "Word Count": row['Words'], 
                        "Action Plan": act, 
                        "Priority": pri
                    })

                complete_df = pd.DataFrame(final_output)
                action_plan_df = complete_df[complete_df['Severity'] != "🟢 OK"].copy()
                
                # --- Excel Export with Two Sheets ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Full Audit')
                    action_plan_df.to_excel(writer, index=False, sheet_name='Priority Fixes')
                
                st.success("Audit Complete! Report is ready for download.")
                st.dataframe(complete_df, use_container_width=True)
                st.download_button("📥 Download Final Excel Report", output.getvalue(), "Universal_SEO_Audit.xlsx")
            else:
                st.error("No links found. Please check the Sitemap URL.")
    else:
        st.warning("Please enter a valid Sitemap URL first.")

st.markdown("---")
st.caption("Developed by M Zahidul Islam | SEO Specialist")
