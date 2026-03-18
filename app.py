import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import json
import time

# --- ১. আসল ক্রলিং লজিক ---
def get_sitemap_urls(url):
    urls = []
    try:
        res = requests.get(url, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            u = loc.text.strip()
            if u.endswith('.xml'):
                urls.extend(get_sitemap_urls(u))
            else:
                urls.append(u)
    except: pass
    return list(set(urls))

def scrape_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        h1 = soup.find('h1').text.strip() if soup.find('h1') else "No H1"
        words = len(soup.get_text().split())
        return title, h1, words
    except: return "Error", "Error", 0

# --- ২. ইউজার ইন্টারফেস ---
st.set_page_config(page_title="Zahidul's SEO Tool", layout="wide")
st.title("🛡️ Ultimate Keyword Cannibalization Checker")

sitemap_input = st.text_input("Enter Sitemap URL (e.g. https://example.com/sitemap_index.xml)")
run_btn = st.button("Analyze Now")

if run_btn and sitemap_input:
    with st.spinner("ডাটা সংগ্রহ করা হচ্ছে... দয়া করে অপেক্ষা করুন।"):
        all_urls = get_sitemap_urls(sitemap_input)
        
        if not all_urls:
            st.error("দুঃখিত, সাইটম্যাপে কোনো লিঙ্ক পাওয়া যায়নি। লিঙ্কটি চেক করুন।")
        else:
            st.info(f"মোট {len(all_urls)} টি ইউআরএল পাওয়া গেছে। এনালাইসিস চলছে...")
            
            results = []
            # সার্ভার লিমিট অনুযায়ী আমরা প্রথম ১০০টি চেক করছি (আপনি চাইলে বাড়াতে পারেন)
            to_process = all_urls[:100] 
            
            p_bar = st.progress(0)
            for i, url in enumerate(to_process):
                t, h, w = scrape_data(url)
                results.append({"URL": url, "Title": t, "H1": h, "Words": w})
                p_bar.progress((i + 1) / len(to_process))
            
            df = pd.DataFrame(results)
            
            # ৩. ক্যানিবালাইজেশন এনালাইসিস
            final_data = []
            for i, row in df.iterrows():
                conflicts = []
                severity = "Safe"
                action = "None"
                
                for j, other in df.iterrows():
                    if i != j:
                        score = fuzz.token_sort_ratio(row['Title'], other['Title'])
                        if score > 80:
                            conflicts.append(other['URL'])
                            severity = "High"
                            action = "Merge or Redirect"
                
                final_data.append({
                    "URL": row['URL'],
                    "Title": row['Title'],
                    "Keyword Issue": "Duplicate Intent" if conflicts else "Healthy",
                    "Severity": severity,
                    "Action": action,
                    "Conflicts": ", ".join(conflicts) if conflicts else "None"
                })

            final_df = pd.DataFrame(final_data)
            st.success("এনালাইসিস সম্পন্ন হয়েছে!")
            st.dataframe(final_df, use_container_width=True)
            
            csv = final_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 ডাউনলোড ফুল রিপোর্ট (CSV)", csv, "seo_audit_report.csv", "text/csv")
