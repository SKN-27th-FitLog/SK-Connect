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
        ■ 게시글 title <br/>
        □ 설명
        <ul>
          <li>화면 중앙정렬 / 상단에 제목 표시 </li>
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
        ■ 게시글 title <br/>
        □ 설명
        <ul>
          <li>화면 중앙정렬 / 상단에 제목 표시 </li>
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
        ■ 게시글 title <br/>
        □ 설명
        <ul>
          <li>화면 중앙정렬 / 상단에 제목 표시 </li>
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
        ■ 게시글 title <br/>
        □ 설명
        <ul>
          <li>화면 중앙정렬 / 상단에 제목 표시 </li>
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
          <li>화면 중앙정렬 / 상단에 제목 표시 </li>
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
        ■ 게시글 title <br/>
        □ 설명
        <ul>
          <li>화면 중앙정렬 / 상단에 제목 표시 </li>
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
        ■ 게시글 title <br/>
        □ 설명
        <ul>
          <li>화면 중앙정렬 / 상단에 제목 표시 </li>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>
