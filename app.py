import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกคะแนน V7 (History Mode)", layout="wide") 

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 2. การเชื่อมต่อฐานข้อมูล ---
@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        else:
            for key_name in ["cresds.json", "creds.json", "cresds", "creds"]:
                if os.path.exists(key_name):
                    return gspread.service_account(filename=key_name)
        return None
    except Exception as e:
        st.error(f"🚨 ไม่สามารถเชื่อมต่อ Google API ได้: {e}")
        return None

gc = get_gspread_client()

if gc:
    try:
        sh = gc.open_by_url(SPREADSHEET_URL)
        worksheet_data = sh.worksheet("Sheet1")      
        worksheet_list = sh.worksheet("StudentList")  
        
        # ดึงข้อมูล Master สำหรับ Dropdown
        master_data = pd.DataFrame(worksheet_list.get_all_records())
        master_data['Name'] = master_data['Name'].astype(str).str.strip()
        master_data['Branch'] = master_data['Branch'].astype(str).str.strip()
    except Exception as e:
        st.error(f"🚨 ปัญหาที่ Tab หรือหัวตาราง: {e}")
        st.stop()
else:
    st.stop()

# --- 3. UI INTERFACE ---
st.title("🎓 ระบบกรอกคะแนนติวเข้าม.1 กรุงเทพ")

col_form, col_table = st.columns([1, 1.3])

with col_form:
    st.subheader("📝 บันทึกข้อมูลใหม่")
    
    # ดึงรายชื่อสาขา
    all_branches = sorted(master_data['Branch'].unique().tolist())
    selected_branch = st.selectbox("1. เลือกสาขา", ["-- โปรดเลือกสาขา --"] + all_branches)
    
    # กรองชื่อเด็กตามสาขา
    if selected_branch != "-- โปรดเลือกสาขา --":
        names_in_branch = master_data[master_data['Branch'] == selected_branch]['Name'].tolist()
    else:
        names_in_branch = []
        
    student_name = st.selectbox("2. เลือกชื่อนักเรียน", ["-- โปรดเลือกรายชื่อ --"] + names_in_branch)

    with st.form("append_form_v7", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            year = st.selectbox("ปีการศึกษา", ["2569", "2570", "2571", "2572"])
        with c2:
            month = st.selectbox("เดือน", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน"
                                           ,"กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
        with c3:
            subject = st.selectbox("วิชา", ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"])
            
        st.divider()
        s1 = st.number_input("คะแนนด้านที่ 1", 0, 100, step=1)
        s2 = st.number_input("คะแนนด้านที่ 2", 0, 100, step=1)
        s3 = st.number_input("คะแนนด้านที่ 3", 0, 100, step=1)
        
        submitted = st.form_submit_button("🚀 บันทึกข้อมูลใหม่")

        if submitted:
            if student_name != "-- โปรดเลือกรายชื่อ --":
                try:
                    # --- จุดที่เปลี่ยน: ใช้ append_row เพื่อเพิ่มแถวใหม่ แทนการ update แถวเดิม ---
                    new_row = [student_name, selected_branch, year, month, subject, s1, s2, s3]
                    worksheet_data.append_row(new_row)
                    
                    st.success(f"✅ บันทึกวิชา {subject} ของ {student_name} เรียบร้อยแล้ว!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"🚨 เกิดข้อผิดพลาด: {e}")
            else:
                st.warning("⚠️ โปรดเลือกชื่อนักเรียนก่อนครับ")

with col_table:
    branch_display = selected_branch if selected_branch != "-- โปรดเลือกสาขา --" else "ทุกสาขา"
    st.subheader(f"🔍 ประวัติการบันทึก: {branch_display}")
    
    try:
        raw_scores = worksheet_data.get_all_records()
        if raw_scores:
            df_display = pd.DataFrame(raw_scores)
            
            # กรองตารางตามสาขาที่เลือก
            if selected_branch != "-- โปรดเลือกสาขา --":
                df_display = df_display[df_display['Branch'] == selected_branch]
            
            if not df_display.empty:
                # เรียงข้อมูลเอาอันใหม่ล่าสุดไว้ข้างบน (Optional)
                st.dataframe(df_display.iloc[::-1], use_container_width=True, height=600)
            else:
                st.info(f"ยังไม่มีข้อมูลของสาขา '{selected_branch}'")
        else:
            st.info("ยังไม่มีข้อมูลในระบบ")
    except Exception as e:
        st.error(f"ไม่สามารถโหลดตารางได้: {e}")