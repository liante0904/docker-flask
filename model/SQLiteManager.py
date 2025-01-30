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

    def search_reports_by_keyword(self, keyword, offset=0, limit=30):
        """
        키워드로 레포트를 검색하고 페이징 처리합니다.
        :param keyword: 검색 키워드
        :param offset: 페이징 offset
        :param limit: 페이징 limit
        :return: 검색 결과 리스트 (각 결과는 딕셔너리 형태)
        """
        query = """
            SELECT id, ARTICLE_TITLE, TELEGRAM_URL, WRITER, SAVE_TIME, FIRM_NM
            FROM data_main_daily_send
            WHERE ARTICLE_TITLE LIKE ? OR WRITER LIKE ? 
            ORDER BY SAVE_TIME DESC
            LIMIT ? OFFSET ?
        """
        keyword_pattern = f"%{keyword}%"
        params = (keyword_pattern, keyword_pattern, limit, offset)

        self.cursor.execute(query, params)

        # 결과를 딕셔너리 리스트 형태로 반환
        results = self.cursor.fetchall()
        return [dict(zip([column[0] for column in self.cursor.description], row)) for row in results]

    def fetch_global_articles_by_todate(self, firm_info=None, date_str=None):
        """Fetch articles by date."""
        query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
        three_days_ago = (datetime.strptime(query_date, '%Y%m%d') - timedelta(days=14)).strftime('%Y%m%d')
        two_days_after = (datetime.strptime(query_date, '%Y%m%d') + timedelta(days=2)).strftime('%Y%m%d')

        query = """
            SELECT * FROM data_main_daily_send
                WHERE   MAIN_CH_SEND_YN = 'Y'
                        AND (SEC_FIRM_ORDER = 1 and ARTICLE_BOARD_ORDER = 3 
                        or SEC_FIRM_ORDER = 5 and ARTICLE_BOARD_ORDER = 2 
                        or SEC_FIRM_ORDER = 9 and ARTICLE_BOARD_ORDER = 2 
                        or SEC_FIRM_ORDER = 10 and ARTICLE_BOARD_ORDER = 3 
                        or SEC_FIRM_ORDER = 12 and ARTICLE_BOARD_ORDER = 3 
                        or SEC_FIRM_ORDER = 18 and ARTICLE_BOARD_ORDER = 2
                        or SEC_FIRM_ORDER = 25 and ARTICLE_BOARD_ORDER = 4
                        or ARTICLE_TITLE LIKE "%.US%"
                        )
                        
                        AND REG_DT BETWEEN ? AND ? 
        """
        params = [three_days_ago, two_days_after]

        if firm_info:
            query += " AND SEC_FIRM_ORDER = ?"
            params.append(firm_info['SEC_FIRM_ORDER'])

        query += " ORDER BY SAVE_TIME DESC , REG_DT DESC"
        self.cursor.execute(query, params)

        results = self.cursor.fetchall()
        return [dict(zip([column[0] for column in self.cursor.description], row)) for row in results]

# Example Usage
if __name__ == "__main__":
    db = SQLiteManagerSQL()

    # Example data
    data_list = [
        {
            "SEC_FIRM_ORDER": 1,
            "ARTICLE_BOARD_ORDER": 2,
            "FIRM_NM": "Test Firm",
            "REG_DT": "20250101",
            "ATTACH_URL": "http://example.com",
            "ARTICLE_TITLE": "Test Title",
            "ARTICLE_URL": "http://example.com/article",
            "MAIN_CH_SEND_YN": "N",
            "DOWNLOAD_URL": None,
            "WRITER": "Author",
            "SAVE_TIME": datetime.now(),
            "TELEGRAM_URL": None,
            "KEY": "unique_key"
        }
    ]

    # Insert or update data
    # db.insert_data(data_list)

    # Fetch data
    rows = db.fetch_daily_articles_by_date()
    print(rows)

    # Update data
    # db.update_telegram_url(record_id=1, telegram_url="http://telegram.link")

    db.close_connection()
