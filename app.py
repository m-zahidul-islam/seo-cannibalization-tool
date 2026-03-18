import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
import io
# Excel styling libraries
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment

# --- 1. Smart & Strict Sitemap Fetcher ---
def get_filtered_urls(sitemap_url):
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
                    urls.extend(get_filtered_urls(link))
                continue
            if not any(link.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.svg']):
                urls.append(link)
    except: pass
    return list(set(urls))

# --- 2. Data Scraper ---
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

# --- 3. UI Layout ---
st.set_page_config(page_title="Zahidul's Pro SEO Auditor", layout="wide")
st.title("🛡️ Professional SEO Auditor (Styled Excel Output)")

sitemap_input = st.text_input("Sitemap URL:", placeholder="https://sareemela.com/sitemap_index.xml")

if st.button("Generate Styled Report"):
    if sitemap_input:
        with st.spinner("Analyzing pages and applying styles..."):
            all_links = get_filtered_urls(sitemap_input)
            if all_links:
                # Process links (Limit to 500 for stability)
                results = []
                p_bar = st.progress(0)
                for i, url in enumerate(all_links[:500]):
                    t, w, pt = scrape_seo_data(url)
                    results.append({"URL": url, "Title": t, "Words": w, "Type": pt})
                    p_bar.progress((i + 1) / len(all_links[:500]))
                
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
                        "Page Type": row['Type'], "Severity": sev, "URL": row['URL'],
                        "Conflicting URL": conf, "Page Title": row['Title'], "Words": row['Words'],
                        "Recommended Action": act, "Priority": pri
                    })

                complete_df = pd.DataFrame(final_data)
                action_df = complete_df[complete_df['Severity'] != "🟢 OK"]

                # --- 4. Excel Styling Logic (The Fix for Colors) ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    complete_df.to_excel(writer, index=False, sheet_name='Full Audit')
                    action_df.to_excel(writer, index=False, sheet_name='Action Plan')
                    
                    # Applying Colors to both sheets
                    for sheet_name in ['Full Audit', 'Action Plan']:
                        ws = writer.sheets[sheet_name]
                        # Set column widths for better look
                        for col in ws.columns:
                            max_length = 0
                            column = col[0].column_letter
                            for cell in col:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except: pass
                            ws.column_dimensions[column].width = min(max_length + 2, 50)

                        # Apply conditional formatting for Severity & Priority
                        red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                        orange_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                        
                        for row in range(2, ws.max_row + 1):
                            sev_cell = ws.cell(row=row, column=2) # Severity Column
                            if "CRITICAL" in str(sev_cell.value):
                                sev_cell.fill = red_fill
                            elif "HIGH" in str(sev_cell.value):
                                sev_cell.fill = orange_fill
                
                st.success("Audit complete! Colors applied to Excel file.")
                st.download_button(
                    label="📥 Download Styled Excel Report",
                    data=output.getvalue(),
                    file_name="SEO_Audit_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
