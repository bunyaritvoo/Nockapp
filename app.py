import streamlit as st
import pandas as pd
import gspread

# --- CONFIG ---
st.set_page_config(page_title="ระบบบันทึกคะแนน V4 (Smart Filter)", layout="wide") 

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 1. การเชื่อมต่อ ---
try:
    if "gcp_service_account" in st.secrets:
        gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    else:
        gc = gspread.service_account(filename="creds.json") 
        
    sh = gc.open_by_url(SPREADSHEET_URL)
    worksheet = sh.sheet1 # ชีทหลักสำหรับบันทึกคะแนน
    
    # ดึงรายชื่อเด็กและสาขาจาก Tab 'StudentList' มาทำเป็น DataFrame
    student_sheet = sh.worksheet("StudentList")
    df_master = pd.DataFrame(student_sheet.get_all_records())
except Exception as e:
    st.error(f"🚨 การเชื่อมต่อมีปัญหา: {e}")
    st.stop()

# --- UI INTERFACE ---
st.title("🎓 ระบบจัดการคะแนน - สาขาสัมพันธ์ (V4)")

col_form, col_table = st.columns([1, 1.2])

with col_form:
    st.subheader("📝 บันทึกคะแนน")
    
    with st.form("smart_update_form", clear_on_submit=True):
        # 1. เลือกสาขาก่อน
        branch_list = ["-- เลือกสาขา --"] + sorted(df_master['Branch'].unique().tolist())
        selected_branch = st.selectbox("1. เลือกสาขา", branch_list)
        
        # 2. กรองรายชื่อเด็กตามสาขาที่เลือก
        if selected_branch != "-- เลือกสาขา --":
            filtered_names = df_master[df_master['Branch'] == selected_branch]['Name'].tolist()
        else:
            filtered_names = []
            
        # 3. Dropdown ชื่อเด็กจะเปลี่ยนไปตามสาขา
        student_name = st.selectbox("2. เลือกชื่อนักเรียน", ["-- โปรดเลือกรายชื่อ --"] + filtered_names)

        c1, c2 = st.columns(2)
        with c1:
            month = st.selectbox("เดือนที่สอบ", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
                                                "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
        with c2:
            subject = st.selectbox("วิชา", ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"])

        st.divider()
        s1 = st.number_input("คะแนนด้านที่ 1", 0, 100, step=1)
        s2 = st.number_input("คะแนนด้านที่ 2", 0, 100, step=1)
        s3 = st.number_input("คะแนนด้านที่ 3", 0, 100, step=1)

        submitted = st.form_submit_button("🚀 บันทึกข้อมูล")

        if submitted:
            if student_name != "-- โปรดเลือกรายชื่อ --":
                try:
                    # ค้นหาแถวของเด็กคนนั้นในแผ่นงานหลัก (worksheet)
                    cell = worksheet.find(student_name)
                    row_idx = cell.row
                    
                    # อัปเดตข้อมูล (Branch, Month, Subject, S1, S2, S3)
                    update_values = [[selected_branch, month, subject, s1, s2, s3]]
                    worksheet.update(f"B{row_idx}:G{row_idx}", update_values)
                    
                    st.success(f"อัปเดตคะแนนของ '{student_name}' (สาขา {selected_branch}) เรียบร้อย!")
                    st.balloons()
                    st.rerun()
                except:
                    st.error("ไม่พบชื่อนักเรียนคนนี้ในตารางบันทึกคะแนน กรุณาตรวจสอบชื่อใน Sheet1")
            else:
                st.warning("กรุณาเลือกชื่อนักเรียนก่อนครับ")

with col_table:
    st.subheader("🔍 ตารางคะแนนรวม")
    try:
        data = worksheet.get_all_records()
        if data:
            df_current = pd.DataFrame(data)
            st.dataframe(df_current, use_container_width=True, height=600)
    except:
        st.write("กำลังรอข้อมูล...")