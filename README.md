# Docker Flask Application

이 프로젝트는 Flask 애플리케이션을 Docker 컨테이너로 배포하기 위한 설정을 포함합니다. 최근 AMD 기반 서버에서 ARM(Oracle Cloud) 기반 서버로 환경을 이전하며, uv를 도입하여 빌드를 최적화하고 NGINX + SSL(Let's Encrypt) 자동 갱신 환경을 구성했습니다.

## 주요 스택
- **Python**: 3.12 (uv 사용, `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`)
- **Web Server**: Gunicorn
- **Proxy**: NGINX (Alpine 기반)
- **Database**: Oracle DB (Thin Mode) + SQLite3

## 🚨 서버 환경 세팅 시 주의 사항 (특히 SSL 인증서 연동)

도커를 이용해 NGINX 컨테이너에 호스트의 Let's Encrypt 인증서를 연동할 때 주의해야 할 핵심 사항을 정리했습니다. (이 설정이 어긋나면 도커가 가짜 폴더를 생성하여 인증서 구조가 깨질 수 있습니다.)

### 1. 도커 볼륨 마운트 시 "디렉토리 자동 생성" 주의
`docker-compose.yml`에서 호스트의 파일을 컨테이너에 마운트할 때, **호스트에 해당 파일이 존재하지 않으면 도커는 그 이름으로 빈 디렉토리를 만들어 버립니다.**
한 번 디렉토리가 생성되면, 나중에 인증서 파일을 복사(`cp`)하거나 생성하려 해도 실패하게 되며 `PEM_read_bio_X509_AUX() failed (no start line)` 등의 에러가 발생합니다.

**해결 방안:**
- 파일 단위로 개별 마운트하지 말고, **`/etc/letsencrypt` 폴더 전체를 마운트**하는 것이 가장 안전합니다.
- 예시: `- /etc/letsencrypt:/etc/letsencrypt:ro`

### 2. Let's Encrypt `live` 폴더의 심볼릭 링크 구조
Let's Encrypt의 인증서 파일은 `/etc/letsencrypt/live/도메인명/` 폴더 내에 존재하지만, 이 파일들은 실제 파일이 아니라 `../../archive/도메인명/` 내의 진짜 파일을 가리키는 **심볼릭 링크**입니다.

- 전체 폴더(`/etc/letsencrypt`)를 마운트하면 도커 내부에서도 이 링크 구조가 유지되어 정상 작동합니다.
- 만약 실수로 폴더가 꼬이거나 도커가 가짜 폴더를 만들었다면, **가짜 폴더를 모두 지우고 원본 파일(`archive`)과의 심볼릭 링크를 수동으로 복구**해야 자동 갱신(`certbot renew`)이 제대로 동작합니다.

#### 💡 심볼릭 링크 수동 복구 명령어
```bash
# 가짜 폴더 삭제
sudo rm -rf /etc/letsencrypt/live/내도메인/fullchain.pem
sudo rm -rf /etc/letsencrypt/live/내도메인/privkey.pem

# archive 폴더의 원본 파일과 링크 연결
sudo ln -sf ../../archive/내도메인/fullchain1.pem /etc/letsencrypt/live/내도메인/fullchain.pem
sudo ln -sf ../../archive/내도메인/privkey1.pem /etc/letsencrypt/live/내도메인/privkey.pem
```

### 3. 인증서 자동 갱신 (crontab)
도커 환경에서 NGINX가 80/443 포트를 점유하고 있을 때, 인증서를 자동으로 갱신하고 NGINX에 반영하려면 호스트 서버의 `crontab`에 아래와 같이 설정합니다.

```bash
sudo crontab -e

# 매월 1일 새벽 3시에 갱신 시도 후, 도커 NGINX 컨테이너 재시작
0 3 1 * * certbot renew && docker exec nginx nginx -s reload
```

### 4. OCI(Oracle Cloud) 포트 개방 필수
아무리 리눅스(`iptables`)나 도커에서 80/443 포트를 열어도, **OCI 콘솔의 네트워킹 설정(VCN -> 보안 목록/Security Lists -> 수신 규칙)**에서 해당 포트(TCP 80, 443)를 명시적으로 열어주지 않으면 외부에서 접근할 수 없습니다.

---

## 실행 방법

1. 환경 변수 파일(`.env`) 구성
2. (필요 시) `certbot`을 이용해 SSL 인증서 발급
3. 도커 컴포즈 실행
```bash
docker-compose up -d --build
```
