from flask import Flask, render_template
from flask_compress import Compress
from flask_talisman import Talisman
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from collections import defaultdict
import os
import json
from model.SQLiteManager import SQLiteManagerSQL, SQLiteManagerInMemory
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Flask 앱 초기화
app = Flask(__name__)
Compress(app)

# CSP 설정 (인라인 스타일과 스크립트 허용)
csp = {
    'default-src': '\'self\'',
    'style-src': ['\'self\'', '\'unsafe-inline\''],
    'script-src': ['\'self\'', '\'unsafe-inline\''],
}
Talisman(app, content_security_policy=csp, force_https=True)

# # PDF 디렉토리 설정
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# PDF_FOLDER = os.path.join(BASE_DIR, 'pdf')
# if not os.path.exists(PDF_FOLDER):
#     os.makedirs(PDF_FOLDER)

# 스케줄러 초기화
scheduler = BackgroundScheduler()
scheduler_started = False

# 메모리 DB와 파일 DB를 동기화할 메서드
def sync_to_memory(disk_manager, memory_manager):
    """디스크 DB 데이터를 메모리 DB로 동기화"""
    schema_query = """
        CREATE TABLE IF NOT EXISTS data_main_daily_send (
            SEC_FIRM_ORDER INTEGER,
            ARTICLE_BOARD_ORDER INTEGER,
            FIRM_NM TEXT,
            REG_DT TEXT,
            ATTACH_URL TEXT,
            ARTICLE_TITLE TEXT,
            ARTICLE_URL TEXT,
            MAIN_CH_SEND_YN TEXT,
            DOWNLOAD_URL TEXT,
            WRITER TEXT,
            SAVE_TIME TEXT,
            TELEGRAM_URL TEXT,
            KEY TEXT PRIMARY KEY
        )
    """
    memory_manager.initialize_schema(schema_query)

    # 디스크 DB에서 데이터 가져오기
    records = disk_manager.fetch_daily_articles_by_date()
    if records:
        formatted_records = [
            (
                record['SEC_FIRM_ORDER'], record['ARTICLE_BOARD_ORDER'], record['FIRM_NM'], record['REG_DT'],
                record['ATTACH_URL'], record['ARTICLE_TITLE'], record['ARTICLE_URL'], record['MAIN_CH_SEND_YN'],
                record['DOWNLOAD_URL'], record['WRITER'], record['SAVE_TIME'], record['TELEGRAM_URL'], record['KEY']
            ) for record in records
        ]
        memory_manager.insert_records(formatted_records)

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
scheduler.add_job(update_cache_grouped_reports, 'cron', minute='10,40')

# 메모리 DB와 파일 DB 동기화
def sync_memory_on_start():
    """앱이 시작될 때 메모리 DB와 파일 DB를 동기화"""
    disk_manager = SQLiteManagerSQL()
    memory_manager = SQLiteManagerInMemory()
    sync_to_memory(disk_manager, memory_manager)
    print("메모리 DB와 파일 DB 동기화 완료.")
    return disk_manager, memory_manager

# 플래그로 스케줄러 시작 여부 확인
scheduler_started = False

def start_scheduler_on_first_request():
    """첫 요청 시 APScheduler 시작"""
    global scheduler_started
    if not scheduler_started:
        scheduler.start()
        scheduler_started = True
        print("APScheduler가 시작되었습니다.")

    # 메모리 DB 동기화
    global disk_manager, memory_manager
    disk_manager, memory_manager = sync_memory_on_start()

app.before_request(start_scheduler_on_first_request)

# 메모리 DB와 파일 DB를 동기화하는 API
@app.route('/')
def home():
    """메인 페이지 - 최근 레포트 표시"""
    if cache_recent_reports["data"] is None:
        update_cache_recent_reports()
    # update_cache_recent_reports()
    grouped_reports = cache_recent_reports["data"]
    return render_template('index.html', grouped_reports=grouped_reports, subtitle="최근 레포트")


@app.route('/report/daily_group')
def daily_group():
    """메인 페이지 - 그룹화된 레포트 표시"""
    if cache_grouped_reports["data"] is None:
        update_cache_grouped_reports()
    # update_cache_grouped_reports()
    grouped_reports = cache_grouped_reports["data"]
    return render_template('index.html', grouped_reports=grouped_reports, subtitle="일자별 레포트")


if __name__ == "__main__":
    # 환경 변수에 따라 app.run() 설정
    if os.getenv('FLASK_ENV') == 'development':
        app.run(debug=True)  # SSL 없이 실행
    else:
        app.run(host="0.0.0.0", port=5000)