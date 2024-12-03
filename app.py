from flask import Flask, send_from_directory
import os

app = Flask(__name__)

# $HOME/pdf 경로 설정
PDF_FOLDER = os.environ.get("PDF_FOLDER", "/app/pdf")  # 기본 경로는 컨테이너 내 /app/pdf

@app.route('/pdf/<path:filename>')
def serve_pdf(filename):
    """
    PDF 파일을 지정된 폴더에서 호스팅
    """
    return send_from_directory(PDF_FOLDER, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
