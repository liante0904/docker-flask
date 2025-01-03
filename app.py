from flask import Flask, send_from_directory, render_template
from flask_talisman import Talisman
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from collections import defaultdict
import os
import json
from model.SQLiteManagerORM import SQLiteManagerSQL

app = Flask(__name__)

# CSP 설정 (인라인 스타일과 스크립트 허용)
csp = {
    'default-src': '\'self\'',
    'style-src': ['\'self\'', '\'unsafe-inline\''],
    'script-src': ['\'self\'', '\'unsafe-inline\''],
}

Talisman(app, content_security_policy=csp, force_https=True)


# PDF_FOLDER 경로를 현재 디렉토리 기준 상대 경로로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_FOLDER = os.path.join(BASE_DIR, 'pdf')
# PDF 디렉토리가 없으면 생성
if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

    
scheduler = BackgroundScheduler()


# 주기적으로 JSON 파일을 생성하는 함수
def generate_json_file():
    db = SQLiteManagerSQL()
    rows = db.fetch_daily_articles_by_date()
    grouped = group_reports_by_date_and_firm()

    json_file_path = os.path.join(BASE_DIR, 'data.json')
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(grouped, json_file, ensure_ascii=False, indent=4)

    db.close_connection()
    print(f"JSON 파일이 생성되었습니다: {json_file_path}")



json_file_path = os.path.join(BASE_DIR, 'data.json')

# 작업 스케줄링: 매 시간 10분, 40분에 실행
scheduler.add_job(generate_json_file, 'cron', minute='10,40')


# 플래그로 스케줄러 시작 여부 확인
scheduler_started = False

@app.before_request
def start_scheduler_on_first_request():
    """첫 요청 시 APScheduler 시작"""
    global scheduler_started
    if not scheduler_started:
        scheduler.start()
        scheduler_started = True
        print("APScheduler가 시작되었습니다.")

# DB에서 가져온 데이터를 날짜별, 회사별로 그룹화
def group_reports_by_date_and_firm():
    db = SQLiteManagerSQL()
    
    # DB에서 데이터 가져오기
    rows = db.fetch_daily_articles_by_date()
    print(f"DB에서 가져온 데이터: {len(rows)}")
    db.close_connection()
    
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

    # grouped_reports = group_reports_by_date_and_firm()
    
    # JSON 파일을 읽어 데이터 가져오기
    json_file_path = os.path.join(BASE_DIR, 'data.json')
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        grouped_reports = json.load(json_file)
        
    # print(f"그룹화된 레포트: {len(grouped_reports)}")
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


if not os.path.exists(json_file_path):
    generate_json_file()
    
if __name__ == "__main__":
    
    # 환경 변수에 따라 app.run() 설정
    if os.getenv('FLASK_ENV') == 'development':
        app.run(debug=False)
    else:
        # 배포 환경에서는 SSL을 설정하거나 다른 옵션을 사용할 수 있습니다.
        context = ('/app/cert.pem', '/app/privkey.pem')  # 인증서와 키 경로
        app.run(host="0.0.0.0", port=5000, debug=False, ssl_context=context)