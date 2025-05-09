
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pytz

# === 設定報名截止時間 ===
截止時間 = datetime.datetime(2025, 5, 10, 23, 59, 59, tzinfo=pytz.timezone("Asia/Taipei"))

# === Google Sheets 驗證與讀取 ===
creds = st.secrets["GOOGLE_CREDENTIALS"]
CREDS = Credentials.from_service_account_info(creds, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
])
client = gspread.authorize(CREDS)

# === 開啟各個工作表 ===
sheet_url = "https://docs.google.com/spreadsheets/d/1RrOvJ_UeP5xu2-l-WJwDySn9d786E5P0hsv_XFq9ovg/edit?usp=sharing"
報名紀錄_url = "https://docs.google.com/spreadsheets/d/1awfvTvLPkyZM3sGL41sflHtO7LgTkva-lkWx-2rUu7k/edit?usp=sharing"

try:
    校系表 = client.open_by_url(sheet_url).worksheet("工作表1")
    限制表 = client.open_by_url(sheet_url).worksheet("工作表2")
    群對照 = client.open_by_url(sheet_url).worksheet("工作表3")
    考生表 = client.open_by_url(sheet_url).worksheet("工作表4")
    報名表 = client.open_by_url(報名紀錄_url).sheet1
except Exception as e:
    st.error(f"❌ Google Sheet 讀取失敗：{e}")
    st.stop()

df1 = pd.DataFrame(校系表.get_all_records())
df2 = pd.DataFrame(限制表.get_all_records())
df3 = pd.DataFrame(群對照.get_all_records())
df4 = pd.DataFrame(考生表.get_all_records())

群別選項 = sorted(df3["統測報考群(類)別"].unique())

st.title("📋 高雄高商114學年度 第一階段甄選入學報名系統")

tab1, tab2 = st.tabs(["我要報名", "查詢報名紀錄"])

with tab1:
    if datetime.datetime.now(pytz.timezone("Asia/Taipei")) > 截止時間:
        st.error("📌 報名已截止，無法進行填寫。")
        st.stop()

    st.subheader("🔐 請先進行身份驗證")
    with st.form("verify"):
        col1, col2 = st.columns(2)
        with col1:
            exam_id = st.text_input("統測報名序號")
            id_number = st.text_input("身分證字號")
        with col2:
            name = st.text_input("考生姓名")
        verify_btn = st.form_submit_button("✅ 開始報名")

    if "已驗證" not in st.session_state:
        st.session_state["已驗證"] = False

    if verify_btn:
        match = df4[
            (df4["統測報名序號"] == exam_id.strip()) &
            (df4["考生姓名"] == name.strip()) &
            (df4["身分證統一編號"] == id_number.strip().upper())
        ]
        if match.empty:
            st.error("❌ 查無考生資料，請確認輸入正確")
        else:
            st.session_state["已驗證"] = True
            st.session_state["exam_id"] = exam_id.strip()
            st.session_state["name"] = name.strip()
            st.session_state["id_number"] = id_number.strip().upper()
            st.success("✅ 身份驗證成功，請繼續填寫報名資料")

    if st.session_state["已驗證"]:
        with st.form("apply_form"):
            群別 = st.selectbox("統測報考群別", 群別選項)

            st.markdown("請依序填寫最多 6 組志願校系代碼：")
            志願1 = st.text_input("第1組校系代碼")
            志願2 = st.text_input("第2組校系代碼")
            志願3 = st.text_input("第3組校系代碼")
            志願4 = st.text_input("第4組校系代碼")
            志願5 = st.text_input("第5組校系代碼")
            志願6 = st.text_input("第6組校系代碼")

            if st.form_submit_button("📨 送出報名"):
                有效代碼 = df1["校系代碼"].tolist()
                志願清單 = [志願1, 志願2, 志願3, 志願4, 志願5, 志願6]
                填寫代碼 = [c.strip() for c in 志願清單 if c.strip()]
                錯誤代碼 = [c for c in 填寫代碼 if c not in 有效代碼]

                資料 = 報名表.get_all_values()
                df = pd.DataFrame(資料[1:], columns=資料[0])
                重複 = not df[
                    (df["統測報名序號"] == st.session_state["exam_id"]) &
                    (df["身分證字號"] == st.session_state["id_number"])
                ].empty

                if 錯誤代碼:
                    st.error(f"以下校系代碼無效：{', '.join(錯誤代碼)}")
                elif 重複:
                    st.warning("⚠️ 您已填過表單，請勿重複報名")
                else:
                    now = datetime.datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")
                    row = [st.session_state["exam_id"], st.session_state["name"], st.session_state["id_number"],
                           群別] + 填寫代碼 + [""] * (6 - len(填寫代碼)) + [now]
                    try:
                        報名表.append_row(row)
                        st.success("✅ 報名成功，感謝您的填寫！")
                    except Exception as e:
                        st.error(f"❌ 寫入報名資料失敗：{e}")

with tab2:
    st.subheader("🔍 查詢報名紀錄")
    q1 = st.text_input("請輸入統測報名序號", key="查q1")
    q2 = st.text_input("請輸入身分證字號", key="查q2")

    if st.button("查詢"):
        try:
            所有資料 = 報名表.get_all_values()
            標題, 資料列 = 所有資料[0], 所有資料[1:]
            df查 = pd.DataFrame(資料列, columns=標題)
            結果 = df查[
                (df查["統測報名序號"] == q1) &
                (df查["身分證字號"] == q2.upper())
            ]
            if 結果.empty:
                st.info("查無資料")
            else:
                st.dataframe(結果)
        except Exception as e:
            st.error(f"查詢錯誤：{e}")
