import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io
# এক্সেল ফরম্যাটিংয়ের জন্য নতুন ইমপোর্ট
from openpyxl.styles import PatternFill, Font

# --- ১. সাইটম্যাপ ফেচার ---
def get_filtered_sitemap_urls(sitemap_url):
    urls = []
    ignore_list = ['image', 'video', 'attachment', 'media', 'gallery']
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(sitemap_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        for loc in soup.find_all('loc'):
            link = loc.text.strip()
            if link.endswith('.xml'):
                if not any(word in link.lower() for word in ignore_list):
                    urls.extend(get_filtered_sitemap_urls(link))
                continue
            if not any(link.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
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
        
        link_low = url.lower()
        if "/product/" in link_low: p_type = "Product"
        elif "/category/" in link_low or "/shop/" in link_low: p_type = "Category"
        elif "/blog/" in link_low: p_type = "Blog"
        else: p_type = "Static/Core"
        
        return title, words, p_type
    except: return "Error", 0, "Unknown"

# --- ৩. এক্সেল স্টাইলিং ফাংশন ---
def apply_excel_style(writer, df, sheet_name):
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    # কালার কোড নির্ধারণ (আপনার ফাইলের মতো)
    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid") # Critical
    orange_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid") # High
    green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid") # OK
    
    for row in range(2, len(df) + 2):
        severity_cell = worksheet.cell(row=row, column=2) # Severity is 2nd column
        priority_cell = worksheet.cell(row=row, column=8) # Priority is 8th column
        
        val = str(severity_cell.value)
        if "CRITICAL" in val:
            severity_cell.fill = red_fill
        elif "HIGH" in val:
            severity_cell.fill = orange_fill
        elif "OK" in val:
            severity_cell.fill = green_fill

# --- UI Layout ---
st.set_page_config(page_title="Zahidul's Pro Auditor", layout="wide")
st.title("🛡️ Professional SEO Auditor with Excel Styling")

sitemap_input = st.text_input("Sitemap URL:", placeholder="https://sareemela.com/sitemap_index.xml")

if st.button("Generate Color-Coded Report"):
    if sitemap_input:
        with st.spinner("Analyzing and formatting report..."):
            all_links = get_filtered_sitemap_urls(sitemap_input)
            if all_links:
                results = []
                for url in all_links[:150]: # Safety limit
                    t, w, pt = scrape_seo_data(url)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt})
                
                df_raw = pd.DataFrame(results)
                final_data = []
                for i, row in df_raw.iterrows():
                    sev, pri, act = "🟢 OK", "🟢 Maintain", "Keep."
                    conf = "None"
                    for j, other in df_raw.iterrows():
                        if i != j and fuzz.token_sort_ratio(row['Title'], other['Title']) > 80:
                            conf = other['URL']
                            if row['Words'] < other['Words']:
                                sev, pri, act = "🔴 CRITICAL", "🔴 P1 - Today", f"Redirect to: {other['URL']}"
                            else:
                                sev, pri, act = "🟠 HIGH", "🟠 P2 - This Week", "Rewrite Title."
                            break
                    
                    final_data.append({
                        "Type": row['Type'], "Severity": sev, "URL": row['URL'],
                        "Conflict": conf, "Title": row['Title'], "Words": row['Words'],
                        "Action": act, "Priority": pri
                    })

                complete_df = pd.DataFrame(final_data)
                
                # এক্সেল ফাইল তৈরি এবং স্টাইল অ্যাপ্লাই
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Audit Report')
                    apply_excel_style(writer, complete_df, 'Audit Report')
                
                st.success("Analysis Complete with Formatting!")
                st.download_button("📥 Download Styled Excel", output.getvalue(), "SEO_Report_Styled.xlsx")
