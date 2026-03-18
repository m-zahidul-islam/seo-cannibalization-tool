import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io

# --- ১. সাইটম্যাপ ক্রলার (সব সাব-সাইটম্যাপ ভিজিট করবে) ---
def get_sitemap_urls(url):
    urls = []
    # কোনোভাবেই এই ফাইলগুলো নেব না
    exclude_ext = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.webp', '.svg', '.xml', '.css', '.js']

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            
            # যদি এটি আরেকটি সাইটম্যাপ (.xml) হয়, তবে তার ভেতরে ঢোকো
            if link.endswith('.xml'):
                # ইমেজ বা অ্যাটাচমেন্ট সাইটম্যাপ হলে বাদ দাও
                if any(x in link.lower() for x in ['image', 'attachment', 'video', 'media']):
                    continue
                urls.extend(get_sitemap_urls(link))
            else:
                # মিডিয়া ফাইল চেক
                is_media = any(link.lower().endswith(ext) for ext in exclude_ext)
                if not is_media:
                    urls.append(link)
    except: pass
    return list(set(urls))

# --- ২. পেজ টাইপ ডিটেক্টর (আপনার ফাইলের মতো ক্যাটাগরি) ---
def detect_page_type(url, domain):
    link_low = url.lower().strip('/')
    base_domain = domain.lower().strip('/')
    
    if link_low == base_domain: return "Static (Home)"
    if any(x in link_low for x in ['about-us', 'contact-us', 'faq', 'terms', 'privacy']): return "Static"
    if "/product/" in link_low: return "Product"
    if "/product-category/" in link_low or "/shop/" in link_low: return "Category"
    if "/category/" in link_low: return "Blog Category"
    if len(link_low.replace(base_domain, '').split('/')) <= 2 and not any(x in link_low for x in ['/product', '/category']): return "Blog/Page"
    return "Page"

def scrape_seo_data(url, domain):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        words = len(soup.get_text().split())
        p_type = detect_page_type(url, domain)
        return title, words, p_type
    except: return "Error", 0, "Unknown"

# --- ৩. UI Layout ---
st.set_page_config(page_title="SareeMela SEO Auditor", layout="wide")
st.title("🛡️ Professional SEO Auditor (Full Sitemap Analysis)")
st.write(f"Analyzing: {sitemap_input if 'sitemap_input' in locals() else 'SareeMela System'}")

sitemap_input = st.text_input("Sitemap URL:", value="https://sareemela.com/sitemap_index.xml")

if st.button("Run Complete 138+ Page Audit"):
    if sitemap_input:
        domain_name = "sareemela.com"
        with st.spinner("১৩৮টি লিঙ্ক প্রসেস করা হচ্ছে... এতে ১-২ মিনিট সময় লাগতে পারে।"):
            all_links = get_sitemap_urls(sitemap_input)
            
            if not all_links:
                st.error("কোনো লিঙ্ক পাওয়া যায়নি।")
            else:
                # আপনার সাইটম্যাপের সব লিঙ্ক প্রসেস করবে (৫০০ পর্যন্ত সেফ লিমিট)
                process_limit = all_links[:500] 
                st.success(f"মোট {len(all_links)} টি ইউনিক পেজ লিঙ্ক পাওয়া গেছে।")
                
                results = []
                p_bar = st.progress(0)
                for i, url in enumerate(process_limit):
                    t, w, pt = scrape_seo_data(url, domain_name)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt})
                    p_bar.progress((i + 1) / len(process_limit))

                df_raw = pd.DataFrame(results)
                final_audit_data = []

                for i, row in df_raw.iterrows():
                    conflict_url, severity, priority, action, issue = "None", "🟢 OK", "🟢 Maintain", "Keep.", "None"
                    
                    for j, other in df_raw.iterrows():
                        if i != j:
                            score = fuzz.token_sort_ratio(row['Title'], other['Title'])
                            if score > 80:
                                conflict_url = other['URL']
                                issue = "Cannibalization"
                                if row['Words'] < other['Words']:
                                    severity, priority, action = "🔴 CRITICAL", "🔴 P1 — Today", f"301 Redirect to: {other['URL']}"
                                else:
                                    severity, priority, action = "🟠 HIGH", "🟠 P2 — This Week", "Rewrite title to differentiate."
                                break

                    final_audit_data.append({
                        "Page Type": row['Type'], "Severity": severity, "URL": row['URL'],
                        "Conflicting URL": conflict_url, "Page Title": row['Title'],
                        "Word Count": row['Words'], "Issue": issue, "Recommended Fix": action, "Priority": priority
                    })

                complete_df = pd.DataFrame(final_audit_data)
                action_df = complete_df[complete_df['Severity'] != "🟢 OK"].copy()

                # Excel Export
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Complete Audit')
                    action_df.to_excel(writer, index=False, sheet_name='Priority Action Plan')
                
                st.subheader("📊 Audit Overview")
                st.dataframe(complete_df, use_container_width=True)
                
                st.download_button(
                    label="📥 ডাউনলোড এক্সেল রিপোর্ট (Full 138+ Pages)",
                    data=output.getvalue(),
                    file_name="SareeMela_Full_SEO_Audit.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
