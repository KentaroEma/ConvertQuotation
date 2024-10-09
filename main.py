import streamlit as st
import pdfplumber
from PIL import Image
import pytesseract
import re
from datetime import datetime

# Tesseractのパスを設定
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # 環境に合わせて設定

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

# 種類、会社名、発行日、合計金額を抽出する関数
def extract_info(text):
    doc_type = ''
    company_name = ''
    issue_date = ''
    total_amount = ''

    # 文書の種類を判定
    if '見積書' in text:
        doc_type = '見積書'
    elif '納品書' in text:
        doc_type = '納品書'
    elif '請求書' in text:
        doc_type = '請求書'

    # 発行日を抽出（例: 2023年10月01日）
    date_match = re.search(r'(\d{4})年(\d{2})月(\d{2})日', text)
    if date_match:
        issue_date = date_match.group(0)
        issue_date_formatted = datetime.strptime(issue_date, '%Y年%m月%d日').strftime('%y%m%d')

    # 合計金額を抽出（例: 100,000円）
    total_match = re.search(r'合計金額.*?(\d{1,3}(,\d{3})*)円', text)
    if total_match:
        total_amount = total_match.group(1)

    # 会社名を抽出（仮定：会社名が「株式会社」で終わる）
    company_match = re.search(r'[\w\d\s]+株式会社', text)
    if company_match:
        company_name = company_match.group(0)

    # 自分の会社名を省略
    my_company_name = "自分の会社名"
    if my_company_name in company_name:
        company_name = "他社"

    return doc_type, company_name, issue_date_formatted, total_amount

# main関数
def main():
    st.title('PDFプレビュー')

    # サイドバーに配置する要素
    with st.sidebar:
        st.header('操作メニュー')

        # PDFファイルのアップロード
        uploaded_pdf = st.file_uploader("PDFファイルをアップロード", type="pdf")

        # OCR結果を保持するためのセッション変数
        if 'ocr_result' not in st.session_state:
            st.session_state.ocr_result = None
            st.session_state.new_file_name = None

        if uploaded_pdf is not None:
            # PDFダウンロード
            st.download_button(label="ダウンロード PDF", data=uploaded_pdf, file_name="preview.pdf")

            # OCR実行ボタン
            if st.button("OCRを実行"):
                # PDFからテキスト抽出
                extracted_text = extract_text_from_pdf(uploaded_pdf)
                st.session_state.ocr_result = extracted_text
                st.write("抽出されたテキスト:")
                st.write(st.session_state.ocr_result)

                # 情報抽出
                doc_type, company_name, issue_date, total_amount = extract_info(st.session_state.ocr_result)
                
                if doc_type and company_name and issue_date:
                    st.session_state.new_file_name = f"{doc_type}_{company_name}_{issue_date}.pdf"
                    st.write(f"新しいファイル名: {st.session_state.new_file_name}")
                else:
                    st.error("必要な情報が見つかりませんでした。")

            # ファイル保存ボタン
            if st.session_state.new_file_name and st.button("ファイルを保存"):
                # ファイル保存
                with open(st.session_state.new_file_name, "wb") as f:
                    f.write(uploaded_pdf.getvalue())
                st.success(f"ファイルが {st.session_state.new_file_name} として保存されました。")

    # メイン画面にPDFプレビューを表示
    if uploaded_pdf is not None:
        st.write("PDFファイルのプレビュー:")
        st.download_button(label="ダウンロード PDF", data=uploaded_pdf, file_name="preview.pdf")

if __name__ == '__main__':
    main()
