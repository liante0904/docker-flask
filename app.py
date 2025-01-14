from flask import Flask, send_from_directory, render_template, jsonify, request , make_response
from flask_talisman import Talisman
from flask_compress import Compress
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from collections import defaultdict
import os
import json
from model.SQLiteManager import SQLiteManagerSQL
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Flask 앱 초기화
app = Flask(__name__)
Compress(app)

# CSP 설정
csp = {
    'default-src': '\'self\'',
    'style-src': ['\'self\'', '\'unsafe-inline\''],
    'script-src': ['\'self\'', '\'unsafe-inline\''],
}

Talisman(app, content_security_policy=csp, force_https=True)

    
scheduler = BackgroundScheduler()

# 캐시 초기화
cache_recent_reports = {"data": None, "last_modified": None}
cache_grouped_reports = {"data": None, "last_modified": None}

# JSON 파일 저장 디렉토리 생성
static_folder = os.path.join(os.getcwd(), 'static', 'reports')
os.makedirs(static_folder, exist_ok=True)

def save_json_to_file(filename, data):
    """데이터를 JSON 파일로 저장"""
    file_path = os.path.join(static_folder, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        # json.dump(data, f, ensure_ascii=False, indent=4)
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"[JSON 저장 완료] {file_path}")

def update_cache_recent_reports():
    """최근 레포트 캐시 갱신 및 JSON 파일 저장"""
    db = SQLiteManagerSQL()
    last_modified_time = db.fetch_last_modified_time()

    if cache_recent_reports["last_modified"] == last_modified_time:
        print("[최근 레포트] 데이터 변경 없음. 캐시를 사용합니다.")
        db.close_connection()
        return

    print("[최근 레포트] 데이터 변경 감지. 캐시를 갱신합니다.")
    rows = db.fetch_articles_by_todate()
    grouped = defaultdict(lambda: defaultdict(list))

    for row in rows:
        cleaned_row = {
            "title": row.get("ARTICLE_TITLE", "").strip(),
            "link": (row.get("TELEGRAM_URL") or "").strip(),
            "writer": (row.get("WRITER") or "").strip()
        }
        date = row.get("SAVE_TIME", "REG_DT").strip()
        date = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f').strftime('%Y-%m-%d')
        firm = row.get("FIRM_NM", "").strip()
        grouped[date][firm].append(cleaned_row)

    cache_recent_reports["data"] = grouped
    cache_recent_reports["last_modified"] = last_modified_time
    save_json_to_file('recent_reports.json', grouped)  # JSON 파일로 저장
    db.close_connection()

def update_cache_grouped_reports():
    """그룹화된 레포트 캐시 갱신 및 JSON 파일 저장"""
    db = SQLiteManagerSQL()
    last_modified_time = db.fetch_last_modified_time()

    if cache_grouped_reports["last_modified"] == last_modified_time:
        print("[그룹화된 레포트] 데이터 변경 없음. 캐시를 사용합니다.")
        db.close_connection()
        return

    print("[그룹화된 레포트] 데이터 변경 감지. 캐시를 갱신합니다.")
    rows = db.fetch_daily_articles_by_date()
    grouped = defaultdict(lambda: defaultdict(list))

    for row in rows:
        cleaned_row = {
            "title": row.get("ARTICLE_TITLE", "").strip(),
            "link": (row.get("TELEGRAM_URL") or "").strip(),
            "writer": (row.get("WRITER") or "").strip()
        }
        date = row.get("REG_DT", "").strip()
        firm = row.get("FIRM_NM", "").strip()
        grouped[date][firm].append(cleaned_row)

    cache_grouped_reports["data"] = grouped
    cache_grouped_reports["last_modified"] = last_modified_time
    save_json_to_file('grouped_reports.json', grouped)  # JSON 파일로 저장
    db.close_connection()

# 작업 스케줄링
scheduler.add_job(update_cache_recent_reports, 'cron', minute='10,40')
scheduler.add_job(update_cache_grouped_reports, 'cron', minute='10,40')


# 플래그로 스케줄러 시작 여부 확인
scheduler_started = False

def start_scheduler_on_first_request():
    """첫 요청 시 APScheduler 시작"""
    global scheduler_started
    if not scheduler_started:
        scheduler.start()
        scheduler_started = True
        print("APScheduler가 시작되었습니다.")

    update_cache_recent_reports()
    update_cache_grouped_reports()
    
app.before_request(start_scheduler_on_first_request)

update_cache_recent_reports()
update_cache_grouped_reports()

@app.after_request
def add_cache_control_headers(response):
    """
    모든 응답에 캐시 제어 헤더를 추가합니다.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/')
def home():
    if cache_recent_reports["data"] is None:
        update_cache_recent_reports()
    grouped_reports = cache_recent_reports["data"]
    return render_template('index.html', grouped_reports=grouped_reports, subtitle="최근 레포트")

@app.route('/report/daily_group')
def daily_group():
    if cache_grouped_reports["data"] is None:
        update_cache_grouped_reports()
    grouped_reports = cache_grouped_reports["data"]
    return render_template('index.html', grouped_reports=grouped_reports, subtitle="일자별 레포트")

if __name__ == "__main__":
    if os.getenv('FLASK_ENV') == 'development':
        app.run(debug=True)
    else:
        app.run(host="0.0.0.0", port=5000)
