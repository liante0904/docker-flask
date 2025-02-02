function toggleMenu() {
    const menuPanel = document.querySelector('.menu-panel');
    menuPanel.classList.toggle('open');
}

document.addEventListener('DOMContentLoaded', () => {
    const subtitleElement = document.getElementById('subtitle');
    const reportContainer = document.getElementById('report-container');
    const loadingElement = document.getElementById('loading');

    const isDailyGroup = window.location.pathname.includes('daily_group');
    const jsonBaseUrl = isDailyGroup 
        ? '/static/reports/daily_group_reports.json' 
        : '/static/reports/recent_reports.json';

    const timestamp = new Date().getTime();
    const jsonUrl = `${jsonBaseUrl}?t=${timestamp}`;

    subtitleElement.textContent = isDailyGroup 
        ? '현재 메뉴: 일자별 레포트' 
        : '현재 메뉴: 최근 게시된 레포트';

    // 로딩 표시
    loadingElement.style.display = 'block';

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
        })
        .finally(() => {
            // 로딩 메시지 숨기기
            loadingElement.style.display = 'none';
        });

    function renderReports(data) {
        reportContainer.innerHTML = ''; 
    
        // JSON 데이터의 날짜 형식 구분
        const isIsoFormat = Object.keys(data)[0].includes('T'); // ISO 8601 포맷인지 확인
    
        // 날짜 정렬 (내림차순)
        const sortedData = Object.entries(data).sort(([dateA], [dateB]) => {
            const dateAParsed = isIsoFormat ? new Date(dateA) : new Date(dateA.slice(0, 4) + '-' + dateA.slice(4, 6) + '-' + dateA.slice(6, 8));
            const dateBParsed = isIsoFormat ? new Date(dateB) : new Date(dateB.slice(0, 4) + '-' + dateB.slice(4, 6) + '-' + dateB.slice(6, 8));
            return dateBParsed - dateAParsed; // 내림차순 정렬
        });
    
        // 렌더링
        sortedData.forEach(([date, firms]) => {
            const dateGroup = document.createElement('div');
            dateGroup.className = 'date-group';
    
            const dateTitle = document.createElement('div');
            dateTitle.className = 'date-title';
            dateTitle.textContent = date;
            dateGroup.appendChild(dateTitle);
    
            Object.entries(firms).forEach(([firm, reports]) => {
                const companyGroup = document.createElement('div');
                companyGroup.className = 'company-group';
    
                const companyTitle = document.createElement('div');
                companyTitle.className = 'company-title';
                companyTitle.textContent = firm;
                companyGroup.appendChild(companyTitle);
    
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