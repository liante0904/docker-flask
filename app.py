from flask import Flask, send_from_directory, render_template, jsonify, request 
from flask_talisman import Talisman
from flask_compress import Compress
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from collections import defaultdict
import os
import json
import redis
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

# Redis 클라이언트 설정
redis_client = redis.StrictRedis(host="redis", port=6379, decode_responses=True)

# PDF_FOLDER 경로를 현재 디렉토리 기준 상대 경로로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_FOLDER = os.path.join(BASE_DIR, 'pdf')

scheduler = BackgroundScheduler()

json_file_path = os.path.join(BASE_DIR, 'data.json')

# 캐시 초기화
cache_recent_reports = {
    "data": None,  # 최근 레포트 데이터 캐시
    "last_modified": None  # 최근 레포트 마지막 수정 시간
}

cache_grouped_reports = {
    "data": None,  # 그룹화된 레포트 데이터 캐시
    "last_modified": None  # 그룹화된 레포트 마지막 수정 시간
}

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

def update_cache_recent_reports():
    """최근 레포트 캐시 갱신"""
    db = SQLiteManagerSQL()
    last_modified_time = db.fetch_last_modified_time()  # DB의 마지막 갱신 시간 가져오기

    # 캐시의 마지막 갱신 시간과 비교
    redis_last_modified_time = redis_client.get("recent_reports_last_modified")

    if redis_last_modified_time == str(last_modified_time):
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

    # Redis에 데이터 저장
    redis_client.setex("recent_reports", 60, json.dumps(grouped))  # TTL: 60초
    redis_client.set("recent_reports_last_modified", str(last_modified_time))  # 마지막 갱신 시간 업데이트

    db.close_connection()


def update_cache_grouped_reports():
    """그룹화된 레포트 캐시 갱신"""
    db = SQLiteManagerSQL()
    last_modified_time = db.fetch_last_modified_time()

    redis_last_modified_time = redis_client.get("grouped_reports_last_modified")

    if redis_last_modified_time == str(last_modified_time):
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

    # Redis에 데이터 저장
    redis_client.setex("grouped_reports", 60, json.dumps(grouped))  # TTL: 60초
    redis_client.set("grouped_reports_last_modified", str(last_modified_time))  # 마지막 갱신 시간 업데이트

    db.close_connection()


# 작업 스케줄링: 매 시간 10분, 40분에 실행
scheduler.add_job(update_cache_recent_reports, 'cron', minute='10,40')

# 작업 스케줄링: 매 시간 10분, 40분에 실행
scheduler.add_job(update_cache_grouped_reports, 'cron', minute='10,40')

@app.route('/')
def home():
    """메인 페이지 - 최근 레포트 표시"""
    update_cache_recent_reports()
    cached_data = redis_client.get("recent_reports")

    if cached_data:
        grouped_reports = json.loads(cached_data)
        print("[최근 레포트] Redis 캐시 사용")
    else:
        print("[최근 레포트] Redis 캐시 없음")
        grouped_reports = {}

    return render_template('index.html', grouped_reports=grouped_reports, subtitle="최근 레포트")


@app.route('/report/daily_group')
def daily_group():
    """메인 페이지 - 그룹화된 레포트 표시"""
    update_cache_grouped_reports()
    cached_data = redis_client.get("grouped_reports")

    if cached_data:
        grouped_reports = json.loads(cached_data)
        print("[그룹화된 레포트] Redis 캐시 사용")
    else:
        print("[그룹화된 레포트] Redis 캐시 없음")
        grouped_reports = {}

    return render_template('index.html', grouped_reports=grouped_reports, subtitle="일자별 레포트")

    
if __name__ == "__main__":
    # 환경 변수에 따라 app.run() 설정
    print(os.getenv('FLASK_ENV'))
    if os.getenv('FLASK_ENV') == 'development':
        print("개발 환경에서 실행합니다.")
        app.run(debug=True)  # SSL 없이 실행
    else:
        print("운영 환경에서 실행합니다.")
        app.run(host="0.0.0.0", port=5000)
