from flask import Flask, request, send_from_directory, render_template, redirect
from collections import defaultdict
import os
from model.SQLiteManagerORM import SQLiteManagerORM

app = Flask(__name__)

# PDF_FOLDER 경로를 현재 디렉토리 기준 상대 경로로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_FOLDER = os.path.join(BASE_DIR, 'pdf')
# PDF 디렉토리가 없으면 생성
if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)


@app.before_request
def before_request():
    """HTTP 요청이 오면 HTTPS로 리다이렉트"""
    if request.headers.get('X-Forwarded-Proto') == 'http':
        return redirect(request.url.replace("http://", "https://"), code=301)

def group_reports_by_date_and_firm():
    db = SQLiteManagerORM()
    
    # DB에서 데이터 가져오기
    rows = db.fetch_daily_articles_by_date()
    print(f"DB에서 가져온 데이터: {rows}")
    db.close_session()
    
    grouped = defaultdict(lambda: defaultdict(list))
    
    # DB에서 가져온 데이터를 그룹화
    for row in rows:
        cleaned_row = {
            "title": row.get("ARTICLE_TITLE", "").strip(),
            "link": (row.get("TELEGRAM_URL") or "").strip(),
            "writer": (row.get("WRITER") or "").strip(),
            "key": row.get("KEY", "").strip()
        }
        date = row.get("REG_DT", "").strip()
        firm = row.get("FIRM_NM", "").strip()
        grouped[date][firm].append(cleaned_row)
    
    return grouped

@app.route('/')
def home():
    """메인 페이지 - 레포트 목록 표시"""
    print(f"PDF_FOLDER: {PDF_FOLDER}")
    grouped_reports = group_reports_by_date_and_firm()
    print(f"그룹화된 레포트: {grouped_reports}")
    return render_template('index.html', grouped_reports=grouped_reports)

@app.route('/pdf/<path:filename>')
def serve_pdf(filename):
    """PDF 파일 서빙"""
    try:
        print(f"요청된 파일: {filename}")
        print(f"PDF 폴더 경로: {PDF_FOLDER}")
        print(f"전체 파일 경로: {os.path.join(PDF_FOLDER, filename)}")
        return send_from_directory(PDF_FOLDER, filename)
    except Exception as e:
        print(f"에러 발생: {str(e)}")
        return f"파일을 찾을 수 없습니다: {filename}", 404

if __name__ == "__main__":
    
    # 환경 변수에 따라 app.run() 설정
    if os.getenv('FLASK_ENV') == 'development':
        app.run(debug=True)
    else:
        # 배포 환경에서는 SSL을 설정하거나 다른 옵션을 사용할 수 있습니다.
        context = ('/app/cert.pem', '/app/privkey.pem')  # 인증서와 키 경로
        app.run(host="0.0.0.0", port=5000, debug=True, ssl_context=context)