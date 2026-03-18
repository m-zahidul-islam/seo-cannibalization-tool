import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import json
import time

# --- ১. স্মার্ট ইউআরএল ফিল্টারিং এবং ক্রলিং লজিক ---
def get_sitemap_urls(url):
    urls = []
    # বাদ দেওয়ার জন্য ফাইল এক্সটেনশন
    exclude_ext = ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.webp', '.svg', '.mp4', '.js', '.css']
    # মিডিয়া বা অ্যাটাচমেন্ট বুঝায় এমন কীওয়ার্ড (সাইটম্যাপ ফিল্টার করার জন্য)
    exclude_keywords = ['attachment', 'image', 'video', 'media', 'css', 'js', 'gallery']
    # ই-কমার্স এবং ব্লগের জন্য গুরুত্বপূর্ণ কি-ওয়ার্ড
    important_paths = ['/product', '/category', '/shop', '/blog', '/post', '/page', '/item', '/p/']

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            
            # মিডিয়া ফাইল হলে সরাসরি বাদ
            if any(link.lower().endswith(ext) for ext in exclude_ext):
                continue
            
            # যদি এটি আরেকটি সাইটম্যাপ (.xml) হয়
            if link.endswith('.xml'):
                # যদি সাইটম্যাপের লিঙ্কে 'image' বা 'attachment' থাকে তবে ভেতরে ঢুকবে না
                if any(k in link.lower() for k in exclude_keywords):
                    continue
                urls.extend(get_sitemap_urls(link))
            else:
                # ই-কমার্স এবং ব্লগের জন্য নির্দিষ্ট ফিল্টার
                # যদি লিঙ্কটিতে গুরুত্বপূর্ণ পাথ থাকে তবেই নেবে
                if any(path in link.lower() for path in important_paths):
                    urls.append(link)
                # যদি কোনো নির্দিষ্ট পাথ না থাকে (অন্যান্য সাধারণ সাইট), তবে মিডিয়া ছাড়া সব নেবে
                elif not any(path in link.lower() for path in important_paths):
                    # কিন্তু নিশ্চিত করবে এটি কোনো ইমেজ ফোল্ডার বা মিডিয়া লিঙ্ক নয়
                    if not any(k in link.lower() for k in exclude_keywords):
                        urls.append(link)
                        
    except: pass
    return list(set(urls))

def scrape_page_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        title = soup.title.string.strip() if soup.title else "No Title"
        h1 = soup.find('h1').text.strip() if soup.find('h1') else "No H1"
        words = len(soup.get_text().split())
        
        # স্কিমা চেক (ই-কমার্সের জন্য গুরুত্বপূর্ণ)
        schemas = [json.loads(s.string).get('@type', 'Unknown') 
                   for s in soup.find_all('script', type='application/ld+json') if s.string]
        
        return title, h1, words, str(list(set(schemas)))
    except:
        return "Error", "Error", 0, "None"

# --- ২. ইউজার ইন্টারফেস (Streamlit Dashboard) ---
st.set_page_config(page_title="Zahidul's SEO Intelligence", layout="wide")

# কাস্টম ডিজাইন
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #1a73e8; color: white; border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Pro Keyword Cannibalization & Intent Checker")
st.write("আপনার ওয়েবসাইট বা ই-কমার্স সাইটের লিঙ্ক এনালাইসিস করে ক্যানিবালাইজেশন রিপোর্ট তৈরি করুন।")

sitemap_input = st.text_input("Enter Sitemap URL:", placeholder="https://example.com/sitemap_index.xml")
analyze_btn = st.button("Analyze Now")

if analyze_btn and sitemap_input:
    with st.spinner("সাইটম্যাপ থেকে লিঙ্ক সংগ্রহ করা হচ্ছে..."):
        all_links = get_sitemap_urls(sitemap_input)
        
        if not all_links:
            st.error("কোনো ভ্যালিড পেজ লিঙ্ক পাওয়া যায়নি। দয়া করে সঠিক সাইটম্যাপ দিন।")
        else:
            st.success(f"মোট {len(all_links)} টি ভ্যালিড পেজ পাওয়া গেছে। গভীর এনালাইসিস শুরু হচ্ছে...")
            
            # পারফরম্যান্সের জন্য প্রথম ১০০টি লিঙ্ক প্রসেস করা হচ্ছে
            process_limit = all_links[:100]
            progress = st.progress(0)
            
            data_list = []
            for i, url in enumerate(process_limit):
                t, h, w, s = scrape_page_data(url)
                data_list.append({"URL": url, "Title": t, "H1": h, "Words": w, "Schema": s})
                progress.progress((i + 1) / len(process_limit))
            
            df = pd.DataFrame(data_list)
            
            # ক্যানিবালাইজেশন এবং ডিসিশন লজিক
            final_results = []
            for i, row in df.iterrows():
                conflicts = []
                recommendation = "✅ Good: Unique Intent"
                
                for j, other in df.iterrows():
                    if i != j:
                        # টাইটেলের মিল চেক (Fuzzy Matching)
                        score = fuzz.token_sort_ratio(row['Title'], other['Title'])
                        if score > 80:
                            conflicts.append(other['URL'])
                            # ডিসিশন লজিক (ওয়ার্ড কাউন্ট অনুযায়ী)
                            if row['Words'] < other['Words']:
                                recommendation = "🚨 High Risk: Consider Redirecting to larger page"
                            else:
                                recommendation = "⚠️ Warning: Potential Cannibalization (Main Page)"
                
                final_results.append({
                    "Target URL": row['URL'],
                    "SEO Title": row['Title'],
                    "Content Depth (Words)": row['Words'],
                    "Schema": row['Schema'],
                    "Status": recommendation,
                    "Conflict With": ", ".join(conflicts) if conflicts else "None"
                })

            final_df = pd.DataFrame(final_results)
            
            st.divider()
            st.subheader("📋 এনালাইসিস রিপোর্ট (মিডিয়া ফাইল বাদে)")
            st.dataframe(final_df, use_container_width=True)
            
            # এক্সেল ফ্রেন্ডলি ডাউনলোড বাটন
            csv_output = final_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 ডাউনলোড প্রফেশনাল রিপোর্ট (CSV)", csv_output, "seo_audit_report.csv", "text/csv")

st.markdown("---")
st.caption("Developed by M Zahidul Islam | SEO & Search Visibility Specialist")
