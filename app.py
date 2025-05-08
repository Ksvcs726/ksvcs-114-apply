
# 安裝 Gradio（Colab 初次執行需安裝）
!pip install gradio

import gradio as gr
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# Google Sheets 認證
SCOPE = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
KEY_FILE_NAME = 'ksvcsapplyassistance-f375e46287c8.json'  # 你的金鑰 JSON 檔名
CREDS = Credentials.from_service_account_file(KEY_FILE_NAME, scopes=SCOPE)
CLIENT = gspread.authorize(CREDS)

# 校系代碼資料來源
SOURCE_URL = 'https://docs.google.com/spreadsheets/d/1RrOvJ_UeP5xu2-l-WJwDySn9d786E5P0hsv_XFq9ovg/edit?usp=sharing'
SOURCE_SHEET = CLIENT.open_by_url(SOURCE_URL).worksheet('工作表1')
raw_data = SOURCE_SHEET.get_all_values()
df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
群別選項 = sorted(df['欲報名之群(類)別'].unique())

# 儲存報名資料的 Google Sheet
SAVE_URL = 'https://docs.google.com/spreadsheets/d/1awfvTvLPkyZM3sGL41sflHtO7LgTkva-lkWx-2rUu7k/edit?usp=drive_link'
SAVE_SHEET = CLIENT.open_by_url(SAVE_URL).sheet1

def 報名與儲存(統測報名序號, 姓名, 身分證字號, 選擇群別, 志願1, 志願2, 志願3, 志願4, 志願5, 志願6):
    合法代碼 = df[df['欲報名之群(類)別'] == 選擇群別]['校系代碼'].tolist()
    填寫代碼 = [c.strip() for c in [志願1, 志願2, 志願3, 志願4, 志願5, 志願6] if c.strip()]
    錯誤代碼 = [c for c in 填寫代碼 if c not in 合法代碼]

    if 錯誤代碼:
        return f"❌ 錯誤：以下校系代碼不屬於「{選擇群別}」：{', '.join(錯誤代碼)}"

    # 檢查是否已報名過
    existing = SAVE_SHEET.get_all_values()
    existing_df = pd.DataFrame(existing[1:], columns=existing[0])
    if not existing_df[(existing_df["統測報名序號"] == 統測報名序號) & (existing_df["身分證字號"] == 身分證字號)].empty:
        return "⚠️ 您已報名過，請勿重複提交。"

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [統測報名序號, 姓名, 身分證字號, 選擇群別] + 填寫代碼 + [""] * (6 - len(填寫代碼)) + [now]
    SAVE_SHEET.append_row(row)
    return "✅ 報名成功！已將您的資料儲存。"

def 查詢報名(查序號, 查身分證):
    try:
        data = SAVE_SHEET.get_all_values()
        header, rows = data[0], data[1:]
        df = pd.DataFrame(rows, columns=header)
        result = df[(df["統測報名序號"] == 查序號) & (df["身分證字號"] == 查身分證)]
        if result.empty:
            return pd.DataFrame([["查無資料"] + [""] * (len(header) - 1)], columns=header)
        return result
    except Exception as e:
        return pd.DataFrame([[f"讀取錯誤：{e}"] + [""] * 10], columns=["統測報名序號", "姓名", "身分證字號", "群別", "志願1", "志願2", "志願3", "志願4", "志願5", "志願6", "報名時間"])

# Gradio 介面
with gr.Blocks() as demo:
    gr.Markdown("## 高雄高商114學年度甄選入學第一階段報名系統")

    with gr.Tab("我要報名"):
        統測報名序號 = gr.Textbox(label="統測報名序號")
        姓名 = gr.Textbox(label="姓名")
        身分證字號 = gr.Textbox(label="身分證字號")
        選擇群別 = gr.Dropdown(choices=群別選項, label="欲報名之群(類)別")

        with gr.Row():
            志願1 = gr.Textbox(label="第1組校系代碼")
            志願2 = gr.Textbox(label="第2組校系代碼")
            志願3 = gr.Textbox(label="第3組校系代碼")
        with gr.Row():
            志願4 = gr.Textbox(label="第4組校系代碼")
            志願5 = gr.Textbox(label="第5組校系代碼")
            志願6 = gr.Textbox(label="第6組校系代碼")

        回饋 = gr.Textbox(label="系統訊息", interactive=False)
        送出 = gr.Button("送出報名")
        送出.click(fn=報名與儲存, inputs=[統測報名序號, 姓名, 身分證字號, 選擇群別, 志願1, 志願2, 志願3, 志願4, 志願5, 志願6], outputs=回饋)

    with gr.Tab("查詢報名紀錄"):
        查序號 = gr.Textbox(label="統測報名序號")
        查身分證 = gr.Textbox(label="身分證字號")
        查詢按鈕 = gr.Button("查詢")
        查詢結果 = gr.Dataframe(label="查詢結果")
        查詢按鈕.click(fn=查詢報名, inputs=[查序號, 查身分證], outputs=查詢結果)

demo.launch(share=True)
