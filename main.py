import streamlit as st
from dotenv import load_dotenv
import pdfplumber
import fitz  # PyMuPDF
import re
import os
import pandas as pd
from datetime import datetime
from io import BytesIO

# ページのレイアウト設定
st.set_page_config(
    page_title="Convert Quotaion PDF",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header."
    }
)

# .env ファイルを読み込む
load_dotenv()

# APIキーを環境変数から取得
my_company_name = os.getenv("MY_COMPANY_NAME")

# 文書の種類
doc_types = ['見積書', '納品書', '請求書']

# 処理済みファイルのリスト
if 'processed_files' not in st.session_state:
    st.session_state['processed_files'] = []

# 処理済みファイルをDataFrame形式で管理
def update_processed_files(original_name, new_name):
    # 既存の処理済みファイルリストに追加
    st.session_state['processed_files'].append({
        '元のファイル名': original_name,
        '新しいファイル名': new_name
    })

    # DataFrame形式で表示する
    df = pd.DataFrame(st.session_state['processed_files'])
    return df

# 元号から西暦に変換する関数
def convert_japanese_era_to_ad(era, year):
    eras = {
        '令和': 2019,
        '平成': 1989,
        '昭和': 1926,
        '大正': 1912,
        '明治': 1868
    }
    return eras.get(era, None) + year - 1 if era in eras else None

# テキストからPDFを抽出する関数
def extract_text_from_pdf(pdf):
    with pdfplumber.open(pdf) as pdf_file:
        return ''.join([page.extract_text() for page in pdf_file.pages])

# PDFを画像に変換して表示する関数
def display_pdf_as_images(pdf):
    doc = fitz.open(stream=pdf.read(), filetype="pdf")
    page_images = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 解像度を上げるためにスケールを設定
        img_data = BytesIO(pix.tobytes("png"))
        page_images.append(img_data)

    for i, img in enumerate(page_images):
        st.image(img, caption=f"Page {i+1}")

# 日付を抽出して西暦に変換する関数
def extract_and_convert_date(text):
    date_match = re.search(r'(\d{4})[年/](\d{1,2})[月/](\d{1,2})[日]?', text)
    if date_match:
        return f'{date_match.group(1)[-2:]}{date_match.group(2).zfill(2)}{date_match.group(3).zfill(2)}'
    
    era_date_match = re.search(r'(令和|平成|昭和|大正|明治)(\d{1,2})年(\d{1,2})月(\d{1,2})日', text)
    if era_date_match:
        ad_year = convert_japanese_era_to_ad(era_date_match.group(1), int(era_date_match.group(2)))
        return f'{str(ad_year)[-2:]}{era_date_match.group(3).zfill(2)}{era_date_match.group(4).zfill(2)}' if ad_year else ''
    
    return ''

# 種類、会社名、発行日、合計金額を抽出する関数
def extract_info(text, my_company_name):
    doc_type = next((dt for dt in doc_types if re.search(f'{dt[:1]}\s*{dt[1]}', text)), '')

    # 会社名を探し、自分の会社名をスキップ
    company_matches_1 = re.findall(r'(.*?)(株式会社|[(]株[)]|合同会社|合資会社|合名会社|法人)', text)
    company_matches_2 = re.findall(r'(株式会社|[(]株[)]|合同会社|合資会社|合名会社|法人)\s*(\S+)', text)

    company_name = ""
    for match in company_matches_1:
        company = re.sub(r'(株式会社|[(]株[)]|合同会社|合資会社|合名会社|法人)', '', match[0]).strip()
        if my_company_name != company:
            company_name = company
            break
    for match in company_matches_2:
        company = re.sub(r'(株式会社|[(]株[)]|合同会社|合資会社|合名会社|法人)', '', match[1]).strip()
        if my_company_name != company:
            company_name = company
            break
    if company_name == "":
        company_name = "会社名が認識できませんでした。"  # 会社名が見つからない場合
    
    issue_date = extract_and_convert_date(text)
    total_amount_match = re.search(r'合計.*?(\d{1,3}(,\d{3})*)円', text)
    total_amount = total_amount_match.group(1) if total_amount_match else ''
    
    return doc_type, company_name, issue_date, total_amount

# セッション状態の初期化
def reset_session_state():
    today = datetime.now().strftime("%y%m%d")  # 今日の日付を YYMMDD 形式で取得
    for key in ['ocr_result', 'doc_type', 'company_name', 'total_amount', 'new_file_name', 'current_file_index']:
        st.session_state[key] = None if key == 'ocr_result' else ''
    st.session_state['issue_date'] = today  # 発行日の初期値に今日の日付を設定
    st.session_state['current_file_index'] = 0  # ファイルインデックスの初期化

# メインのPDFアップロード、OCR処理を行う関数
def process_pdf(file, my_company_name):
    if file:
        display_pdf_as_images(file)
        if st.sidebar.button("テキスト抽出", key=f"extract_text_button_{st.session_state['current_file_index']}"):
            st.session_state.ocr_result = extract_text_from_pdf(file)
            doc_type, company_name, issue_date, total_amount = extract_info(st.session_state.ocr_result, my_company_name)
            st.session_state.update({'doc_type': doc_type, 'company_name': company_name, 'issue_date': issue_date, 'total_amount': total_amount})

# ファイル名生成、ダウンロード、リセットを行う関数
def handle_actions(file):
    # 手入力された内容でファイル名を生成
    st.session_state.new_file_name = f"{st.session_state.doc_type}_{st.session_state.company_name}_{st.session_state.issue_date}.pdf"
    
    # ファイル名とダウンロードボタンを表示
    if st.download_button(
        label="新しいファイル名でダウンロード",
        data=file.getvalue(),
        file_name=st.session_state.new_file_name,
        mime="application/pdf"
        ):
        # ダウンロードが実行されたら処理済みファイルリストに追加
        update_processed_files(file.name, st.session_state.new_file_name)

# メイン関数
def main():
    st.title("見積書/納品書/請求書のファイル名変換ツール")
    st.write("PDFファイルをアップロードして、ファイル名を変換してダウンロードできます。")
    st.sidebar.header("ナビゲーションウィンドウ")
    files = st.sidebar.file_uploader("PDFファイルをアップロード", type="pdf", accept_multiple_files=True)

    if files:
        if 'current_file_index' not in st.session_state:
            reset_session_state()

        current_file_index = st.session_state['current_file_index']

        if current_file_index < len(files):
            file = files[current_file_index]

            # ページを2つの列に分ける
            col1, col2 = st.columns([1, 1])

            # 左列にPDFを表示
            with col1:
                st.subheader("PDFファイルのプレビュー")
                
                # 初期化処理
                if 'ocr_result' not in st.session_state or st.session_state['ocr_result'] is None:
                    reset_session_state()

                process_pdf(file, my_company_name)

                with st.sidebar:
                    # PDFから抽出したテキストをエクスパンダーで表示
                    if st.session_state.ocr_result:
                        with st.expander("抽出されたテキストを表示"):
                            st.write(st.session_state.ocr_result)

                    # プルダウン形式で種類を選択
                    doc_type_options = ['見積書', '納品書', '請求書', 'その他']
                    selected_doc_type = st.selectbox(
                        "種類を選択", 
                        doc_type_options, 
                        index=doc_type_options.index(st.session_state.doc_type) if st.session_state.doc_type in doc_type_options else 0
                    )
                    st.session_state.doc_type = st.text_input("種類を手入力(オプション)", selected_doc_type)

                    # 会社名と発行日
                    st.session_state.company_name = st.text_input("取引先", st.session_state.company_name, key="company_name_input")
                    st.session_state.issue_date = st.text_input("発行日(YYMMDD形式)", st.session_state.issue_date, key="issue_date_input")

                    handle_actions(file)

                    side_col1, side_col2 = st.columns([1, 1])
                    with side_col2:
                    # 次のファイルへ進むボタン
                        if st.button("次のファイルへ", key="next_file_button"):
                            st.session_state['current_file_index'] += 1
                            st.experimental_rerun()  # 強制的に再描画して次のファイルへ進む
                    with side_col1:
                        if st.button("前のファイルへ", key="previous_file_button"):
                            st.session_state['current_file_index'] -= 1
                            reset_session_state()

            # 右列に処理済みファイルのリストを表示
            with col2:
                st.subheader("処理済みファイル一覧")
                if len(st.session_state['processed_files']) > 0:
                    df = pd.DataFrame(st.session_state['processed_files'])
                    st.dataframe(df)

    # リセットボタン
    if st.sidebar.button("入力内容クリア", key="reset_button"):
        reset_session_state()

main()
