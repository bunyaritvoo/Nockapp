import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกคะแนน V6 (Smart Filter)", layout="wide") 

# ลิงก์ Google Sheets ของคุณบาส
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 2. การเชื่อมต่อฐานข้อมูล (Service Account) ---
@st.cache_resource
def get_gspread_client():
    try:
        # ลำดับการเช็กกุญแจ: 1. ตรวจใน Secrets (ออนไลน์) 2. ตรวจไฟล์ในเครื่อง (Local)
        if "gcp_service_account" in st.secrets:
            return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        else:
            # ตรวจสอบชื่อไฟล์ให้ตรงกับในเครื่องคุณบาส (cresds.json หรือ creds.json)
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
        worksheet_data = sh.worksheet("Sheet1")      # สำหรับเก็บคะแนน (A-H)
        worksheet_list = sh.worksheet("StudentList")  # สำหรับรายชื่อ Master (Name, Branch)
        
        # ดึงข้อมูลรายชื่อนักเรียนมาทำ Dropdown
        master_data = pd.DataFrame(worksheet_list.get_all_records())
        master_data['Name'] = master_data['Name'].astype(str).str.strip()
        master_data['Branch'] = master_data['Branch'].astype(str).str.strip()
    except Exception as e:
        st.error(f"🚨 ตรวจพบปัญหาที่ Tab หรือหัวตาราง: {e}")
        st.stop()
else:
    st.error("🚨 ไม่พบไฟล์กุญแจ JSON หรือการตั้งค่า Secrets ไม่ถูกต้อง")
    st.stop()

# --- 3. UI INTERFACE ---
st.title("🎓 ระบบกรอกคะแนนติวเข้า ม.1 กรุงเทพ")
st.markdown("---")

col_form, col_table = st.columns([1, 1.3])

with col_form:
    st.subheader("📝 บันทึกข้อมูลรายคน")
    
    # ดึงรายชื่อสาขาอัตโนมัติจาก Tab StudentList
    all_branches = sorted(master_data['Branch'].unique().tolist())
    selected_branch = st.selectbox("1. เลือกสาขา", ["-- โปรดเลือกสาขา --"] + all_branches)
    
    # กรองชื่อเด็กตามสาขาที่เลือก
    if selected_branch != "-- โปรดเลือกสาขา --":
        names_in_branch = master_data[master_data['Branch'] == selected_branch]['Name'].tolist()
    else:
        names_in_branch = []
        
    student_name = st.selectbox("2. เลือกชื่อนักเรียน", ["-- โปรดเลือกรายชื่อ --"] + names_in_branch)

    # ฟอร์มกรอกคะแนน
    with st.form("input_form_v6", clear_on_submit=True):
        st.write(f"📌 นักเรียน: **{student_name}**")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            year = st.selectbox("ปีการศึกษา", ["2569", "2570", "2571", "2572"])
        with c2:
            month = st.selectbox("เดือน", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน"
                                           , "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
        with c3:
            subject = st.selectbox("วิชา", ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"])
            
        st.divider()
        s1 = st.number_input("คะแนนด้านที่ 1", 0, 100, step=1)
        s2 = st.number_input("คะแนนด้านที่ 2", 0, 100, step=1)
        s3 = st.number_input("คะแนนด้านที่ 3", 0, 100, step=1)
        
        submitted = st.form_submit_button("🚀 บันทึกข้อมูลลงระบบ")

        if submitted:
            if student_name != "-- โปรดเลือกรายชื่อ --":
                try:
                    # ค้นหาแถวแบบฉลาด (ลบช่องว่างทิ้งก่อนเทียบ)
                    all_names_in_sheet = [n.strip() for n in worksheet_data.col_values(1)]
                    
                    if student_name.strip() in all_names_in_sheet:
                        row_idx = all_names_in_sheet.index(student_name.strip()) + 1
                        
                        # เตรียมข้อมูลอัปเดต [Branch, Year, Month, Subject, S1, S2, S3]
                        # ข้อมูลจะไปลงที่คอลัมน์ B, C, D, E, F, G, H
                        update_values = [[selected_branch, year, month, subject, s1, s2, s3]]
                        worksheet_data.update(f"B{row_idx}:H{row_idx}", update_values)
                        
                        st.success(f"✅ บันทึกข้อมูลของ {student_name} เรียบร้อยแล้ว!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ ไม่พบชื่อ '{student_name}' ในหน้า Sheet1 คอลัมน์ A")
                except Exception as e:
                    st.error(f"🚨 เกิดข้อผิดพลาดขณะบันทึก: {e}")
            else:
                st.warning("⚠️ โปรดเลือกชื่อนักเรียนก่อนกดบันทึก")

with col_table:
    # ส่วนโชว์ตารางที่กรองตามสาขา
    branch_display = selected_branch if selected_branch != "-- โปรดเลือกสาขา --" else "ทุกสาขา"
    st.subheader(f"🔍 ตารางคะแนน: {branch_display}")
    
    try:
        # ดึงข้อมูลจาก Sheet1 มาแสดง
        raw_scores = worksheet_data.get_all_records()
        if raw_scores:
            df_display = pd.DataFrame(raw_scores)
            
            # --- ระบบกรองตารางฝั่งขวาตามสาขาที่เลือกฝั่งซ้าย ---
            if selected_branch != "-- โปรดเลือกสาขา --":
                # กรองให้เหลือเฉพาะเด็กในสาขานั้นๆ
                df_display = df_display[df_display['Branch'] == selected_branch]
            
            if not df_display.empty:
                st.dataframe(df_display, use_container_width=True, height=600)
            else:
                st.info(f"ยังไม่มีข้อมูลที่ถูกบันทึกของสาขา '{selected_branch}'")
        else:
            st.info("ยังไม่มีข้อมูลในระบบ (Sheet1 ว่างเปล่า)")
    except Exception as e:
        st.error(f"ไม่สามารถโหลดตารางได้: {e}")

# ปุ่มสำหรับรีเฟรชข้อมูลหน้าเว็บ
if st.button("🔄 รีเฟรชตาราง"):
    st.rerun()