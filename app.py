import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io
import time

# --- ১. সাইটম্যাপ ক্রলার ---
def get_sitemap_urls(url):
    urls = []
    exclude_keywords = ['image', 'attachment', 'video', 'media', 'gallery', 'css', 'js']
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            if link.endswith('.xml'):
                if any(k in link.lower() for k in exclude_keywords): continue
                urls.extend(get_sitemap_urls(link))
            else:
                if not any(link.lower().endswith(ext) for ext in ['.jpg', '.png', '.webp', '.pdf']):
                    urls.append(link)
    except: pass
    return list(set(urls))

# --- ২. ডাটা স্ক্র্যাপার ---
def scrape_seo_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        words = len(soup.get_text().split())
        
        # পেজ টাইপ নির্ধারণ
        if "/product/" in url: p_type = "Product"
        elif "/category/" in url or "/shop/" in url: p_type = "Category"
        elif "/blog/" in url or "/post/" in url: p_type = "Blog"
        else: p_type = "Static"
        
        return title, words, p_type
    except:
        return "Error", 0, "Unknown"

# --- ৩. ইউজার ইন্টারফেস ---
st.set_page_config(page_title="Zahidul's Pro SEO Auditor", layout="wide")
st.title("🛡️ Advanced SEO Auditor (500 Limit & Excel)")

sitemap_input = st.text_input("Sitemap URL দিন:", placeholder="https://example.com/sitemap_index.xml")

if st.button("Generate Professional Audit"):
    if sitemap_input:
        with st.spinner("লিঙ্ক এনালাইসিস চলছে... দয়া করে অপেক্ষা করুন।"):
            all_links = get_sitemap_urls(sitemap_input)
            
            if not all_links:
                st.error("কোনো ভ্যালিড লিঙ্ক পাওয়া যায়নি।")
            else:
                # আপনার অনুরোধ অনুযায়ী ৫০০টি লিঙ্কের লিমিট সেট করা হলো
                process_limit = all_links[:500] 
                st.info(f"মোট {len(all_links)} টি লিঙ্ক পাওয়া গেছে। প্রথম ৫০০টি প্রসেস করা হচ্ছে...")
                
                results = []
                progress_bar = st.progress(0)
                
                for i, url in enumerate(process_limit):
                    t, w, pt = scrape_seo_data(url)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt})
                    progress_bar.progress((i + 1) / len(process_limit))

                df_raw = pd.DataFrame(results)
                final_audit_data = []

                # ৪. ক্যানিবালাইজেশন এবং অ্যাকশন প্ল্যান লজিক
                for i, row in df_raw.iterrows():
                    conflict_url = "None"
                    severity = "🟢 OK"
                    priority = "🟢 Maintain"
                    action = "Keep. No action needed."
                    issue = "None"
                    
                    for j, other in df_raw.iterrows():
                        if i != j:
                            score = fuzz.token_sort_ratio(row['Title'], other['Title'])
                            if score > 80:
                                conflict_url = other['URL']
                                issue = "Keyword Cannibalization"
                                if row['Words'] < other['Words']:
                                    severity = "🔴 CRITICAL"
                                    priority = "🔴 P1 — Today"
                                    action = f"301 Redirect this page to: {other['URL']}"
                                elif score > 95:
                                    severity = "🟠 HIGH"
                                    priority = "🟠 P2 — This Week"
                                    action = "Identical title. Rewrite to differentiate intent."
                                else:
                                    severity = "🟡 MEDIUM"
                                    priority = "🟡 P3 — This Month"
                                    action = "Title overlap. Adjust primary keywords."
                                break

                    final_audit_data.append({
                        "Page Type": row['Type'],
                        "Severity": severity,
                        "URL": row['URL'],
                        "Conflicting URL": conflict_url,
                        "Page Title": row['Title'],
                        "Word Count": row['Words'],
                        "Issue / Problem": issue,
                        "Recommended Fix": action,
                        "Priority": priority
                    })

                # ৫. ডেটাফ্রেম তৈরি
                complete_audit_df = pd.DataFrame(final_audit_data)
                action_plan_df = complete_audit_df[complete_audit_df['Severity'] != "🟢 OK"].copy()
                action_plan_df = action_plan_df[['Priority', 'Recommended Fix', 'URL', 'Conflicting URL', 'Issue / Problem']]

                # ৬. এক্সেল ফাইল জেনারেশন (Memory Buffer)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_audit_df.to_excel(writer, index=False, sheet_name='Complete Audit')
                    action_plan_df.to_excel(writer, index=False, sheet_name='Priority Action Plan')
                
                processed_data = output.getvalue()

                # ৭. রেজাল্ট এবং ডাউনলোড বাটন
                st.success("অডিট সম্পন্ন হয়েছে!")
                st.subheader("🔥 Priority Action Plan")
                st.dataframe(action_plan_df, use_container_width=True)

                st.download_button(
                    label="📥 ডাউনলোড প্রফেশনাল এক্সেল (.xlsx)",
                    data=processed_data,
                    file_name="SEO_Audit_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.warning("সাইটম্যাপ ইউআরএল দিন।")
