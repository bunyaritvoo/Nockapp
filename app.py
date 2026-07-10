import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import urllib.request
import gspread
import os
import textwrap

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกคะแนนติวเข้าม.1", layout="wide") 
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 2. โหลดฟอนต์ภาษาไทย ---
@st.cache_resource
def load_thai_font():
    font_url = "https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Regular.ttf"
    font_path = "Sarabun-Regular.ttf"
    if not os.path.exists(font_path): 
        urllib.request.urlretrieve(font_url, font_path)
    fm.fontManager.addfont(font_path)
    return (
        fm.FontProperties(fname=font_path, size=12), 
        fm.FontProperties(fname=font_path, size=16, weight='bold'), 
        fm.FontProperties(fname=font_path, size=20, weight='bold')
    )

prop_normal, prop_title, prop_header = load_thai_font()
prop_comment = fm.FontProperties(fname="Sarabun-Regular.ttf", size=14)

# --- 3. การเชื่อมต่อฐานข้อมูล (ระบบ Cache ป้องกัน API โดนแบน) ---
@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets: 
            return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        else:
            key_file = "cresds.json" if os.path.exists("cresds.json") else "creds.json"
            return gspread.service_account(filename=key_file)
    except: 
        return None

gc = get_gspread_client()
if not gc: 
    st.error("🚨 เชื่อมต่อ Google API ไม่ได้")
    st.stop()

@st.cache_resource
def get_spreadsheet():
    return gc.open_by_url(SPREADSHEET_URL)

try:
    sh = get_spreadsheet()
except Exception as e:
    st.error(f"🚨 เชื่อมต่อไฟล์ Google Sheets ไม่ได้: {e}")
    st.stop()

@st.cache_data(ttl=600)
def load_core_data():
    m_data = pd.DataFrame(sh.worksheet("StudentList").get_all_records())
    t_data = pd.DataFrame(sh.worksheet("TopicSettings").get_all_records())
    try: 
        c_data = pd.DataFrame(sh.worksheet("Comments").get_all_records())
    except: 
        c_data = pd.DataFrame()
    return m_data, t_data, c_data

try:
    master_data, df_topics, df_comments = load_core_data()
except Exception as e:
    st.error(f"🚨 โหลดข้อมูลเริ่มต้นไม่ได้ (อาจโดนจำกัดโควต้าการดึงข้อมูล กรุณารอ 1 นาทีแล้วรีเฟรชหน้าเว็บ): {e}")
    st.stop()

@st.cache_data(ttl=600)
def load_month_df(month_name):
    try:
        ws = sh.worksheet(month_name)
        df = pd.DataFrame(ws.get_all_values())
        if not df.empty:
            df.columns = df.iloc[0]
            df = df[1:].reset_index(drop=True)
        return df
    except:
        return pd.DataFrame()

def get_real_comment(subject, total_score, full_score):
    if df_comments.empty: 
        return "ไม่พบหน้าตาราง Comments ใน Google Sheets"
    if full_score == 0: 
        return "คะแนนเต็มรวมเป็น 0 ไม่สามารถคำนวณได้"
    
    percent_score = (total_score / full_score) * 100
    col_map = {'คณิตศาสตร์': 'Comment_math', 'วิทยาศาสตร์': 'Comment_sci', 'ภาษาอังกฤษ': 'Comment_eng'}
    target_col = col_map.get(subject)
    
    if not target_col or target_col not in df_comments.columns:
        return f"ไม่พบคอลัมน์ {target_col} ในหน้า Comments"

    for _, row in df_comments.iterrows():
        try:
            range_str = str(row.get('เกณฑ์คะแนน', '')).strip()
            if '-' in range_str:
                min_s, max_s = map(int, range_str.split('-'))
                if min_s <= round(percent_score) <= max_s:
                    return str(row[target_col])
        except: 
            continue
    return "คะแนนไม่อยู่ในเกณฑ์ที่ตั้งไว้"

def format_radar_label(label):
    label = label.strip()
    if "Demonstrative" in label:
        return label.replace("/", "\n")
    elif "Countable" in label and "Uncountable" in label:
        return "Countable and\nUncountable Nouns"
    elif "Singular" in label and "Plural" in label:
        return "Singular &\nPlural Nouns"
    elif "Auxiliary" in label:
        return "Auxiliary Verb\nand Modal Verb"
    elif "ตัวประกอบของจำนวนนับ" in label:
        return "ตัวประกอบของจำนวนนับ\nห.ร.ม. ค.ร.น."
    return "\n".join(textwrap.wrap(label, width=22, break_long_words=False))

# --- 4. UI INTERFACE ---
st.title("🎓 ระบบจัดการคะแนนและรายงานผล")
tab_entry, tab_dashboard, tab_stat, tab_trend = st.tabs(["📝 บันทึกข้อมูล", "📊 พิมพ์รายงานผล (Report Card)", "📈 สถิติภาพรวม", "📈 วิเคราะห์พัฒนาการ"])

# ==========================================
# 🌟 TAB 1: บันทึกข้อมูล
# ==========================================
with tab_entry:
    col_form, col_table = st.columns([1, 1.3])
    with col_form:
        target_month = st.selectbox("เลือกเดือน (สำหรับบันทึก)", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"], key="entry_month")
        try:
            ws_current = sh.worksheet(target_month)
            df_month = load_month_df(target_month)
            if df_month.empty: raise Exception
        except: 
            st.error(f"❌ ไม่พบหน้า Sheet ชื่อ '{target_month}'")
            st.stop()

        branches = sorted(master_data['Branch'].unique().tolist())
        selected_branch = st.selectbox("สาขา", ["-- โปรดเลือกสาขา --"] + branches)
        names = master_data[master_data['Branch'] == selected_branch]['Name'].tolist() if selected_branch != "-- โปรดเลือกสาขา --" else []
        student_name = st.selectbox("นักเรียน", ["-- โปรดเลือกรายชื่อ --"] + names)

        available_subjects = df_month[df_month.iloc[:, 0].str.strip() == student_name.strip()].iloc[:, 1].unique().tolist()
        selected_subject = st.selectbox("วิชา", ["-- เลือกวิชา --"] + available_subjects)

        topic_labels, topic_fulls = [], []

        if selected_subject != "-- เลือกวิชา --":
            match_topic = df_topics[(df_topics['Month'].astype(str).str.strip() == target_month.strip()) & (df_topics['Subject'].astype(str).str.strip() == selected_subject.strip())]
            if not match_topic.empty:
                row = match_topic.iloc[0]
                for i in range(1, 8):
                    t_name = str(row.get(f'Topic_{i}', '')).strip()
                    if t_name and t_name.lower() != 'nan' and t_name != '':
                        topic_labels.append(t_name)
                        try: 
                            topic_fulls.append(int(row.get(f'FullScore_{i}', 10)))
                        except: 
                            topic_fulls.append(10)
            
            if not topic_labels:
                topic_labels, topic_fulls = ["ด.1", "ด.2", "ด.3"], [10, 10, 10]

            st.divider()
            
            with st.form("update_dynamic_form"):
                year = st.selectbox("ปีการศึกษา", ["2568", "2569", "2570", "2571"], index=1)
                st.markdown("**กรอกคะแนนรายหัวข้อ:**")
                
                input_scores = []
                cols = st.columns(len(topic_labels))
                for idx, col in enumerate(cols):
                    with col:
                        val = st.number_input(f"{topic_labels[idx]} (เต็ม {topic_fulls[idx]})", min_value=0, max_value=topic_fulls[idx], value=0, key=f"score_{idx}")
                        input_scores.append(val)
                
                if st.form_submit_button("🚀 บันทึกข้อมูล"):
                    try:
                        found = False
                        for i, r in enumerate(ws_current.get_all_values()):
                            if r[0].strip() == student_name.strip() and r[1].strip() == selected_subject.strip():
                                end_col_char = chr(ord('C') + 2 + len(input_scores))
                                update_range = f"C{i+1}:{end_col_char}{i+1}"
                                update_values = [[target_month, year, selected_branch] + input_scores]
                                
                                ws_current.update(update_range, update_values)
                                st.cache_data.clear() 
                                st.success("✅ บันทึกสำเร็จ!")
                                st.balloons()
                                st.rerun()
                                found = True
                                break
                        if not found: 
                            st.error("❌ ไม่พบแถวข้อมูลนักเรียนรายวิชานี้ในชีตประจำเดือน")
                    except Exception as e: 
                        st.error(f"🚨 ข้อผิดพลาด: {e}")

    with col_table:
        st.subheader(f"🔍 ตาราง: {target_month}")
        if not df_month.empty:
            display_df = df_month.copy()
            if selected_branch != "-- โปรดเลือกสาขา --": 
                display_df = display_df[display_df.iloc[:, 4] == selected_branch]
            st.dataframe(display_df, use_container_width=True, height=600)

# ==========================================
# 🌟 TAB 2: กราฟ + ดึงคอมเมนต์อัตโนมัติตามช่วงคะแนน
# ==========================================
with tab_dashboard:
    col_rep1, col_rep2 = st.columns(2)
    with col_rep1:
        report_month = st.selectbox("เลือกเดือน (สำหรับออกรายงาน)", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"], index=4, key="report_month_select")
    with col_rep2:
        report_year = st.selectbox("เลือกปีการศึกษา (สำหรับออกรายงาน)", ["2568", "2569", "2570", "2571"], index=1, key="report_year_select")

    st.subheader(f"📄 พิมพ์รายงานผลการเรียนรู้: เดือน {report_month} ปี {report_year}")
    
    df_report = load_month_df(report_month)
    if df_report.empty:
        st.error(f"❌ ไม่พบหน้าตารางข้อมูล (Sheet) ของเดือน '{report_month}'")
    else:
        year_col = df_report.columns[3]
        df_report = df_report[df_report[year_col].astype(str).str.strip() == report_year.strip()]

        if not df_report.empty:
            all_students = sorted([n for n in df_report.iloc[:, 0].astype(str).str.strip().unique().tolist() if n])
            report_student = st.selectbox("เลือกนักเรียน", ["-- เลือกนักเรียน --"] + all_students)

            if report_student != "-- เลือกนักเรียน --":
                student_data = df_report[df_report.iloc[:, 0].str.strip() == report_student]
                subjects_taken = student_data.iloc[:, 1].str.strip().tolist()

                if subjects_taken:
                    fig = plt.figure(figsize=(18, 12))
                    
                    fig.subplots_adjust(top=0.82, hspace=0.4, wspace=0.3)
                    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 1.2])
                    fig.suptitle(f'รายงานผลการเรียนรู้: {report_student} (เดือน {report_month} ปี {report_year})', fontproperties=prop_header, fontsize=28, y=0.96)

                    ax_dict = {
                        "คณิตศาสตร์": fig.add_subplot(gs[0, 0], polar=True),
                        "วิทยาศาสตร์": fig.add_subplot(gs[1, 0], polar=True),
                        "ภาษาอังกฤษ": fig.add_subplot(gs[1, 1], polar=True)
                    }
                    colors = {"คณิตศาสตร์": "blue", "วิทยาศาสตร์": "red", "ภาษาอังกฤษ": "green"}
                    
                    ax_stats = fig.add_subplot(gs[0, 1])
                    ax_stats.axis('off')
                    ax_stats.set_ylim(0, 100)
                    ax_stats.set_xlim(0, 100)
                    
                    ax_text = fig.add_subplot(gs[:, 2])
                    ax_text.axis('off')
                    ax_text.set_ylim(0, 100)
                    ax_text.set_xlim(0, 100)
                    
                    comment_texts = {"คณิตศาสตร์": "ยังไม่มีข้อมูล", "วิทยาศาสตร์": "ยังไม่มีข้อมูล", "ภาษาอังกฤษ": "ยังไม่มีข้อมูล"}
                    stats_texts = {}

                    for subj in subjects_taken:
                        if subj not in ax_dict: 
                            continue
                        ax = ax_dict[subj]
                        
                        t_labels, t_fulls = [], []
                        match_topic = df_topics[(df_topics['Month'].astype(str).str.strip() == report_month) & (df_topics['Subject'].astype(str).str.strip() == subj)]
                        if not match_topic.empty:
                            row = match_topic.iloc[0]
                            for i in range(1, 8):
                                t_name = str(row.get(f'Topic_{i}', '')).strip()
                                if t_name and t_name.lower() != 'nan' and t_name != '':
                                    t_labels.append(t_name)
                                    try: 
                                        t_fulls.append(int(row.get(f'FullScore_{i}', 10)))
                                    except: 
                                        t_fulls.append(10)

                        if not t_labels:
                            t_labels, t_fulls = ["T1", "T2", "T3"], [10, 10, 10]

                        subj_row = student_data[student_data.iloc[:, 1].str.strip() == subj].iloc[0]
                        student_branch_val = str(subj_row.iloc[4]).strip()
                        
                        scores_raw = []
                        for idx in range(len(t_labels)):
                            try:
                                val_str = str(subj_row.iloc[5 + idx]).strip()
                                scores_raw.append(float(val_str) if val_str else 0.0)
                            except:
                                scores_raw.append(0.0)

                        scores_norm = [(s/f)*10 if f>0 else 0 for s, f in zip(scores_raw, t_fulls)]
                        total_score = sum(scores_raw)
                        sum_full_score = sum(t_fulls)
                        calc_percent = (total_score / sum_full_score) * 100 if sum_full_score > 0 else 0.0

                        mask = (df_report.iloc[:, 1].astype(str).str.strip() == subj) & (df_report.iloc[:, 4].astype(str).str.strip() == student_branch_val)
                        peer_data = df_report[mask]
                        
                        peer_totals = []
                        for _, prow in peer_data.iterrows():
                            p_scores = []
                            for idx in range(len(t_labels)):
                                try:
                                    val_s = str(prow.iloc[5 + idx]).strip()
                                    p_scores.append(float(val_s) if val_s else 0.0)
                                except:
                                    p_scores.append(0.0)
                            peer_totals.append(sum(p_scores))
                            
                        if peer_totals:
                            stat_min = min(peer_totals)
                            stat_max = max(peer_totals)
                            stat_mean = sum(peer_totals) / len(peer_totals)
                            stats_texts[subj] = f"Max: {stat_max:g}   |   Min: {stat_min:g}   |   Mean: {stat_mean:.1f}"
                        else:
                            stats_texts[subj] = "ไม่มีข้อมูลสถิติ"

                        num_vars = len(t_labels)
                        angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
                        angles += angles[:1]
                        scores_norm += scores_norm[:1]
                        
                        ax.set_theta_offset(np.pi / 2)
                        ax.set_theta_direction(-1)
                        ax.set_xticks(angles[:-1])
                        
                        wrapped_labels = [format_radar_label(l) for l in t_labels]
                        ax.set_xticklabels(wrapped_labels, fontproperties=prop_normal, fontsize=10)
                        ax.set_yticks(np.arange(0, 11, 2))
                        ax.set_ylim(0, 10)
                        
                        line_color = colors.get(subj, "gray")
                        ax.plot(angles, scores_norm, color=line_color, linewidth=2)
                        ax.fill(angles, scores_norm, color=line_color, alpha=0.25)
                        
                        ax.set_title(f"วิชา {subj}", color=line_color, y=1.1, fontproperties=prop_title)

                        fetched_comment = get_real_comment(subj, total_score, sum_full_score)
                        comment_texts[subj] = f"คะแนนรวม: {total_score}/{sum_full_score} (คิดเป็น {calc_percent:.1f}%)\nความเห็น:\n{fetched_comment}"

                    for subj, ax in ax_dict.items():
                        if subj not in subjects_taken: 
                            ax.axis('off')

                    ax_stats.text(0, 95, "📊 สถิติเปรียบเทียบในสาขา", fontproperties=prop_title, color='#333333', ha='left', va='top', fontsize=15)
                    
                    y_stat = 75
                    for subj in ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"]:
                        if subj in subjects_taken:
                            ax_stats.text(0, y_stat, f"• {subj}", fontproperties=prop_title, color=colors.get(subj, "black"), ha='left', va='top')
                            ax_stats.text(5, y_stat - 12, stats_texts[subj], fontproperties=prop_comment, color='#555555', ha='left', va='top')
                            y_stat -= 28 

                    y_current = 98 
                    for subj in ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"]:
                        ax_text.text(0, y_current, f"รายงานผล: {subj}", color=colors.get(subj, "black"), fontproperties=prop_title, ha='left', va='top')
                        y_current -= 4 
                        
                        wrapped_text = "\n".join(textwrap.wrap(comment_texts[subj], width=55, break_long_words=False))
                        ax_text.text(0, y_current, wrapped_text, color='#333333', fontproperties=prop_comment, ha='left', va='top', linespacing=1.5)
                        
                        num_lines = len(wrapped_text.split('\n'))
                        y_current -= (num_lines * 2.8) + 12

                    st.pyplot(fig)
                else: 
                    st.info("ไม่พบข้อมูลลงทะเบียนเรียนวิชาของนักเรียนคนนี้")
        else:
            st.warning(f"ไม่มีข้อมูลการสอบของนักเรียนในปีการศึกษา {report_year} สำหรับเดือน {report_month}")

# ==========================================
# 🌟 TAB 3: สถิติภาพรวม
# ==========================================
with tab_stat:
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        stat_month = st.selectbox("เลือกเดือน (สำหรับดูสถิติ)", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"], index=4, key="stat_month_select")
    with col_stat2:
        stat_year = st.selectbox("เลือกปีการศึกษา (สำหรับดูสถิติ)", ["2568", "2569", "2570", "2571"], index=1, key="stat_year_select")

    st.subheader(f"📈 สถิติคะแนนภาพรวม: เดือน {stat_month} ปี {stat_year}")
    
    df_stat = load_month_df(stat_month)
        
    if not df_stat.empty:
        year_col = df_stat.columns[3]
        df_stat = df_stat[df_stat[year_col].astype(str).str.strip() == stat_year.strip()]
        
        if not df_stat.empty:
            score_cols = df_stat.columns[5:]
            for col in score_cols:
                df_stat[col] = pd.to_numeric(df_stat[col], errors='coerce').fillna(0)
            
            df_stat['Total_Score'] = df_stat[score_cols].sum(axis=1)
            df_stat = df_stat[df_stat.iloc[:, 1].astype(str).str.strip() != '']
            df_stat = df_stat[df_stat.iloc[:, 1].notna()]
            
            if not df_stat.empty:
                branch_col = df_stat.columns[4]
                subj_col = df_stat.columns[1]
                
                stat_summary = df_stat.groupby([branch_col, subj_col])['Total_Score'].agg(
                    Min='min', 
                    Max='max', 
                    Mean='mean',
                    Count='count'
                ).reset_index()
                
                stat_summary.columns = ['สาขา', 'วิชา', 'คะแนนต่ำสุด (Min)', 'คะแนนสูงสุด (Max)', 'คะแนนเฉลี่ย (Mean)', 'จำนวนนักเรียนสอบ']
                stat_summary['คะแนนเฉลี่ย (Mean)'] = stat_summary['คะแนนเฉลี่ย (Mean)'].round(2)
                
                st.dataframe(stat_summary, use_container_width=True)
                st.divider()
                st.markdown(f"### 📊 กราเปรียบเทียบคะแนนเฉลี่ย (เดือน {stat_month} ปี {stat_year})")
                
                fig_stat, ax_stat = plt.subplots(figsize=(12, 6))
                pivot_stat = stat_summary.pivot(index='วิชา', columns='สาขา', values='คะแนนเฉลี่ย (Mean)')
                pivot_stat.plot(kind='bar', ax=ax_stat, width=0.6, alpha=0.85)
                
                ax_stat.set_title(f'เปรียบเทียบคะแนนเฉลี่ย: {stat_month} {stat_year}', fontproperties=prop_header, pad=20)
                ax_stat.set_xlabel('รายวิชา', fontproperties=prop_title, labelpad=10)
                ax_stat.set_ylabel('คะแนนเฉลี่ย (คะแนนดิบรวม)', fontproperties=prop_title, labelpad=10)
                
                ax_stat.set_xticklabels(pivot_stat.index, fontproperties=prop_normal, rotation=0, fontsize=14)
                for label in ax_stat.get_yticklabels():
                    label.set_fontproperties(prop_normal)
                    label.set_fontsize(12)
                    
                ax_stat.legend(prop=prop_normal, title="สาขา", title_fontproperties=prop_title)
                fig_stat.tight_layout()
                st.pyplot(fig_stat)
            else:
                st.info(f"ไม่พบข้อมูลนักเรียนที่มีคะแนนในเดือน {stat_month} ปี {stat_year}")
        else:
            st.warning(f"ไม่มีข้อมูลการสอบของนักเรียนในปีการศึกษา {stat_year} สำหรับเดือน {stat_month}")
    else:
        st.error(f"❌ ไม่พบหน้าตารางข้อมูล (Sheet) ของเดือน '{stat_month}'")

# ==========================================
# 🌟 TAB 4: วิเคราะห์พัฒนาการระยะยาว (Trend Analysis) 3 วิชา
# ==========================================
with tab_trend:
    st.subheader("📈 วิเคราะห์พัฒนาการระยะยาว (รวม 3 วิชา)")

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        trend_year = st.selectbox("เลือกปีการศึกษา", ["2568", "2569", "2570", "2571"], index=1, key="trend_year")
    with col_t2:
        all_branches_trend = sorted(master_data['Branch'].unique().tolist())
        trend_branch = st.selectbox("สาขา", ["-- โปรดเลือกสาขา --"] + all_branches_trend, key="trend_branch")
    with col_t3:
        trend_names = master_data[master_data['Branch'] == trend_branch]['Name'].tolist() if trend_branch != "-- โปรดเลือกสาขา --" else []
        trend_student = st.selectbox("นักเรียน", ["-- โปรดเลือกรายชื่อ --"] + trend_names, key="trend_student")

    all_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    selected_months = st.multiselect("เลือกเดือนที่ต้องการเปรียบเทียบ (เรียงตามเวลาการสอบ)", all_months, default=["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน"], key="trend_months")

    if st.button("🔍 เริ่มวิเคราะห์พัฒนาการ", use_container_width=True):
        if trend_student != "-- โปรดเลือกรายชื่อ --" and len(selected_months) > 1:
            with st.spinner("กำลังรวบรวมข้อมูลข้ามเดือน... อาจใช้เวลาสักครู่"):
                trend_data = []
                subjects_to_analyze = ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"]

                for m in selected_months:
                    try:
                        df_m = load_month_df(m)
                        if not df_m.empty:
                            month_record = {"เดือน": m}
                            has_any_data = False
                            
                            for subj in subjects_to_analyze:
                                student_row = df_m[(df_m.iloc[:, 0].str.strip() == trend_student) & 
                                                   (df_m.iloc[:, 1].str.strip() == subj) & 
                                                   (df_m.iloc[:, 3].astype(str).str.strip() == trend_year.strip())]

                                if not student_row.empty:
                                    row_data = student_row.iloc[0]
                                    match_topic = df_topics[(df_topics['Month'].astype(str).str.strip() == m) & 
                                                            (df_topics['Subject'].astype(str).str.strip() == subj)]

                                    t_fulls = []
                                    if not match_topic.empty:
                                        t_row = match_topic.iloc[0]
                                        for i in range(1, 8):
                                            t_name = str(t_row.get(f'Topic_{i}', '')).strip()
                                            if t_name and t_name.lower() != 'nan' and t_name != '':
                                                try: t_fulls.append(int(t_row.get(f'FullScore_{i}', 10)))
                                                except: t_fulls.append(10)

                                    if not t_fulls: t_fulls = [10, 10, 10]

                                    scores_raw = []
                                    for idx in range(len(t_fulls)):
                                        try:
                                            val_str = str(row_data.iloc[5 + idx]).strip()
                                            scores_raw.append(float(val_str) if val_str else 0.0)
                                        except:
                                            scores_raw.append(0.0)

                                    total_score = sum(scores_raw)
                                    sum_full_score = sum(t_fulls)

                                    if sum_full_score > 0:
                                        percent = (total_score / sum_full_score) * 100
                                        month_record[f"{subj} (%)"] = percent
                                        month_record[f"{subj} (ดิบ)"] = f"{total_score}/{sum_full_score}"
                                        has_any_data = True
                                    else:
                                        month_record[f"{subj} (%)"] = None
                                        month_record[f"{subj} (ดิบ)"] = "0/0"
                                else:
                                    month_record[f"{subj} (%)"] = None
                                    month_record[f"{subj} (ดิบ)"] = "-"
                            
                            if has_any_data:
                                trend_data.append(month_record)
                        else:
                            pass 
                    except Exception as e:
                        pass 

                df_trend = pd.DataFrame(trend_data)

                if not df_trend.empty:
                    st.success(f"พบข้อมูลการสอบจำนวน {len(df_trend)} เดือน จากที่เลือกไว้ทั้งหมด {len(selected_months)} เดือน")
                    st.divider()
                    
                    st.markdown(f"### 📈 แนวโน้มผลการเรียน 3 วิชาหลัก")
                    st.markdown(f"**นักเรียน:** {trend_student} | **ปีการศึกษา:** {trend_year}")

                    # 🌟 วาดกราฟ 3 เส้น ลงบนพื้นที่เดียวกัน 🌟
                    fig_trend, ax_trend = plt.subplots(figsize=(14, 6))
                    colors = {"คณิตศาสตร์": "blue", "วิทยาศาสตร์": "red", "ภาษาอังกฤษ": "green"}

                    for subj in subjects_to_analyze:
                        col_percent = f"{subj} (%)"
                        if col_percent in df_trend.columns:
                            mask = df_trend[col_percent].notna() # วาดเส้นเฉพาะเดือนที่มีคะแนน
                            if mask.any():
                                ax_trend.plot(df_trend.loc[mask, 'เดือน'], df_trend.loc[mask, col_percent], 
                                              marker='o', linestyle='-', color=colors[subj], markersize=10, linewidth=2.5, label=subj)
                                
                                # ใส่ตัวเลขกำกับจุดไข่ปลา
                                for i, txt in enumerate(df_trend.loc[mask, col_percent]):
                                    ax_trend.annotate(f"{txt:.1f}%", (df_trend.loc[mask, 'เดือน'].iloc[i], df_trend.loc[mask, col_percent].iloc[i]),
                                                      textcoords="offset points", xytext=(0,12), ha='center', fontproperties=prop_title, color=colors[subj])

                    ax_trend.set_ylim(0, 115) 
                    ax_trend.set_ylabel('ผลการเรียน (คิดเป็นเปอร์เซ็นต์ %)', fontproperties=prop_title, fontsize=14, labelpad=15)
                    ax_trend.set_title(f'กราฟวิเคราะห์การเติบโตรายวิชา', fontproperties=prop_header, pad=20)

                    # เซ็ตให้แกน X แสดงชื่อเดือน
                    ax_trend.set_xticks(range(len(df_trend['เดือน'])))
                    ax_trend.set_xticklabels(df_trend['เดือน'], fontproperties=prop_normal, fontsize=12)
                    
                    for label in ax_trend.get_yticklabels():
                        label.set_fontproperties(prop_normal)

                    ax_trend.legend(prop=prop_normal, title="วิชา", title_fontproperties=prop_title, loc='lower right')
                    ax_trend.grid(True, linestyle='--', alpha=0.5)
                    
                    st.pyplot(fig_trend)

                    # ตารางสรุปด้านล่าง
                    st.markdown("#### 📋 ตารางสรุปคะแนน")
                    display_cols = ["เดือน"]
                    for subj in subjects_to_analyze:
                        if f"{subj} (ดิบ)" in df_trend.columns:
                            display_cols.append(f"{subj} (%)")
                            display_cols.append(f"{subj} (ดิบ)")
                    
                    st.dataframe(df_trend[display_cols], use_container_width=True)
                else:
                    st.warning("ไม่พบประวัติคะแนนของนักเรียนคนนี้ในเดือนที่คุณเลือกเลยครับ")
        else:
            st.info("⚠️ โปรดเลือกนักเรียน และเดือนที่ต้องการเปรียบเทียบ (อย่างน้อย 2 เดือน) ให้ครบถ้วน แล้วกดปุ่มค้นหาครับ")
