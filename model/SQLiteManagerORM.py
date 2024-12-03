from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func, update, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SQLITE_PATH = os.getenv('SQLITE_PATH')

db_path = os.path.expanduser(SQLITE_PATH)
Base = declarative_base()
engine = create_engine(f'sqlite:///{db_path}', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

# Define ORM model for data_main_daily_send
class DataMainDailySend(Base):
    __tablename__ = 'data_main_daily_send'

    id = Column(Integer, primary_key=True)
    SEC_FIRM_ORDER = Column(Integer, nullable=False)
    ARTICLE_BOARD_ORDER = Column(Integer, nullable=False)
    FIRM_NM = Column(String(255), nullable=False)
    REG_DT = Column(String(8))
    ATTACH_URL = Column(Text)
    ARTICLE_TITLE = Column(Text)
    ARTICLE_URL = Column(Text)
    MAIN_CH_SEND_YN = Column(String(1), default='N')
    DOWNLOAD_URL = Column(Text)
    WRITER = Column(String(255))
    SAVE_TIME = Column(DateTime)
    TELEGRAM_URL = Column(Text)
    KEY = Column(String(255), unique=True)

# Ensure the table exists
Base.metadata.create_all(engine)

class SQLiteManagerORM:
    def __init__(self):
        self.session = Session()

    def close_session(self):
        self.session.close()

    def insert_data(self, data_list):
        """Insert or update data in the database."""
        inserted_count = 0
        updated_count = 0

        for entry in data_list:
            stmt = update(DataMainDailySend).where(DataMainDailySend.KEY == entry['KEY']).values(
                REG_DT=entry.get('REG_DT', ''),
                WRITER=entry.get('WRITER', ''),
                DOWNLOAD_URL=entry.get('DOWNLOAD_URL', None),
                TELEGRAM_URL=entry.get('TELEGRAM_URL', None)
            ).execution_options(synchronize_session="fetch")

            result = self.session.execute(stmt)

            if result.rowcount == 0:
                # If no rows were updated, insert a new record
                new_record = DataMainDailySend(**entry)
                self.session.add(new_record)
                inserted_count += 1
            else:
                updated_count += 1

        self.session.commit()
        print(f"Data inserted: {inserted_count} rows, updated: {updated_count} rows.")
        return inserted_count, updated_count

    def fetch_daily_articles_by_date(self, firm_info=None, date_str=None):
        """Fetch articles by date."""
        query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')

        three_days_ago = (datetime.strptime(query_date, '%Y%m%d') - timedelta(days=14)).strftime('%Y%m%d')
        two_days_after = (datetime.strptime(query_date, '%Y%m%d') + timedelta(days=14)).strftime('%Y%m%d')

        query = self.session.query(DataMainDailySend).filter(
            and_(
                DataMainDailySend.REG_DT.between(three_days_ago, two_days_after),
                DataMainDailySend.KEY.isnot(None)
            )
        )

        if firm_info:
            query = query.filter(DataMainDailySend.SEC_FIRM_ORDER == firm_info['SEC_FIRM_ORDER'])

        results = query.order_by(
            DataMainDailySend.REG_DT.desc(),
            DataMainDailySend.SEC_FIRM_ORDER,
            DataMainDailySend.ARTICLE_BOARD_ORDER,
            DataMainDailySend.SAVE_TIME
        ).all()

        return [row.__dict__ for row in results]

    def update_telegram_url(self, record_id, telegram_url, article_title=None):
        """Update telegram URL and optionally article title."""
        stmt = update(DataMainDailySend).where(DataMainDailySend.id == record_id).values(
            TELEGRAM_URL=telegram_url
        )

        if article_title:
            stmt = stmt.values(ARTICLE_TITLE=article_title)

        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount

    def daily_select_data(self, date_str=None, type=None):
        """Fetch data for specific date and type."""
        if type not in ['send', 'download']:
            raise ValueError("Invalid type. Must be 'send' or 'download'.")

        query_date = datetime.now().strftime('%Y-%m-%d') if not date_str else f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

        three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y%m%d')
        two_days_after = (datetime.now() + timedelta(days=2)).strftime('%Y%m%d')

        query = self.session.query(DataMainDailySend).filter(
            and_(
                DataMainDailySend.REG_DT >= three_days_ago,
                DataMainDailySend.REG_DT <= two_days_after,
                func.date(DataMainDailySend.SAVE_TIME) == query_date
            )
        )

        if type == 'send':
            query = query.filter(
                or_(DataMainDailySend.MAIN_CH_SEND_YN != 'Y', DataMainDailySend.MAIN_CH_SEND_YN.is_(None))
            )
        elif type == 'download':
            query = query.filter(DataMainDailySend.MAIN_CH_SEND_YN == 'Y', DataMainDailySend.DOWNLOAD_URL.is_(None))

        return [row.__dict__ for row in query.all()]

    def daily_update_data(self, fetched_rows, type):
        """Update data based on the type."""
        if type == 'send':
            for row in fetched_rows:
                stmt = update(DataMainDailySend).where(DataMainDailySend.id == row['id']).values(
                    MAIN_CH_SEND_YN='Y'
                )
                self.session.execute(stmt)
        elif type == 'download':
            stmt = update(DataMainDailySend).where(DataMainDailySend.id == fetched_rows['id']).values(
                DOWNLOAD_URL='Y'
            )
            self.session.execute(stmt)

        self.session.commit()

# Example Usage
if __name__ == "__main__":
    db = SQLiteManagerORM()

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

    # # Insert or update data
    # db.insert_data(data_list)

    # Fetch data
    # rows = db.fetch_daily_articles_by_date(firm_info={"SEC_FIRM_ORDER": 1})
    rows = db.fetch_daily_articles_by_date()
    print(rows)

    # # Update data
    # db.update_telegram_url(record_id=1, telegram_url="http://telegram.link")
    db.close_session()
