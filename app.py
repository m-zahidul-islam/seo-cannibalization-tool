import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io

# --- 1. Smart Sitemap Fetcher (Filters out Hidden/Media Sitemaps) ---
def get_filtered_sitemap_urls(sitemap_url):
    urls = []
    # Keywords to strictly ignore in sitemaps
    ignore_list = ['image', 'video', 'attachment', 'media', 'gallery', 'css', 'js']
    exclude_ext = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.webp', '.svg']

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(sitemap_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            
            # If it's a sub-sitemap, check if it's worth entering
            if link.endswith('.xml'):
                # ONLY enter if it's NOT in the ignore list
                if not any(word in link.lower() for word in ignore_list):
                    urls.extend(get_filtered_sitemap_urls(link))
                continue
            
            # If it's a direct page link, skip media files
            if not any(link.lower().endswith(ext) for ext in exclude_ext):
                urls.append(link)
    except:
        pass
    
    return list(set(urls))

# --- 2. Professional SEO Scraper ---
def scrape_seo_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        words = len(soup.get_text().split())
        
        # Determine Page Type
        link_low = url.lower()
        if "/product/" in link_low: p_type = "Product"
        elif "/category/" in link_low or "/shop/" in link_low: p_type = "Category"
        elif "/blog/" in link_low or "/post/" in link_low: p_type = "Blog"
        else: p_type = "Static/Core"
        
        return title, words, p_type
    except:
        return "Error", 0, "Unknown"

# --- 3. Streamlit UI Layout ---
st.set_page_config(page_title="Zahidul's Smart SEO Auditor", layout="wide")
st.title("🛡️ Professional SEO Audit Tool")
st.write("Enter your sitemap below. The tool will automatically skip media and hidden sitemaps.")

sitemap_input = st.text_input("Sitemap URL:", placeholder="https://sareemela.com/sitemap_index.xml")

if st.button("Generate Professional Audit"):
    if sitemap_input:
        with st.spinner("Scanning relevant pages..."):
            all_links = get_filtered_sitemap_urls(sitemap_input)
            
            if not all_links:
                st.warning("No valid page links found. Please check your sitemap URL.")
            else:
                st.info(f"Found {len(all_links)} relevant pages to audit.")
                
                results = []
                p_bar = st.progress(0)
                for i, url in enumerate(all_links[:500]): # 500 limit for performance
                    t, w, pt = scrape_seo_data(url)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt})
                    p_bar.progress((i + 1) / len(all_links[:500]))

                df_raw = pd.DataFrame(results)
                final_audit = []

                # Cannibalization & Action Plan Logic
                for i, row in df_raw.iterrows():
                    conflict_url, severity, priority, action = "None", "🟢 OK", "🟢 Maintain", "Keep. No action needed."
                    for j, other in df_raw.iterrows():
                        if i != j:
                            score = fuzz.token_sort_ratio(row['Title'], other['Title'])
                            if score > 80:
                                conflict_url = other['URL']
                                if row['Words'] < other['Words']:
                                    severity, priority, action = "🔴 CRITICAL", "🔴 P1", f"Redirect to: {other['URL']}"
                                else:
                                    severity, priority, action = "🟠 HIGH", "🟠 P2", "Rewrite Title for intent."
                                break

                    final_audit.append({
                        "Type": row['Type'], "Severity": severity, "URL": row['URL'],
                        "Conflict URL": conflict_url, "Title": row['Title'],
                        "Words": row['Words'], "Action Plan": action, "Priority": priority
                    })

                complete_df = pd.DataFrame(final_audit)
                action_df = complete_df[complete_df['Severity'] != "🟢 OK"]

                # Excel Export
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Full Audit')
                    action_df.to_excel(writer, index=False, sheet_name='Action Plan')
                
                st.subheader("📊 Audit Overview")
                st.dataframe(complete_df, use_container_width=True)
                
                st.download_button(
                    label="📥 Download Professional Excel Report",
                    data=output.getvalue(),
                    file_name="SEO_Audit_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.warning("Please enter a sitemap URL first.")

st.markdown("---")
st.caption("Developed by M Zahidul Islam | SEO Specialist")
