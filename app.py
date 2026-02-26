import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกคะแนน V6 (Filter Mode)", layout="wide") 

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 1. การเชื่อมต่อฐานข้อมูล ---
@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        else:
            return gspread.service_account(filename="creds.json")
    except Exception as e:
        st.error(f"🚨 เชื่อมต่อไม่ได้: {e}")
        return None

gc = get_gspread_client()

if gc:
    try:
        sh = gc.open_by_url(SPREADSHEET_URL)
        worksheet_data = sh.worksheet("Sheet1")
        worksheet_list = sh.worksheet("StudentList")
        
        master_data = worksheet_list.get_all_records()
        df_master = pd.DataFrame(master_data)
        df_master['Name'] = df_master['Name'].astype(str).str.strip()
        df_master['Branch'] = df_master['Branch'].astype(str).str.strip()
    except Exception as e:
        st.error(f"🚨 หา Tab ไม่เจอ หรือหัวตารางไม่ถูกต้อง: {e}")
        st.stop()
else:
    st.stop()

# --- UI INTERFACE ---
st.title("🎓 ระบบจัดการคะแนน (Smart Filter & Year Support)")

col_form, col_table = st.columns([1, 1.3])

with col_form:
    st.subheader("📝 บันทึกคะแนน")
    
    # ดึงรายชื่อสาขาอัตโนมัติ
    all_branches = sorted(df_master['Branch'].unique().tolist())
    selected_branch = st.selectbox("1. เลือกสาขา", ["-- โปรดเลือกสาขา --"] + all_branches)
    
    # กรองชื่อเด็กตามสาขา
    if selected_branch != "-- โปรดเลือกสาขา --":
        names_in_branch = df_master[df_master['Branch'] == selected_branch]['Name'].tolist()
    else:
        names_in_branch = []
        
    student_name = st.selectbox("2. เลือกชื่อนักเรียน", ["-- โปรดเลือกรายชื่อ --"] + names_in_branch)

    with st.form("score_v6_form", clear_on_submit=True):
        st.write(f"📍 บันทึกข้อมูล: **{student_name}**")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            # เพิ่มการเลือกปี
            year = st.selectbox("ปีการศึกษา", ["2567", "2568", "2569", "2570"])
        with c2:
            month = st.selectbox("เดือน", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน"
                                           , "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
        with c3:
            subject = st.selectbox("วิชา", ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"])
        
        st.divider()
        s1 = st.number_input("ด้านที่ 1", 0, 100)
        s2 = st.number_input("ด้านที่ 2", 0, 100)
        s3 = st.number_input("ด้านที่ 3", 0, 100)
        
        submitted = st.form_submit_button("🚀 บันทึก")

        if submitted:
            if student_name != "-- โปรดเลือกรายชื่อ --":
                try:
                    cell = worksheet_data.find(student_name)
                    row_idx = cell.row
                    
                    # อัปเดตลงคอลัมน์ B ถึง H (เพิ่ม Year เข้ามา)
                    update_data = [[selected_branch, year, month, subject, s1, s2, s3]]
                    worksheet_data.update(f"B{row_idx}:H{row_idx}", update_data)
                    
                    st.success(f"บันทึกคะแนนปี {year} ของ {student_name} สำเร็จ!")
                    st.balloons()
                    st.rerun()
                except:
                    st.error("ไม่พบชื่อนักเรียนใน Sheet1")
            else:
                st.warning("กรุณาเลือกรายชื่อก่อนครับ")

with col_table:
    st.subheader(f"🔍 ข้อมูลเฉพาะ: {selected_branch if selected_branch != '-- โปรดเลือกสาขา --' else 'ทุกสาขา'}")
    try:
        all_scores = worksheet_data.get_all_records()
        if all_scores:
            df_display = pd.DataFrame(all_scores)
            
            # --- จุดที่แก้: ระบบกรองตารางตามสาขาที่เลือกด้านซ้าย ---
            if selected_branch != "-- โปรดเลือกสาขา --":
                df_display = df_display[df_display['Branch'] == selected_branch]
            
            if not df_display.empty:
                st.dataframe(df_display, use_container_width=True, height=600)
            else:
                st.info(f"ยังไม่มีการบันทึกข้อมูลของสาขา {selected_branch}")
        else:
            st.info("ยังไม่มีข้อมูลในระบบ")
    except:
        st.write("ระบบกำลังเตรียมตาราง...")