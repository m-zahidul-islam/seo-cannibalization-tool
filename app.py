import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io

# --- ১. সব ধরনের সাইটের জন্য স্মার্ট ফিল্টার ---
def get_sitemap_urls(url):
    urls = []
    # এজেন্সি, ই-কমার্স এবং ব্লগের সাধারণ পাথগুলো
    valid_paths = [
        '/product/', '/category/', '/shop/', '/blog/', '/post/', '/page/', 
        '/services/', '/case-study/', '/portfolio/', '/location/', '/pricing/',
        'about', 'contact', 'faq', 'team'
    ]
    exclude_ext = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.webp', '.svg', '.xml', '.css', '.js']

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            
            if link.endswith('.xml'):
                # মিডিয়া বা অ্যাটাচমেন্ট সাইটম্যাপ হলে বাদ
                if any(x in link.lower() for x in ['image', 'attachment', 'video', 'media']):
                    continue
                urls.extend(get_sitemap_urls(link))
            else:
                is_media = any(link.lower().endswith(ext) for ext in exclude_ext)
                # হোমপেজ চেক
                base_domain = url.split('/sitemap')[0].strip('/')
                is_home = link.strip('/') == base_domain
                
                # যদি মিডিয়া না হয় এবং (হোমপেজ অথবা ভ্যালিড পাথ অথবা সাধারণ ছোট ইউআরএল) হয় তবে নাও
                if not is_media:
                    if is_home or any(path in link.lower() for path in valid_paths) or len(link.split('/')) < 5:
                        urls.append(link)
    except: pass
    return list(set(urls))

# --- ২. পেজ টাইপ ডিটেক্টর (Universal Logic) ---
def detect_page_type(url, domain):
    link_low = url.lower().strip('/')
    if link_low == domain.lower().strip('/'): return "Static (Home)"
    if any(x in link_low for x in ['about', 'contact', 'faq', 'terms', 'privacy']): return "Static"
    if "/product/" in link_low or "/item/" in link_low: return "Product"
    if any(x in link_low for x in ['/category/', '/shop/', '/collection/']): return "Category"
    if any(x in link_low for x in ['/blog/', '/post/', '/news/']): return "Blog"
    if any(x in link_low for x in ['/services/', '/our-work/', '/portfolio/']): return "Service/Case Study"
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
st.set_page_config(page_title="Zahidul's Universal Auditor", layout="wide")
st.title("🛡️ Universal SEO Auditor & Action Plan Generator")
st.write("ই-কমার্স, এজেন্সি বা ব্লগ—যেকোনো সাইটম্যাপ দিন। এটি অটোমেটিক টাইপ ডিটেক্ট করবে।")

sitemap_input = st.text_input("Sitemap URL:", placeholder="https://example.com/sitemap_index.xml")

if st.button("Generate Professional Audit"):
    if sitemap_input:
        domain_name = sitemap_input.split('/sitemap')[0].strip('/')
        with st.spinner("পুরো ওয়েবসাইট এনালাইসিস করা হচ্ছে..."):
            all_links = get_sitemap_urls(sitemap_input)
            
            if not all_links:
                st.error("কোনো ভ্যালিড পেজ পাওয়া যায়নি।")
            else:
                # ৫০০ লিঙ্কের লিমিট (পারফরম্যান্সের জন্য)
                process_limit = all_links[:500] 
                st.info(f"মোট {len(all_links)} টি লিঙ্ক পাওয়া গেছে। {len(process_limit)} টি প্রসেস হচ্ছে।")
                
                results = []
                progress_bar = st.progress(0)
                for i, url in enumerate(process_limit):
                    t, w, pt = scrape_seo_data(url, domain_name)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt})
                    progress_bar.progress((i + 1) / len(process_limit))

                df_raw = pd.DataFrame(results)
                final_audit_data = []

                # ক্যানিবালাইজেশন এবং প্রায়োরিটি লজিক (আপনার ফাইলের স্টাইলে)
                for i, row in df_raw.iterrows():
                    conflict_url, severity, priority, action, issue = "None", "🟢 OK", "🟢 Maintain", "Keep.", "None"
                    
                    for j, other in df_raw.iterrows():
                        if i != j:
                            score = fuzz.token_sort_ratio(row['Title'], other['Title'])
                            if score > 80:
                                conflict_url = other['URL']
                                issue = "Keyword Cannibalization"
                                if row['Words'] < other['Words']:
                                    severity, priority, action = "🔴 CRITICAL", "🔴 P1 — Today", f"Redirect/Merge to: {other['URL']}"
                                elif score > 95:
                                    severity, priority, action = "🟠 HIGH", "🟠 P2 — This Week", "Duplicate Title. Rewrite to differentiate intent."
                                else:
                                    severity, priority, action = "🟡 MEDIUM", "🟡 P3 — This Month", "Title overlap detected."
                                break

                    final_audit_data.append({
                        "Page Type": row['Type'], "Severity": severity, "URL": row['URL'],
                        "Conflicting URL": conflict_url, "Page Title": row['Title'],
                        "Words": row['Words'], "Issue": issue, "Recommended Fix": action, "Priority": priority
                    })

                complete_df = pd.DataFrame(final_audit_data)
                # সাজানো (Static -> Service -> Category -> Product -> Blog)
                order_map = {'Static (Home)':1, 'Static':2, 'Service/Case Study':3, 'Category':4, 'Product':5, 'Blog':6, 'Page':7}
                complete_df['order'] = complete_df['Page Type'].map(order_map)
                complete_df = complete_df.sort_values('order').drop('order', axis=1)

                action_df = complete_df[complete_df['Severity'] != "🟢 OK"].copy()

                # Excel Export (Multiple Sheets)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Complete Audit')
                    action_df.to_excel(writer, index=False, sheet_name='Priority Action Plan')
                
                st.success("অডিট সম্পন্ন হয়েছে!")
                st.download_button("📥 ডাউনলোড প্রফেশনাল এক্সেল অডিট", output.getvalue(), "Universal_SEO_Audit.xlsx")
    else:
        st.warning("সাইটম্যাপ ইউআরএল দিন।")
