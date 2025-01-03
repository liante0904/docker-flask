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

    def insert_data(self, data_list):
        """Insert or update data in the database."""
        inserted_count = 0
        updated_count = 0

        for entry in data_list:
            # Check if the record already exists
            self.cursor.execute("SELECT COUNT(1) FROM data_main_daily_send WHERE KEY = ?", (entry['KEY'],))
            record_exists = self.cursor.fetchone()[0] > 0

            if record_exists:
                # Update existing record
                self.cursor.execute("""
                    UPDATE data_main_daily_send
                    SET REG_DT = ?, WRITER = ?, DOWNLOAD_URL = ?, TELEGRAM_URL = ?
                    WHERE KEY = ?
                """, (entry.get('REG_DT', ''),
                      entry.get('WRITER', ''),
                      entry.get('DOWNLOAD_URL', None),
                      entry.get('TELEGRAM_URL', None),
                      entry['KEY']))
                updated_count += 1
            else:
                # Insert new record
                self.cursor.execute("""
                    INSERT INTO data_main_daily_send (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
                                                       ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN,
                                                       DOWNLOAD_URL, WRITER, SAVE_TIME, TELEGRAM_URL, KEY)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (entry['SEC_FIRM_ORDER'],
                      entry['ARTICLE_BOARD_ORDER'],
                      entry['FIRM_NM'],
                      entry.get('REG_DT', ''),
                      entry.get('ATTACH_URL', ''),
                      entry.get('ARTICLE_TITLE', ''),
                      entry.get('ARTICLE_URL', ''),
                      entry.get('MAIN_CH_SEND_YN', 'N'),
                      entry.get('DOWNLOAD_URL', None),
                      entry['WRITER'],
                      entry['SAVE_TIME'],
                      entry.get('TELEGRAM_URL', None),
                      entry['KEY']))
                inserted_count += 1

        self.conn.commit()
        print(f"Data inserted: {inserted_count} rows, updated: {updated_count} rows.")
        return inserted_count, updated_count

    def fetch_daily_articles_by_date(self, firm_info=None, date_str=None):
        """Fetch articles by date."""
        query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
        three_days_ago = (datetime.strptime(query_date, '%Y%m%d') - timedelta(days=14)).strftime('%Y%m%d')
        two_days_after = (datetime.strptime(query_date, '%Y%m%d') + timedelta(days=14)).strftime('%Y%m%d')

        query = """
            SELECT * FROM data_main_daily_send
            WHERE REG_DT BETWEEN ? AND ? AND KEY IS NOT NULL
        """
        params = [three_days_ago, two_days_after]

        if firm_info:
            query += " AND SEC_FIRM_ORDER = ?"
            params.append(firm_info['SEC_FIRM_ORDER'])

        query += " ORDER BY REG_DT DESC, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME"
        self.cursor.execute(query, params)

        results = self.cursor.fetchall()
        return [dict(zip([column[0] for column in self.cursor.description], row)) for row in results]

    def update_telegram_url(self, record_id, telegram_url, article_title=None):
        """Update telegram URL and optionally article title."""
        query = "UPDATE data_main_daily_send SET TELEGRAM_URL = ?"
        params = [telegram_url]

        if article_title:
            query += ", ARTICLE_TITLE = ?"
            params.append(article_title)

        query += " WHERE id = ?"
        params.append(record_id)

        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor.rowcount

    def daily_select_data(self, date_str=None, type=None):
        """Fetch data for specific date and type."""
        if type not in ['send', 'download']:
            raise ValueError("Invalid type. Must be 'send' or 'download'.")

        query_date = datetime.now().strftime('%Y-%m-%d') if not date_str else f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

        three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y%m%d')
        two_days_after = (datetime.now() + timedelta(days=2)).strftime('%Y%m%d')

        query = """
            SELECT * FROM data_main_daily_send
            WHERE REG_DT >= ? AND REG_DT <= ? AND DATE(SAVE_TIME) = ?
        """
        params = [three_days_ago, two_days_after, query_date]

        if type == 'send':
            query += " AND (MAIN_CH_SEND_YN != 'Y' OR MAIN_CH_SEND_YN IS NULL)"
        elif type == 'download':
            query += " AND MAIN_CH_SEND_YN = 'Y' AND DOWNLOAD_URL IS NULL"

        self.cursor.execute(query, params)
        results = self.cursor.fetchall()
        return [dict(zip([column[0] for column in self.cursor.description], row)) for row in results]

    def daily_update_data(self, fetched_rows, type):
        """Update data based on the type."""
        if type == 'send':
            for row in fetched_rows:
                self.cursor.execute("""
                    UPDATE data_main_daily_send
                    SET MAIN_CH_SEND_YN = 'Y'
                    WHERE id = ?
                """, (row['id'],))
        elif type == 'download':
            self.cursor.execute("""
                UPDATE data_main_daily_send
                SET DOWNLOAD_URL = 'Y'
                WHERE id = ?
            """, (fetched_rows['id'],))

        self.conn.commit()

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
