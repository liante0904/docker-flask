function toggleMenu() {
    const menuPanel = document.querySelector('.menu-panel');
    menuPanel.classList.toggle('open');
}

// 검색창 토글
function toggleSearch() {
    const overlay = document.getElementById("searchOverlay");
    const searchInput = document.getElementById("searchInput");

    if (overlay.style.display === "flex") {
        overlay.style.display = "none";
    } else {
        overlay.style.display = "flex";
        searchInput.focus(); // 검색창 열릴 때 자동 포커스
    }
}

// 검색 실행
function submitSearch() {
    const query = document.getElementById("searchInput").value;
    if (!query.trim()) {
        alert("검색어를 입력해주세요.");
        return;
    }
    // 검색 요청을 서버로 전송
    window.location.href = `/search_report?query=${encodeURIComponent(query)}`;
}

// 검색 입력 필드에서 Enter 키 처리
document.getElementById("searchInput").addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        submitSearch();
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const subtitleElement = document.getElementById('subtitle');
    const reportContainer = document.getElementById('report-container');

    // URL에 따라 JSON 파일 경로 설정
    const isDailyGroup = window.location.pathname.includes('daily_group');
    const jsonBaseUrl = isDailyGroup 
        ? '/static/reports/grouped_reports.json' 
        : '/static/reports/recent_reports.json';

    // 타임스탬프 추가
    const timestamp = new Date().getTime();
    const jsonUrl = `${jsonBaseUrl}?t=${timestamp}`;

    subtitleElement.textContent = isDailyGroup 
        ? '현재 메뉴: 일자별 레포트' 
        : '현재 메뉴: 최근 게시된 레포트';

    // JSON 데이터 로드 및 렌더링
    fetch(jsonUrl)
        .then(response => {
            if (!response.ok) throw new Error('네트워크 응답에 문제가 있습니다.');
            return response.json();
        })
        .then(data => {
            renderReports(data);
        })
        .catch(error => {
            console.error('JSON 데이터를 가져오는 중 오류 발생:', error);
            reportContainer.innerHTML = '<p>데이터를 가져오는 데 실패했습니다.</p>';
        });

    function renderReports(data) {
        reportContainer.innerHTML = ''; // 기존 콘텐츠 제거

        Object.entries(data).forEach(([date, firms]) => {
            // 날짜 그룹 생성
            const dateGroup = document.createElement('div');
            dateGroup.className = 'date-group';

            const dateTitle = document.createElement('div');
            dateTitle.className = 'date-title';
            dateTitle.textContent = date;
            dateGroup.appendChild(dateTitle);

            // 회사별 그룹 생성
            Object.entries(firms).forEach(([firm, reports]) => {
                const companyGroup = document.createElement('div');
                companyGroup.className = 'company-group';

                const companyTitle = document.createElement('div');
                companyTitle.className = 'company-title';
                companyTitle.textContent = firm;
                companyGroup.appendChild(companyTitle);

                // 레포트 목록 생성
                reports.forEach(report => {
                    const reportElement = document.createElement('div');
                    reportElement.className = 'report';

                    const reportLink = document.createElement('a');
                    reportLink.href = report.link;
                    reportLink.target = '_blank';
                    reportLink.textContent = report.title;

                    const reportWriter = document.createElement('p');
                    reportWriter.textContent = `작성자: ${report.writer}`;

                    reportElement.appendChild(reportLink);
                    reportElement.appendChild(reportWriter);
                    companyGroup.appendChild(reportElement);
                });

                dateGroup.appendChild(companyGroup);
            });

            reportContainer.appendChild(dateGroup);
        });
    }
});
