# Python 이미지 기반
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY app.py /app/
COPY requirements.txt /app/

# 종속성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 인증서 복사
COPY cert.pem /app/
COPY privkey.pem /app/

COPY . .
# 환경 변수 설정 (PDF 디렉토리)
ENV PDF_FOLDER=/app/pdf

# 포트 열기
EXPOSE 5000

# Flask 애플리케이션 실행
CMD ["python", "app.py"]
