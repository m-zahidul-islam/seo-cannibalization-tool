import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import time

# --- ১. শুধুমাত্র সাইটম্যাপের লিঙ্ক রিড করার ফাংশন ---
def get_only_relevant_urls(sitemap_url):
    urls = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(sitemap_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            
            # যদি এটি আরেকটি সাইটম্যাপ হয়, তবে ইমেজ বা অ্যাটাচমেন্ট সাইটম্যাপ হলে সেটি বাদ দেবে
            if link.endswith('.xml'):
                if any(x in link.lower() for x in ['image', 'attachment', 'media', 'video']):
                    continue
                urls.extend(get_only_relevant_urls(link))
            else:
                # মিডিয়া ফাইল এক্সটেনশন থাকলে বাদ
                if not any(link.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.webp']):
                    urls.append(link)
    except:
        pass
    return list(set(urls))

def scrape_seo_data(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        words = len(soup.get_text().split())
        return title, words
    except:
        return "Error", 0

# --- ২. ইউজার ইন্টারফেস ---
st.set_page_config(page_title="Zahidul's SEO Tool", layout="wide")
st.title("🛡️ Simple & Fast SEO Cannibalization Checker")

sitemap_input = st.text_input("Sitemap URL দিন:", placeholder="https://example.com/sitemap_index.xml")
if st.button("Analyze Now"):
    if sitemap_input:
        with st.spinner("লিঙ্কগুলো চেক করা হচ্ছে..."):
            all_links = get_only_relevant_urls(sitemap_input)
            
            if not all_links:
                st.error("কোনো ভ্যালিড লিঙ্ক পাওয়া যায়নি।")
            else:
                st.success(f"মোট {len(all_links)} টি পেজ পাওয়া গেছে।")
                
                results = []
                # পারফরম্যান্সের জন্য লিমিট (আপনার প্রয়োজন মত বাড়াতে পারেন)
                process_limit = all_links[:100] 
                
                bar = st.progress(0)
                for i, url in enumerate(process_limit):
                    t, w = scrape_seo_data(url)
                    results.append({"URL": url, "Title": t, "Words": w})
                    bar.progress((i + 1) / len(process_limit))

                df = pd.DataFrame(results)
                
                # ক্যানিবালাইজেশন চেক
                final_report = []
                for i, row in df.iterrows():
                    conflicts = [other['URL'] for j, other in df.iterrows() 
                                 if i != j and fuzz.token_sort_ratio(row['Title'], other['Title']) > 80]
                    
                    final_report.append({
                        "URL": row['URL'],
                        "Title": row['Title'],
                        "Word Count": row['Words'],
                        "Status": "🚨 Issue" if conflicts else "✅ Clear",
                        "Conflicting URLs": ", ".join(conflicts) if conflicts else "None"
                    })

                st.dataframe(pd.DataFrame(final_report), use_container_width=True)
                
                csv = pd.DataFrame(final_report).to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 ডাউনলোড রিপোর্ট (CSV)", csv, "seo_audit.csv", "text/csv")
