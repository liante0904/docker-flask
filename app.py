from flask import Flask, send_from_directory, render_template, jsonify, request 
from flask_talisman import Talisman
from flask_compress import Compress
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from collections import defaultdict
import os
import json
from model.SQLiteManager import SQLiteManagerSQL

app = Flask(__name__)
Compress(app)

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


@app.before_request
def start_scheduler_on_first_request():
    """첫 요청 시 APScheduler 시작"""
    global scheduler_started
    if not scheduler_started:
        scheduler.start()
        scheduler_started = True
        print("APScheduler가 시작되었습니다.")

# 캐시 초기화
cache_recent_reports = {
    "data": None,  # 최근 레포트 데이터 캐시
    "last_modified": None  # 최근 레포트 마지막 수정 시간
}

cache_grouped_reports = {
    "data": None,  # 그룹화된 레포트 데이터 캐시
    "last_modified": None  # 그룹화된 레포트 마지막 수정 시간
}


def update_cache_recent_reports():
    """최근 레포트 캐시 갱신"""
    db = SQLiteManagerSQL()
    last_modified_time = db.fetch_last_modified_time()  # DB의 마지막 갱신 시간 가져오기

    # 캐시의 마지막 갱신 시간과 비교
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
    db.close_connection()


def update_cache_grouped_reports():
    """그룹화된 레포트 캐시 갱신"""
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
    db.close_connection()

# 작업 스케줄링: 매 시간 10분, 40분에 실행
scheduler.add_job(update_cache_recent_reports, 'cron', minute='10,40')


# 플래그로 스케줄러 시작 여부 확인
scheduler_started = False


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
            "writer": (row.get("WRITER") or "").strip()
        }
        date = row.get("REG_DT", "").strip()
        firm = row.get("FIRM_NM", "").strip()
        grouped[date][firm].append(cleaned_row)
    
    return grouped

# DB에서 가져온 데이터를 날짜별, 회사별로 그룹화
def recent_reports_by_today():
    db = SQLiteManagerSQL()
    
    # DB에서 데이터 가져오기
    rows = db.fetch_articles_by_todate()
    print(f"DB에서 가져온 데이터: {len(rows)}")
    db.close_connection()
    
    grouped = defaultdict(lambda: defaultdict(list))
    
    # DB에서 가져온 데이터를 그룹화
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
    
    return grouped



    # JSON 파일을 읽어 데이터 가져오기
    # json_file_path = os.path.join(BASE_DIR, 'data.json')
    # with open(json_file_path, 'r', encoding='utf-8') as json_file:
    #     grouped_reports = json.load(json_file)
    
    
@app.route('/')
def home():
    """메인 페이지 - 최근 레포트 표시"""
    update_cache_recent_reports()
    grouped_reports = cache_recent_reports["data"]
    return render_template('index.html', grouped_reports=grouped_reports, subtitle="최근 레포트")


@app.route('/report/daily_group')
def daily_group():
    """메인 페이지 - 그룹화된 레포트 표시"""
    update_cache_grouped_reports()
    grouped_reports = cache_grouped_reports["data"]
    return render_template('index.html', grouped_reports=grouped_reports, subtitle="일자별 레포트")


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

# if not os.path.exists(json_file_path):
#     generate_json_file()
    
if __name__ == "__main__":
    # 환경 변수에 따라 app.run() 설정
    if os.getenv('FLASK_ENV') == 'development':
        app.run(debug=True)  # SSL 없이 실행
    else:
        app.run(host="0.0.0.0", port=5000)