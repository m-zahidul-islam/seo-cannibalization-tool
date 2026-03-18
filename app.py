import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import time

def get_sitemap_urls(url):
    urls = []
    exclude_keywords = ['image', 'attachment', 'video', 'media', 'gallery']
    try:
        res = requests.get(url, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            if link.endswith('.xml'):
                if any(k in link.lower() for k in exclude_keywords): continue
                urls.extend(get_sitemap_urls(link))
            else:
                if not any(link.lower().endswith(ext) for ext in ['.jpg', '.png', '.pdf', '.webp']):
                    urls.append(link)
    except: pass
    return list(set(urls))

def scrape_seo_data(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        words = len(soup.get_text().split())
        # পেজ টাইপ ডিটেক্ট করা
        page_type = "Product" if "/product/" in url else "Category" if "/category/" in url else "Blog" if "/blog/" in url else "Static"
        return title, words, page_type
    except: return "Error", 0, "Unknown"

# --- UI ---
st.set_page_config(page_title="Zahidul's Pro SEO Auditor", layout="wide")
st.title("🛡️ Advanced SEO Cannibalization Auditor")

sitemap_input = st.text_input("Sitemap URL দিন:", placeholder="https://sareemela.com/sitemap_index.xml")

if st.button("Generate Professional Audit"):
    all_links = get_sitemap_urls(sitemap_input)
    if all_links:
        results = []
        process_limit = all_links[:100] # প্রথম ১০০টি পেজ
        bar = st.progress(0)
        
        for i, url in enumerate(process_limit):
            t, w, p_type = scrape_seo_data(url)
            results.append({"URL": url, "Title": t, "Words": w, "Type": p_type})
            bar.progress((i + 1) / len(process_limit))

        df = pd.DataFrame(results)
        final_report = []

        for i, row in df.iterrows():
            conflicts = []
            severity = "🟢 OK"
            priority = "🟢 Maintain"
            action = "Keep. No action needed."
            
            for j, other in df.iterrows():
                if i != j:
                    score = fuzz.token_sort_ratio(row['Title'], other['Title'])
                    if score > 80:
                        conflicts.append(other['URL'])
                        # লজিক: যদি টাইটেল মিলে যায় এবং কন্টেন্ট কম থাকে
                        if row['Words'] < 300:
                            severity = "🔴 CRITICAL"
                            priority = "🔴 Fix Today"
                            action = f"Thin content & overlap with {other['URL']}. Merge or 301 Redirect."
                        else:
                            severity = "🟡 MEDIUM"
                            priority = "🟡 This Month"
                            action = "Title overlap detected. Rewrite title to differentiate intent."

            final_report.append({
                "Page Type": row['Type'],
                "Severity": severity,
                "URL": row['URL'],
                "Page Title": row['Title'],
                "Issue / Problem": "Keyword Cannibalization" if conflicts else "None",
                "Recommended Fix": action,
                "Priority": priority
            })

        final_df = pd.DataFrame(final_report)
        st.dataframe(final_df, use_container_width=True)
        
        # CSV ডাউনলোড (গুগল শীটে আপলোড করার জন্য রেডি)
        csv = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ডাউনলোড প্রফেশনাল রিপোর্ট (CSV)", csv, "seo_audit_report.csv", "text/csv")
