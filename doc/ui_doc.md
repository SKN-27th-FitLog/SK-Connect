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
<!----------------- 1페이지 ----------------------->

<table class="meta">
  <tr>
    <th class="label">버전(ver)</th><td class="val">1.0</td>
    <th class="label">페이지코드</th><td class="val">1</td>
    <th class="label">페이지명</th><td class="wide">board</td>
    <th class="label">이용자</th><td class="small">PC</td>
    <th class="descH">Description</th>
  </tr>
  <tr>
    <th class="label">작성인</th><td class="val">김경수</td>
    <th class="label">작성일</th><td class="val">2026.02.24</td>
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
        <img src="ui_doc_borad.png" alt="" class="img-500"/>
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

  <div class="list">
    <div class="descItem">
      <div class="descNum">2</div>
      <div class="descBody">
        ■ 게시글 - 카테고리 <br/>
        □ 설명
        <ul>
          <li>카테고리에 따라 게시글을 필터해서 보여준다.<br/>
            1. 카테고리 중에 하나만 선택 가능.<br/>
            2. 다른 카테고리가 선택되면 이전 선택은 해제.<br/>
            3. 카테고리 클릭 시 카테고리에 따라 게시글 목록 표시.<br/>
          </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">3</div>
      <div class="descBody">
        ■ 게시글 리스트 <br/>
        □ 설명
        <ul>
          <li>데이터에 따라 게시글들을 카드 형식으로 표시한다. </li>
          <li>게시들 글은 세로방향 스크롤로 표시된다. </li>
          <li>세로 스크롤에 최대 제한을 둘건지 확인 필요!! </li>
          <li>스크롤 바는 표시하지 않는다. </li>
          <li>화면 상/하 드래그 시 화면 스크롤 이동. </li>
          <li>post카드의 버튼 이외의 영역 클릭 시 해당 포스트로 이동 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">4</div>
      <div class="descBody">
        ■ 메뉴 플로터(공용) <br/>
        □ 설명
        <ul>
          <li>모든 화면에서 표시 </li>
          <li>표시하는 페이지 이동 (홈 = 게시글) </li>
          <li>홈 화면이 default (로그인 된 상태일때) </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">5</div>
      <div class="descBody">
        ■ 신규 작성 플로터(공용) <br/>
        □ 설명
        <ul>
          <li>팝업 창으로 새로운 글 작성창을 띄움 </li>
          <li>표시 화면에 따라 게시판 / 커뮤니티 추가로 변경됨 </li>
          <li>지도 / 마이페이지 에서는 해당 버튼 표시 안함 </li>
          <br>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>

---
<!----------------- 2페이지 ----------------------->

<table class="meta">
  <tr>
    <th class="label">버전(ver)</th><td class="val">1.0</td>
    <th class="label">페이지코드</th><td class="val">2</td>
    <th class="label">페이지명</th><td class="wide">post_card</td>
    <th class="label">이용자</th><td class="small">PC</td>
    <th class="descH">Description</th>
  </tr>
  <tr>
    <th class="label">작성인</th><td class="val">김경수</td>
    <th class="label">작성일</th><td class="val">2026.02.24</td>
    <th class="label">페이지 경로</th><td class="wide">-</td>
    <th class="label">페이지</th><td class="small">1</td>
    <td class="descH"> </td>
  </tr>
</table>

<div class="content">

  <div class="screen box">
    <div class="title">▼ 이어서 ▼</div>
    <div class="inner">
      <div class="imgWrap">
        <img src="ui_doc_post_card.png" alt="" class="img-800"/>
      </div>
    </div>
  </div>

  <div class="descPanel">
    <div class="head">화면 설명</div>
  

  <div class="list">
    <div class="descItem">
      <div class="descNum">1</div>
      <div class="descBody">
        ■ post img <br/>
        □ 설명
        <ul>
          <li>post 카드 이미지 </li>
          <li>url 경로 텍스트 저장하고 UI 그릴때 해당 경로의 이미지 불러와 표시한다. </li>
          <li>이미지url 없을 경우 표시하지 않음 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">2</div>
      <div class="descBody">
        ■ post 정보 <br/>
        □ 설명
        <ul>
          <li>해당 post에 대한 정보를 표시한다. <br/>
            1. 포스트 작성자 이미지 or 아이콘 표시 <br/>
            2. 포스트 작성자 이름 표시 <br/>
            3. 포스트 최초 작성일 표시 <br/>
          </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">3</div>
      <div class="descBody">
        ■ post 카테고리 <br/>
        □ 설명
        <ul>
          <li>해당 포스트가 가지는 카테고리 표시한다. </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">4</div>
      <div class="descBody">
        ■ post 제목/내용 <br/>
        □ 설명
        <ul>
          <li>post 제목은 bold로 강조 </li>
          <li>제목은 최대 20자 까지 표시 20자 넘어가면 뒷부분 ... 으로 적는다. </li>
          <li>post 내용은 2줄까지 표시 </li>
          <li>내용 표시글자 1줄에 최대 20자 까지 표시 </li>
          <li>2줄 넘어가면 나머지 텍스트는 ... 으로 표시 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">5</div>
      <div class="descBody">
        ■ post interaction 버튼 <br/>
        □ 설명
        <ul>
          1. 좋아요 버튼 - 클릭 시 좋아요 count 변경<br/>
          2. 댓글 버튼 - (결정 필요) 댓글만 입력할 인터페이스 제공할지 여부 <br/>
          3. 공유 버튼 - 팝업 창으로 공유 인터페이스 제공 <br/>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>

---
<!----------------- 3페이지 ----------------------->

<table class="meta">
  <tr>
    <th class="label">버전(ver)</th><td class="val">1.0</td>
    <th class="label">페이지코드</th><td class="val">2</td>
    <th class="label">페이지명</th><td class="wide">post_btn</td>
    <th class="label">이용자</th><td class="small">PC</td>
    <th class="descH">Description</th>
  </tr>
  <tr>
    <th class="label">작성인</th><td class="val">김경수</td>
    <th class="label">작성일</th><td class="val">2026.02.24</td>
    <th class="label">페이지 경로</th><td class="wide">-</td>
    <th class="label">페이지</th><td class="small">1</td>
    <td class="descH"> </td>
  </tr>
</table>

<div class="content">

  <div class="screen box">
    <div class="title">▼ 이어서 ▼</div>
    <div class="inner">
      <div class="imgWrap">
        <img src="ui_doc_post_btn.png" alt="" class="img-800"/>
      </div>
    </div>
  </div>

  <div class="descPanel">
    <div class="head">화면 설명</div>
  

  <div class="list">
    <div class="descItem">
      <div class="descNum">1</div>
      <div class="descBody">
        ■ post_btn_Hover <br/>
        □ 설명
        <ul>
          <li>post 카드의 버튼에 커서 Hover 시 10% 크기 키움 </li>
          <li>입력 가능한 버튼에 커서 위치하고 있는거 시인용 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">2</div>
      <div class="descBody">
        ■ post_btn_like <br/>
        □ 설명
        <ul>
          <li>default는 색상 없는 상태 </li>
          <li>사용자 별로 is_like 상태 관리 / 값이 True면 하트에 색상 표시됨 </li>
          <li>post의 is_like 값이 변경될 때 마다 숫자 증감 </li>
          <li>post의 is_like 값은 사용자 별로 1번씩만 변경 가능능 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">3</div>
      <div class="descBody">
        ■ post_btn_reply <br/>
        □ 설명
        <ul>
          <li>(검토)버튼 클릭 시 해당 포스트 화면으로 이동 </li>
          <li>포스트 이동과 겹쳐서 댓글만 달 수 있는 숏컷 제공할지 고려해야 함 </li>
        </ul>
      </div>
    </div>
  </div>

  <div class="list">
    <div class="descItem">
      <div class="descNum">4</div>
      <div class="descBody">
        ■ post_btn_linkshare <br/>
        □ 설명
        <ul>
          <li>클릭 시 공유창 호출 </li>
          <li>공유창은 해당 포스트의 URL 링크를 전달한다. </li>
          <li>전달 타겟은 공유창에서 선택 </li>
          <li>공유창은 화면 위에 올라가는 모달로 만든다.(공유창 닫기 전에는 다른 창 조작 불가) </li>
          <li>x 버튼이나 공유창 밖 영역 클릭 시 공유창 닫음 </li>
        </ul>
      </div>
    </div>
  </div>

  </div>
</div>
