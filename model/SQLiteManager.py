import sqlite3
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

SQLITE_PATH = os.getenv('SQLITE_PATH')
db_path = os.path.expanduser(SQLITE_PATH)

class SQLiteManagerSQL:
    def __init__(self):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def close_connection(self):
        self.conn.close()

    def fetch_last_modified_time(self):
        """SAVE_TIME 컬럼에서 가장 최근 시간을 반환"""
        query = "SELECT MAX(SAVE_TIME) FROM data_main_daily_send"
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        if result and result[0]:
            # ISO 형식의 문자열을 Python datetime 객체로 변환
            return datetime.fromisoformat(result[0])
        return None

    def fetch_daily_articles_by_date(self, firm_info=None, date_str=None):
        """Fetch articles by date."""
        query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
        three_days_ago = (datetime.strptime(query_date, '%Y%m%d') - timedelta(days=3)).strftime('%Y%m%d')
        two_days_after = (datetime.strptime(query_date, '%Y%m%d') + timedelta(days=2)).strftime('%Y%m%d')

        query = """
            SELECT * FROM data_main_daily_send
            WHERE REG_DT BETWEEN ? AND ?
        """
        params = [three_days_ago, two_days_after]

        if firm_info:
            query += " AND SEC_FIRM_ORDER = ?"
            params.append(firm_info['SEC_FIRM_ORDER'])

        query += " ORDER BY REG_DT DESC, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME"
        self.cursor.execute(query, params)

        results = self.cursor.fetchall()
        return [dict(zip([column[0] for column in self.cursor.description], row)) for row in results]

    def fetch_articles_by_todate(self, firm_info=None, date_str=None):
        """Fetch articles by date."""
        query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
        three_days_ago = (datetime.strptime(query_date, '%Y%m%d') - timedelta(days=3)).strftime('%Y%m%d')
        two_days_after = (datetime.strptime(query_date, '%Y%m%d') + timedelta(days=2)).strftime('%Y%m%d')

        query = """
            SELECT * FROM data_main_daily_send
            WHERE REG_DT BETWEEN ? AND ? 
        """
        params = [three_days_ago, two_days_after]

        if firm_info:
            query += " AND SEC_FIRM_ORDER = ?"
            params.append(firm_info['SEC_FIRM_ORDER'])

        query += " ORDER BY SAVE_TIME DESC , REG_DT DESC"
        self.cursor.execute(query, params)

        results = self.cursor.fetchall()
        return [dict(zip([column[0] for column in self.cursor.description], row)) for row in results]


class SQLiteManagerInMemory:
    """메모리 기반 SQLite 관리 클래스"""
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()

    def initialize_schema(self, schema_sql):
        self.cursor.executescript(schema_sql)
        self.conn.commit()

    def insert_records(self, records):
        query = """
            INSERT INTO data_main_daily_send (
                SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT, ATTACH_URL,
                ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, DOWNLOAD_URL,
                WRITER, SAVE_TIME, TELEGRAM_URL, KEY
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.cursor.executemany(query, records)
        self.conn.commit()

    def fetch_all(self):
        self.cursor.execute("SELECT * FROM data_main_daily_send")
        results = self.cursor.fetchall()
        return [dict(zip([column[0] for column in self.cursor.description], row)) for row in results]

    def close_connection(self):
        self.conn.close()


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

# Example Usage
if __name__ == "__main__":
    # 디스크 기반 SQLite 초기화
    disk_manager = SQLiteManagerSQL()

    # 메모리 기반 SQLite 초기화
    memory_manager = SQLiteManagerInMemory()

    # 디스크에서 메모리로 동기화
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

        # fetch 데이터를 활용해 메모리 DB 갱신
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

    # 데이터 동기화 실행
    sync_to_memory(disk_manager, memory_manager)

    # 메모리 DB 데이터 확인
    print("메모리 DB 데이터:")
    for row in memory_manager.fetch_all():
        print(row)

    # 연결 종료
    disk_manager.close_connection()
    memory_manager.close_connection()
