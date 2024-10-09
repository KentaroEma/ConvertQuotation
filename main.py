import streamlit as st
import pdfplumber
from PIL import Image
import pytesseract
import re
from datetime import datetime
import base64

# Tesseractのパスを設定
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # 環境に合わせて設定

# 元号から西暦に変換する関数
def convert_japanese_era_to_ad(era, year):
    eras = {
        '令和': 2019,
        '平成': 1989,
        '昭和': 1926,
        '大正': 1912,
        '明治': 1868
    }
    if era in eras:
        return eras[era] + year - 1  # 元年は1年引く
    return None

# OCRで画像からテキストを抽出する関数
def extract_text_from_image(image):
    text = pytesseract.image_to_string(image, lang='jpn')
    return text

# PDFからテキストを抽出する関数
def extract_text_from_pdf(pdf):
    text = ''
    with pdfplumber.open(pdf) as pdf_file:
        for page in pdf_file.pages:
            text += page.extract_text()
    return text

# 元号も含めて日付を抽出して西暦に変換する関数
def extract_and_convert_date(text):
    # 西暦日付フォーマット (例: 2024年10月9日、2024/10/09、2024-10-09)
    date_match = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})[日]?', text)
    if date_match:
        year, month, day = date_match.groups()
        return f'{year[-2:]}{month.zfill(2)}{day.zfill(2)}'
    
    # 元号日付フォーマット (例: 令和2年10月9日、平成30年10月9日)
    era_date_match = re.search(r'(令和|平成|昭和|大正|明治)(\d{1,2})年(\d{1,2})月(\d{1,2})日', text)
    if era_date_match:
        era, year, month, day = era_date_match.groups()
        year = int(year)
        month = int(month)
        day = int(day)
        ad_year = convert_japanese_era_to_ad(era, year)
        if ad_year:
            return f'{str(ad_year)[-2:]}{str(month).zfill(2)}{str(day).zfill(2)}'
    
    return ''

# 種類、会社名、発行日、合計金額を抽出する関数
def extract_info(text):
    doc_type = ''
    company_name = ''
    issue_date_formatted = ''  # デフォルトで空文字列をセット
    total_amount = ''

    # 文書の種類を判定 (見積書、納品書、請求書にスペース対応)
    if re.search(r'見\s*積\s*書', text):
        doc_type = '見積書'
    elif re.search(r'納\s*品\s*書', text):
        doc_type = '納品書'
    elif re.search(r'請\s*求\s*書', text):
        doc_type = '請求書'

    # 発行日を抽出
    issue_date_formatted = extract_and_convert_date(text)

    # 合計金額を抽出（例: 100,000円）
    total_match = re.search(r'合計金額.*?(\d{1,3}(,\d{3})*)円', text)
    if total_match:
        total_amount = total_match.group(1)

    # 会社名を抽出（「株式会社〇〇」「〇〇株式会社」「(株)〇〇」などに対応）
    company_matches = re.findall(r'(.*?)(株式会社|[(]株[)]|法人)', text)
    
    # 自分の会社名を省略
    my_company_name = "ノベルクリスタルテクノロジー"
    
    # 自分の会社名以外の会社名を選ぶ
    for match in company_matches:
        # matchが文字列かを確認してから処理する
        if match and isinstance(match[0], str):
            if my_company_name not in match[0]:
                # 「株式会社」「(株)」を取り除く
                company_name = re.sub(r'(株式会社|[(]株[)]|法人)', '', match[0]).strip()
                break
    else:
        company_name = "会社名が認識できませんでした。"  # 会社名が見つからない場合

    return doc_type, company_name, issue_date_formatted, total_amount

# PDFをサイドバーにアップロードする関数
def upload_pdf_file():
    uploaded_file = st.sidebar.file_uploader("Upload PDF file", type="pdf")
    if uploaded_file is None:
        st.sidebar.write("Please upload a PDF file.")
    return uploaded_file

# PDFファイルを画面に表示する関数
def display_pdf(uploaded_file):
    if uploaded_file is not None:
        pdf_contents = uploaded_file.read()
        pdf_base64 = base64.b64encode(pdf_contents).decode('utf-8')

        # PDFを埋め込むためのHTMLタグ
        encoded_pdf = f'<embed id="pdf_viewer" src="data:application/pdf;base64,{pdf_base64}" width="100%" height="600px" type="application/pdf">'

        # PDFの埋め込みを表示
        st.markdown(encoded_pdf, unsafe_allow_html=True)
    else:
        st.write("No PDF file uploaded.")

# main関数
def main():
    # CSSを使って全画面表示にする
    st.markdown(
        """
        <style>
        .css-18e3th9 {padding: 0;}   /* ヘッダーのパディングをゼロに */
        .css-1d391kg {padding: 0;}   /* ページのパディングをゼロに */
        .main .block-container {padding: 0;margin: 0;width: 100vw;height: 100vh;max-width: 100vw;}  /* メインコンテナの幅と高さを100%に */
        iframe {position: absolute; top: 0; left: 0; width: 100vw; height: 100vh; border: none;} /* iframeを全画面表示 */
        </style>
        """,
        unsafe_allow_html=True
    )

    # サイドバーにアップロードのUIを設置
    file = upload_pdf_file()

    # PDFのプレビューをメイン画面に表示
    if file is not None:
        display_pdf(file)

        # サイドバーにOCRとファイル保存の機能を追加
        with st.sidebar:
            st.write("OCRとファイル名の変更")

            # OCR結果を保持するためのセッション変数
            if 'ocr_result' not in st.session_state:
                st.session_state.ocr_result = None
                st.session_state.doc_type = ''
                st.session_state.company_name = ''
                st.session_state.issue_date = ''
                st.session_state.new_file_name = None

            # OCR実行ボタン
            if st.button("OCRを実行"):
                # PDFからテキスト抽出
                extracted_text = extract_text_from_pdf(file)
                st.session_state.ocr_result = extracted_text

                # 情報抽出
                doc_type, company_name, issue_date, total_amount = extract_info(st.session_state.ocr_result)

                # 抽出結果をセッションに保存
                st.session_state.doc_type = doc_type
                st.session_state.company_name = company_name
                st.session_state.issue_date = issue_date

            # 抽出結果をエクスパンダーで表示（通常は非表示）
            with st.expander("抽出されたテキストを表示"):
                st.write(st.session_state.ocr_result)

            # プルダウンメニューで種類を選択（手入力も可能）
            doc_type_options = ['見積書', '納品書', '請求書']
            st.session_state.doc_type = st.selectbox(
                "種類 (見積書/納品書/請求書)", doc_type_options, index=doc_type_options.index(st.session_state.doc_type) if st.session_state.doc_type in doc_type_options else 0
            )
            # with st.expander("種類を手入力（オプション）"):
            #     st.session_state.doc_type = st.text_input(selected_doc_type)

            # 会社名と発行日
            st.session_state.company_name = st.text_input("会社名", st.session_state.company_name)
            st.session_state.issue_date = st.text_input("発行日 (YYMMDD形式)", st.session_state.issue_date)

            # ユーザーが修正したファイル名を生成
            if st.session_state.doc_type or st.session_state.company_name or st.session_state.issue_date:
                st.session_state.new_file_name = f"{st.session_state.doc_type}_{st.session_state.company_name}_{st.session_state.issue_date}.pdf"
                st.write(f"新しいファイル名: \n{st.session_state.new_file_name}")

            # PDFをダウンロードボタン
            if st.session_state.new_file_name:
                # 新しいファイル名を指定してPDFをダウンロード
                st.download_button(
                    label="新しいファイル名でダウンロード",
                    data=file.getvalue(),
                    file_name=st.session_state.new_file_name,
                    mime="application/pdf"
                )

main()
