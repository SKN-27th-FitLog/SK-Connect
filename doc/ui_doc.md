---
marp: true
size: 16:9
paginate: true
style: |
  /* 전체 기본 */
  section {
    font-family: "Pretendard", "Noto Sans KR", "Malgun Gothic", Arial, sans-serif;
    background: #fff;
    padding: 28px 32px;
  }

  /* 공통 테두리 스타일 */
  .box { border: 1.5px solid #333; border-radius: 2px; }

  /* 상단 메타 테이블 */
  .meta {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 14px;
  }
  .meta th, .meta td {
    border: 1px solid #333;
    padding: 6px 8px;
    vertical-align: middle;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .meta th { background: #f4f4f4; font-weight: 700; text-align: center; }
  .meta .label { width: 90px; }
  .meta .val   { width: 170px; }
  .meta .wide  { width: 360px; }
  .meta .small { width: 90px; }
  .meta .descH { width: 220px; text-align: center; font-weight: 700; }

  /* 본문 2컬럼 레이아웃 */
  .content {
    margin-top: 14px;
    display: grid;
    grid-template-columns: 1fr 360px; /* 좌측: 가변 / 우측: 고정 */
    gap: 16px;
    align-items: start; /* 내용 높이에 맞춤 */
    min-height: calc(100% - 84px); /* 상단 테이블 높이 대략 제외 */
  }

  /* 좌측 화면 영역 */
  .screen {
    position: relative;
    height: 100%;
    padding: 14px;
  }
  .screen .title {
    position: absolute;
    top: -10px;
    left: 50%;
    transform: translateX(-50%);
    background: #fff;
    padding: 0 10px;
    font-size: 13px;
    font-weight: 700;
  }
  .screen .inner {
    height: 100%;
    border: 1px solid #333;
    border-radius: 2px;
    /* 와이어프레임 느낌: 상단 살짝 물결/구분선 흉내는 간단히 점선으로 */
    background:
      linear-gradient(#fff, #fff) padding-box,
      repeating-linear-gradient(
        90deg,
        rgba(0,0,0,0.08) 0px,
        rgba(0,0,0,0.08) 0px,
        transparent 60px,
        transparent 60px
      );
  }
  .screen .imgWrap img {
    display: block;
    vertical-align: middle;
  }
  /* 이미지별 크기: class="img-숫자" 로 지정 (예: img-200 → 200px), 미지정 시 auto */
  .screen .imgWrap img.img-300 { width: 300px !important; height: auto !important; }
  .screen .imgWrap img.img-400 { width: 400px !important; height: auto !important; }
  .screen .imgWrap img.img-500 { width: 500px !important; height: auto !important; }
  .screen .imgWrap img.img-600 { width: 600px !important; height: auto !important; }
  .screen .imgWrap img.img-800 { width: 800px !important; height: auto !important; }
  /* 필요 시 위와 동일 형식으로 추가: img.img-180 { width: 180px !important; ... } */

  /* 우측 Description 패널 - 화면 크기에 따라 폰트 자동 축소, 넘치면 스크롤 */
  .descPanel {
    display: flex;
    flex-direction: column;
    max-height: calc(100vh - 130px);
    min-height: 0;
    overflow-y: auto;
  }
  .descPanel .head {
    border: 1px solid #333;
    border-bottom: none;
    padding: 8px 10px;
    font-weight: 800;
    text-align: center;
    font-size: clamp(10px, 1.8vmin, 16px);
  }
  .descPanel .list {
    border: 1px solid #333;
    padding: 0;
    display: grid;
    grid-auto-rows: auto;
  }

  .descItem {
    display: grid;
    grid-template-columns: 40px 1fr;
    border-top: 1px solid #333;
  }
  .descItem:first-child { border-top: none; }
  .descNum {
    border-right: 1px solid #333;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 10px;
    color: #c40000;
    font-weight: 800;
    font-size: clamp(9px, 1.6vmin, 14px);
  }
  .descBody {
    padding: 8px 10px;
    font-size: clamp(8px, 1.4vmin, 12.5px);
    line-height: 1.35;
  }
  .descBody ul { margin: 6px 0 0 18px; padding: 0; }
  .descBody li { margin: 2px 0; }



---
<!--------------------- 1페이지 ------------------------->

<table class="meta">
  <tr>
    <th class="label">버전(ver)</th><td class="val">2.0</td>
    <th class="label">페이지코드</th><td class="val">1</td>
    <th class="label">페이지명</th><td class="wide">게시글목록</td>
    <th class="label">이용자</th><td class="small">Mobile</td>
    <th class="descH">Description</th>
  </tr>
  <tr>
    <th class="label">작성인</th><td class="val">김경수</td>
    <th class="label">작성일</th><td class="val">2026.02.28</td>
    <th class="label">페이지 경로</th><td class="wide">-</td>
    <th class="label">페이지</th><td class="small">1</td>
    <td class="descH"> </td>
  </tr>
</table>

<div class="content">

  <div class="screen box">
    <!-- <div class="title">▼ 이어서 ▼</div> -->
    <div class="inner">
      <div class="imgWrap">
        <img src="네비게이터.png" alt="" />
      </div>
    </div>
  </div>

  <div class="descPanel">
    <div class="head">화면 설명</div>
  

  <div class="list">
    <div class="descItem">
      <div class="descNum">1</div>
      <div class="descBody">
        ■ 신규 작성 버튼 <br/>
        □ 설명
        <ul>
          <li>게시글 / 커뮤니티 화면에서만 표시 </li>
          <li>버튼 클릭 시 게시글 작성 / 모임 추가 페이지로 이동 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">2</div>
      <div class="descBody">
        ■ 페이지 네비게이터 <br/>
        □ 설명
        <ul>
          <li>화면 하단에 항상 표시 (게시글 작성 등 이부 페이지에선 예외) </li>
          <li>버튼 클릭 시 해당 화면으로 이동 </li>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>

---
<!--------------------- 2페이지 ------------------------->

<table class="meta">
  <tr>
    <th class="label">버전(ver)</th><td class="val">2.0</td>
    <th class="label">페이지코드</th><td class="val">2</td>
    <th class="label">페이지명</th><td class="wide">게시글목록_일반</td>
    <th class="label">이용자</th><td class="small">Mobile</td>
    <th class="descH">Description</th>
  </tr>
  <tr>
    <th class="label">작성인</th><td class="val">김경수</td>
    <th class="label">작성일</th><td class="val">2026.02.28</td>
    <th class="label">페이지 경로</th><td class="wide">-</td>
    <th class="label">페이지</th><td class="small">1</td>
    <td class="descH"> </td>
  </tr>
</table>

<div class="content">

  <div class="screen box">
    <!-- <div class="title">▼ 이어서 ▼</div> -->
    <div class="inner">
      <div class="imgWrap">
        <img src="게시글목록_일반.png" alt="" />
      </div>
    </div>
  </div>

  <div class="descPanel">
    <div class="head">화면 설명</div>
  

  <div class="list">
    <div class="descItem">
      <div class="descNum">1</div>
      <div class="descBody">
        ■ 탭 버튼 <br/>
        □ 설명
        <ul>
          <li>버튼에 따라 아래 표시되는 게시글 목록이 변경됨 </li>
          <li>목록 변경은 각 카테고리에서 부연설명 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">2</div>
      <div class="descBody">
        ■ 게시글 목록 <br/>
        □ 설명
        <ul>
          <li>조회된 게시글 목록을 표시한다. </li>
          <li>리스트는 상하 스크롤로 이동한다. </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">3</div>
      <div class="descBody">
        ■ 인터랙션 버튼 <br/>
        □ 설명
        <ul>
          <li>게시글 인터랙션 버튼. </li>
          <li>버튼 클릭 시 해당 게시글에 대해 추가 기능을 이용할 수 있다. </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">3</div>
      <div class="descBody">
        ■ 좋아요/댓글/공유 버튼튼 <br/>
        □ 설명
        <ul>
          <li>좋아요 : 클릭 시 좋아요 상태 변경, 좋아요 숫자 증감 </li>
          <li>댓글 : 해당 게시글로 이동 -> 댓글 입력 상태가 됨 </li>
          <li>공유 : 해당 게시글의 주소를 다른 앱으로 공유 -> 공유앱 목록 창 호출 </li>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>

---
<!--------------------- 3페이지 ------------------------->

<table class="meta">
  <tr>
    <th class="label">버전(ver)</th><td class="val">2.0</td>
    <th class="label">페이지코드</th><td class="val">3</td>
    <th class="label">페이지명</th><td class="wide">게시글목록_인기,관심,최신</td>
    <th class="label">이용자</th><td class="small">Mobile</td>
    <th class="descH">Description</th>
  </tr>
  <tr>
    <th class="label">작성인</th><td class="val">김경수</td>
    <th class="label">작성일</th><td class="val">2026.02.28</td>
    <th class="label">페이지 경로</th><td class="wide">-</td>
    <th class="label">페이지</th><td class="small">1</td>
    <td class="descH"> </td>
  </tr>
</table>

<div class="content">

  <div class="screen box">
    <!-- <div class="title">▼ 이어서 ▼</div> -->
    <div class="inner">
      <div class="imgWrap">
        <img src="게시글목록_인기,관심,최신.png" alt="" />
      </div>
    </div>
  </div>

  <div class="descPanel">
    <div class="head">화면 설명</div>
  

  <div class="list">
    <div class="descItem">
      <div class="descNum">1</div>
      <div class="descBody">
        ■ 인기 탭 버튼 <br/>
        □ 설명
        <ul>
          <li>버튼 클릭 시 게시글이 좋아요 내림차 순으로 정렬 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">2</div>
      <div class="descBody">
        ■ 관심 탭 버튼 <br/>
        □ 설명
        <ul>
          <li>버튼 클릭 시 내가 좋아요 누른 게시글만 필터해서 표시 </li>
          <li>정렬 순서는 서버에서 주는 대로 표시함 (왠만하면 수정일자 내림차순이면 좋음) </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">3</div>
      <div class="descBody">
        ■ 최신 탭 버튼 <br/>
        □ 설명
        <ul>
          <li>버튼 클릭 시 수정일자 내림차 순으로 게시글 표시 </li>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>

---
<!--------------------- 4페이지 ------------------------->

<table class="meta">
  <tr>
    <th class="label">버전(ver)</th><td class="val">2.0</td>
    <th class="label">페이지코드</th><td class="val">4</td>
    <th class="label">페이지명</th><td class="wide">게시글목록_카테고리</td>
    <th class="label">이용자</th><td class="small">Mobile</td>
    <th class="descH">Description</th>
  </tr>
  <tr>
    <th class="label">작성인</th><td class="val">김경수</td>
    <th class="label">작성일</th><td class="val">2026.02.28</td>
    <th class="label">페이지 경로</th><td class="wide">-</td>
    <th class="label">페이지</th><td class="small">1</td>
    <td class="descH"> </td>
  </tr>
</table>

<div class="content">

  <div class="screen box">
    <!-- <div class="title">▼ 이어서 ▼</div> -->
    <div class="inner">
      <div class="imgWrap">
        <img src="게시글목록_카테고리.png" alt="" />
      </div>
    </div>
  </div>

  <div class="descPanel">
    <div class="head">화면 설명</div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">1</div>
      <div class="descBody">
        ■ 관심 필터 <br/>
        □ 설명
        <ul>
          <li>스터디/운동/맛집/취미/네트워킹/기타 6개 항목 제공 </li>
          <li>카테고리 선택 시 기본으로 선택된 필터가 존재함 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">2</div>
      <div class="descBody">
        ■ 필터된 게시글 목록 <br/>
        □ 설명
        <ul>
          <li>선택된 필터와 일치하는 게시글만 목록에 표시됨 </li>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>

---
<!--------------------- 5페이지 ------------------------->

<table class="meta">
  <tr>
    <th class="label">버전(ver)</th><td class="val">2.0</td>
    <th class="label">페이지코드</th><td class="val">5</td>
    <th class="label">페이지명</th><td class="wide">게시글</td>
    <th class="label">이용자</th><td class="small">Mobile</td>
    <th class="descH">Description</th>
  </tr>
  <tr>
    <th class="label">작성인</th><td class="val">김경수</td>
    <th class="label">작성일</th><td class="val">2026.02.28</td>
    <th class="label">페이지 경로</th><td class="wide">-</td>
    <th class="label">페이지</th><td class="small">1</td>
    <td class="descH"> </td>
  </tr>
</table>

<div class="content">

  <div class="screen box">
    <!-- <div class="title">▼ 이어서 ▼</div> -->
    <div class="inner">
      <div class="imgWrap">
        <img src="게시글.png" alt="" />
      </div>
    </div>
  </div>

  <div class="descPanel">
    <div class="head">화면 설명</div>
  

  <div class="list">
    <div class="descItem">
      <div class="descNum">1</div>
      <div class="descBody">
        ■ 게시글 title <br/>
        □ 설명
        <ul>
          <li>클릭 시 홈 화면으로 나감 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">2</div>
      <div class="descBody">
        ■ 이미지 <br/>
        □ 설명
        <ul>
          <li>게시글에 등록된 이미지 표시(없으면 표시 안함) </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">3</div>
      <div class="descBody">
        ■ 작성자 정보 <br/>
        □ 설명
        <ul>
          <li>작성자 이름 / 게시글 수정일자 표시 / 게시글 편집 버튼 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">4</div>
      <div class="descBody">
        ■ 게시글 제목/내용, 카테고리, 위치 <br/>
        □ 설명
        <ul>
          <li>게시글 제목과 내용 표시 </li>
          <li>게시글의 카테고리 표시 (이미지 추후 수정) </li>
          <li>게시글에 링크된 위치 표시 (이미지 추후 수정) </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">5</div>
      <div class="descBody">
        ■ 좋아요 버튼 <br/>
        □ 설명
        <ul>
          <li>게시글의 좋아요 개수 표시 / 버튼 클릭 시 좋아요 동작 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">6</div>
      <div class="descBody">
        ■ 댓글 목록 <br/>
        □ 설명
        <ul>
          <li>게시글의 댓글 목록 표시 </li>
          <li>댓글 목록은 상하 스크롤로 이동 가능 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">7</div>
      <div class="descBody">
        ■ 댓글 입력 창 <br/>
        □ 설명
        <ul>
          <li>신규 댓글을 추가하기 위한 입력창 </li>
          <li>입력기에 포커스가 가면 모바일 텍스트 입력기 같이 표시됨 </li>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>

---
<!--------------------- 6페이지 ------------------------->

<table class="meta">
  <tr>
    <th class="label">버전(ver)</th><td class="val">2.0</td>
    <th class="label">페이지코드</th><td class="val">6</td>
    <th class="label">페이지명</th><td class="wide">게시글작성</td>
    <th class="label">이용자</th><td class="small">Mobile</td>
    <th class="descH">Description</th>
  </tr>
  <tr>
    <th class="label">작성인</th><td class="val">김경수</td>
    <th class="label">작성일</th><td class="val">2026.02.28</td>
    <th class="label">페이지 경로</th><td class="wide">-</td>
    <th class="label">페이지</th><td class="small">1</td>
    <td class="descH"> </td>
  </tr>
</table>

<div class="content">

  <div class="screen box">
    <!-- <div class="title">▼ 이어서 ▼</div> -->
    <div class="inner">
      <div class="imgWrap">
        <img src="게시글작성.png" alt="" />
      </div>
    </div>
  </div>

  <div class="descPanel">
    <div class="head">화면 설명</div>
  

  <div class="list">
    <div class="descItem">
      <div class="descNum">1</div>
      <div class="descBody">
        ■ title <br/>
        □ 설명
        <ul>
          <li>클릭 시 홈 화면 (게시글 목록) 으로 이동 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">2<br><br>~<br><br>7</div>
      <div class="descBody">
        ■ 게시글 정보 입력 <br/>
        □ 설명
        <ul>
          <li>게시글에 등록될 각 정보를 입력 </li>
          2) 제목 (필수)<br>
          3) 내용 (필수)<br>
          4) 카테고리 (필수)<br>
          5) 위치 -> 지도 api 호출해서 위치 찾음<br>
          6) 이미지 -> 내 기기에서 등록 이미지 찾는 창 호출<br>
          7) 입력 버튼 -> 필수 정보 모두 입력해야 누를 수 있음<br>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>

---
<!--------------------- 7페이지 ------------------------->

<table class="meta">
  <tr>
    <th class="label">버전(ver)</th><td class="val">2.0</td>
    <th class="label">페이지코드</th><td class="val">7</td>
    <th class="label">페이지명</th><td class="wide">지도</td>
    <th class="label">이용자</th><td class="small">Mobile</td>
    <th class="descH">Description</th>
  </tr>
  <tr>
    <th class="label">작성인</th><td class="val">김경수</td>
    <th class="label">작성일</th><td class="val">2026.02.28</td>
    <th class="label">페이지 경로</th><td class="wide">-</td>
    <th class="label">페이지</th><td class="small">1</td>
    <td class="descH"> </td>
  </tr>
</table>

<div class="content">

  <div class="screen box">
    <!-- <div class="title">▼ 이어서 ▼</div> -->
    <div class="inner">
      <div class="imgWrap">
        <img src="지도.png" alt="" />
      </div>
    </div>
  </div>

  <div class="descPanel">
    <div class="head">화면 설명</div>
  

  <div class="list">
    <div class="descItem">
      <div class="descNum">1</div>
      <div class="descBody">
        ■ 지도 인터랙션 버튼 <br/>
        □ 설명
        <ul>
          <li>확대 버튼 </li>
          <li>축소 버튼 </li>
          <li>내위치 버튼 : 기기에 등록된 내 위치로 위치정보 갱신 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">2</div>
      <div class="descBody">
        ■ 지도 화면 <br/>
        □ 설명
        <ul>
          <li>지도는 지도api 통해서 얻어와 표시 </li>
          <li>기본으로 표시할 위치는 내 현재 위치로 (모바일 기준) </li>
          <li>지도 핀 : 게시글이 가지고 있는 위치로 핀을 표현 </li>
          <li>핀의 아이콘은 게시글 카테고리를 기준으로 결정됨 </li>
          <li>지도 중앙 위치를 기준으로 일정 반경내 핀을 검색해서 표시 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">3</div>
      <div class="descBody">
        ■ 지도 핀 -> 요약 정보창 <br/>
        □ 설명
        <ul>
          <li>핀의 선택 시 해당 게시글의 요약 정보창 표시 </li>
          <li>요약 정보창에는 게시글의 제목일부 / 내용일부 / 카테고리 / 위치 를 표시한다.  </li>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>
