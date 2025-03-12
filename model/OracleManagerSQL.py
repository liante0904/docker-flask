import oracledb
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Oracle Wallet 설정
WALLET_LOCATION = os.getenv('WALLET_LOCATION')  # .env에 Wallet 디렉토리 경로 추가
WALLET_PASSWORD = os.getenv('WALLET_PASSWORD')  # .env에 Wallet 비밀번호 추가 (필요 시)
DB_USER = os.getenv('DB_USER')                  # Oracle 사용자 이름
DB_PASSWORD = os.getenv('DB_PASSWORD')          # Oracle 비밀번호
DB_DSN = os.getenv('DB_DSN')                    # tnsnames.ora의 TNS 별칭

class OracleManagerSQL:
    def __init__(self):
        # Oracle Wallet을 사용한 연결 설정
        self.conn = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN,
            config_dir=WALLET_LOCATION,
            wallet_location=WALLET_LOCATION,
            wallet_password=WALLET_PASSWORD
        )
        self.cursor = self.conn.cursor()

    def close_connection(self):
        self.conn.close()

    def fetch_last_modified_time(self):
        """SAVE_TIME 컬럼에서 가장 최근 시간을 반환"""
        query = "SELECT MAX(SAVE_TIME) FROM data_main_daily_send"
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        if result and result[0]:
            # Oracle에서 반환되는 datetime 객체를 그대로 사용
            return result[0] if isinstance(result[0], datetime) else datetime.fromisoformat(result[0])
        return None

    def fetch_daily_articles_by_date(self, firm_info=None, date_str=None):
        """Fetch articles by date."""
        query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
        three_days_ago = (datetime.strptime(query_date, '%Y%m%d') - timedelta(days=3)).strftime('%Y%m%d')
        two_days_after = (datetime.strptime(query_date, '%Y%m%d') + timedelta(days=2)).strftime('%Y%m%d')

        query = """
            SELECT * FROM data_main_daily_send
            WHERE REG_DT BETWEEN :1 AND :2
        """
        params = [three_days_ago, two_days_after]

        if firm_info:
            query += " AND SEC_FIRM_ORDER = :3"
            params.append(firm_info['SEC_FIRM_ORDER'])

        query += " ORDER BY id DESC, REG_DT DESC, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER"
        self.cursor.execute(query, params)

        # Oracle은 컬럼 이름과 함께 결과를 반환
        columns = [col[0] for col in self.cursor.description]
        results = self.cursor.fetchall()
        return [dict(zip(columns, row)) for row in results]

    def fetch_articles_by_todate(self, firm_info=None, date_str=None):
        """Fetch articles by date."""
        query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
        three_days_ago = (datetime.strptime(query_date, '%Y%m%d') - timedelta(days=3)).strftime('%Y%m%d')
        two_days_after = (datetime.strptime(query_date, '%Y%m%d') + timedelta(days=2)).strftime('%Y%m%d')

        query = """
            SELECT * FROM data_main_daily_send
            WHERE REG_DT BETWEEN :1 AND :2
        """
        params = [three_days_ago, two_days_after]

        if firm_info:
            query += " AND SEC_FIRM_ORDER = :3"
            params.append(firm_info['SEC_FIRM_ORDER'])

        query += " ORDER BY id DESC, REG_DT DESC"
        self.cursor.execute(query, params)

        columns = [col[0] for col in self.cursor.description]
        results = self.cursor.fetchall()
        return [dict(zip(columns, row)) for row in results]

    def search_reports_by_keyword(self, keyword, last_id, limit=30):
        """
        키워드로 레포트를 검색하고 페이징 처리합니다.
        """
        
        query = """
            SELECT id, ARTICLE_TITLE, TELEGRAM_URL, WRITER, SAVE_TIME, FIRM_NM
            FROM (
                SELECT id, ARTICLE_TITLE, TELEGRAM_URL, WRITER, SAVE_TIME, FIRM_NM
                FROM data_main_daily_send
                WHERE CONTAINS(ARTICLE_TITLE, :keyword, 1) > 0
                AND id < NVL(:last_id, (SELECT MAX(id) FROM data_main_daily_send))
                ORDER BY id DESC
            )
            WHERE ROWNUM <= :limit
        """

        keyword_pattern = f"%{keyword}%"
        params = {"keyword": keyword_pattern, "last_id": last_id, "limit": limit}

        self.cursor.execute(query, params)
        columns = [col[0] for col in self.cursor.description]
        results = self.cursor.fetchall()

        return [dict(zip(columns, row)) for row in results]

    def fetch_global_articles_by_todate(self, firm_info=None, date_str=None):
        """Fetch articles by date."""
        query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
        three_days_ago = (datetime.strptime(query_date, '%Y%m%d') - timedelta(days=14)).strftime('%Y%m%d')
        two_days_after = (datetime.strptime(query_date, '%Y%m%d') + timedelta(days=2)).strftime('%Y%m%d')

        query = """
            SELECT * FROM data_main_daily_send
            WHERE MAIN_CH_SEND_YN = 'Y'
            AND MKT_TP != 'KR'
            AND REG_DT BETWEEN :1 AND :2
            ORDER BY id DESC, REG_DT DESC
        """
        params = [three_days_ago, two_days_after]

        self.cursor.execute(query, params)
        columns = [col[0] for col in self.cursor.description]
        results = self.cursor.fetchall()
        return [dict(zip(columns, row)) for row in results]

    def fetch_global_articles_by_id(self, last_id=0, limit=10):
        """Fetch articles by date."""
        query = """
            SELECT * FROM data_main_daily_send
            WHERE MAIN_CH_SEND_YN = 'Y'
            AND MKT_TP != 'KR'
        """
        params = []

        if last_id:
            query += " AND id < :1"
            params.append(last_id)

        query += " ORDER BY id DESC FETCH FIRST :2 ROWS ONLY"
        params.append(limit)

        self.cursor.execute(query, params)
        columns = [col[0] for col in self.cursor.description]
        results = self.cursor.fetchall()
        return [dict(zip(columns, row)) for row in results] if results else []

# Example Usage
if __name__ == "__main__":
    db = OracleManagerSQL()

    # Fetch data
    rows = db.fetch_daily_articles_by_date()
    print(rows)

    db.close_connection()