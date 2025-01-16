# Python 이미지 기반
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY requirements.txt /app/

# 종속성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 및 관련 파일 복사
COPY . .

# 환경 변수 설정
ENV PDF_FOLDER=/app/pdf \
    DB_FOLDER=/app/sqlite3 \
    TZ=Asia/Seoul

# Timezone 설정 (옵션)
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 포트 열기
EXPOSE 5000

# Gunicorn 실행
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "60", "--keep-alive", "75", "app:app"]

# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--keep-alive", "75", "app:app"]


# Gunicorn 실행 시 SSL 설정 추가
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "5", "--certfile=/app/cert.pem", "--keyfile=/app/privkey.pem", "app:app"]

# Flask 애플리케이션 실행
#CMD ["python", "app.py"]
