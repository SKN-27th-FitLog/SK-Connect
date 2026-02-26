# API 리스트 
---

## 1. 게시글 목록 api 
---

1.1 추천 탭 게시글 목록 업데이트
~~1.2 관심 탭 게시글 목록 업데이트~~ (1차 에자일 제외)
1.3 카테고리 탭 게시글 목록 업데이트
1.4 최신 탭 게시글 목록 업데이트

## 2. 게시글 좋아요 api
---

~~2.1 게시글 좋아요 상태 변경 (is_like = True)~~ (1차 에자일 제외)
~~2.2 게시글 좋아요 상태 변경 (is_like = False)~~ (1차 에자일 제외)

## 3. 게시글 api
---

3.1 게시글 신규 작성 
~~3.2 게시글 수정~~ (1차 에자일 제외)
~~3.3 게시글 삭제~~ (1차 에자일 제외)
3.4 특정 ID 게시글 조회 (댓글 이외)

## 4. 댓글 목록 api
---

4.1 특정 ID의 게시글 댓글 목록 업데이트
~~4.2 커뮤니티 댓글 목록 업데이트~~ (1차 에자일 제외)

## 5. 댓글 api
---

5.1 댓글 신규 작성
~~5.2 댓글 수정~~ (1차 에자일 제외)
~~5.3 댓글 삭제~~ (1차 에자일 제외)

## 6. 지도 api
---

6.1 주변 위치 게시글 마크 업데이트
6.2 게시글 마크 정보 요청



# api 상세 내용
---

## 추천 탭 게시글 목록 업데이트
1. 용도 : 
> 1.1) 홈 화면에서 추천 탭 상태에서 표시할 게시글 목록 호출
> 1.2) 홈 화면에서 추천 탭 상태에서 스크롤이 일어났을 때 갱신할 게시글 목록 호출


2. 기대결과 : 게시글 테이블을 좋아요 개수 순서로 내림차순 정렬 -> 요청한 번호 부터 100개 댓글 목록을 반환

3. api 요청 시 추가 인자
> 1. 표시할 게시글 목록 번호 

```json
{
  "post_index": 0
}
```

4. 받을 데이터 포멧 (json) -> dict 100개 리스트로 전달.
> 1. 게시글 ID : int 
> 2. 제목 (30자) : str 
> 3. 내용(120자) : str 
> 4. 이미지 Url : str 
> 5. 작성자 이름 : str 
> 6. 작성자 아이콘 : str 
> 7. 마지막 업데이트 날짜 : datetime 
> 8. 카테고리 타입 : enum 
> 9. 위치 테그 : str
> 10. 위치 좌표 : list [0,0] # json에서는 튜플이 없음음
> 9. 좋아요 개수 : int 
> 10. 좋아요 설정 여부 (is_like) : bool 
> 11. 댓글 개수 : int

```json
{
  "post_id": 12345,
  "title": "제목은 최대 30자까지",
  "content": "내용은 최대 120자까지. UI 카드/리스트에 바로 넣기 좋게 짧게 유지.",
  "image_url": "https://cdn.example.com/posts/12345/main.jpg",
  "author_name": "김경수",
  "author_icon_url": "https://cdn.example.com/users/987/avatar.png",
  "updated_at": "2026-02-26T13:45:12+09:00",
  "category": "NOTICE",
  "location_name": "대륭17차",
  "location": [234234,344954],
  "like_count": 27,
  "is_like": true,
  "comment_count": 4
}
```

---

## 카테고리 탭 게시글 목록 업데이트
1. 용도 : 
> 1.1) 홈 화면에서 카테고리 탭 -> 특정 카테고리 선택한 상태에서 표시할 게시글 목록 호출
> 1.2) 홈 화면에서 카테고리 탭 -> 특정 카테고리 선택한 상태에서 스크롤이 일어났을 때 갱신할 게시글 목록 호출


2. 기대결과 : 게시글 테이블에서 특정 타입의 게시글만 필터한 뒤 좋아요 개수 순서로 내림차순 정렬 -> 요청한 번호 부터 100개 댓글 목록을 반환

3. api 요청 시 추가 인자
> 1. 표시할 게시글 목록 번호 

```json
{
  "post_index": 0,
  "category": "NOTICE"
}
```

4. 받을 데이터 포멧 (json) -> dict 100개 리스트로 전달.
> 1. 게시글 ID : int 
> 2. 제목 (30자) : str 
> 3. 내용(120자) : str 
> 4. 이미지 Url : str 
> 5. 작성자 이름 : str 
> 6. 작성자 아이콘 : str 
> 7. 마지막 업데이트 날짜 : datetime 
> 8. 카테고리 타입 : enum 
> 9. 위치 테그 : str
> 10. 위치 좌표 : list [0,0] # json에서는 튜플이 없음음
> 9. 좋아요 개수 : int 
> 10. 좋아요 설정 여부 (is_like) : bool 
> 11. 댓글 개수 : int

```json
{
  "post_id": 12345,
  "title": "제목은 최대 30자까지",
  "content": "내용은 최대 120자까지. UI 카드/리스트에 바로 넣기 좋게 짧게 유지.",
  "image_url": "https://cdn.example.com/posts/12345/main.jpg",
  "author_name": "김경수",
  "author_icon_url": "https://cdn.example.com/users/987/avatar.png",
  "updated_at": "2026-02-26T13:45:12+09:00",
  "category": "NOTICE",
  "location_name": "대륭17차",
  "location": [234234,344954],
  "like_count": 27,
  "is_like": true,
  "comment_count": 4
}
```

---

## 최신 탭 게시글 목록 업데이트
1. 용도 : 
> 1.1) 홈 화면에서 최신 탭 에서 표시할 게시글 목록 호출
> 1.2) 홈 화면에서 최신 탭 에서 스크롤이 일어났을 때 갱신할 게시글 목록 호출


2. 기대결과 : 게시글 테이블에서 수정된 날짜 순서로 내림차순 정렬 -> 요청한 번호 부터 100개 댓글 목록을 반환

3. api 요청 시 추가 인자
> 1. 표시할 게시글 목록 번호 

```json
{
  "post_index": 0
}
```

4. 받을 데이터 포멧 (json) -> dict 100개 리스트로 전달.
> 1. 게시글 ID : int 
> 2. 제목 (30자) : str 
> 3. 내용(120자) : str 
> 4. 이미지 Url : str 
> 5. 작성자 이름 : str 
> 6. 작성자 아이콘 : str 
> 7. 마지막 업데이트 날짜 : datetime 
> 8. 카테고리 타입 : enum 
> 9. 위치 테그 : str
> 10. 위치 좌표 : list [0,0] # json에서는 튜플이 없음음
> 9. 좋아요 개수 : int 
> 10. 좋아요 설정 여부 (is_like) : bool 
> 11. 댓글 개수 : int

```json
{
  "post_id": 12345,
  "title": "제목은 최대 30자까지",
  "content": "내용은 최대 120자까지. UI 카드/리스트에 바로 넣기 좋게 짧게 유지.",
  "image_url": "https://cdn.example.com/posts/12345/main.jpg",
  "author_name": "김경수",
  "author_icon_url": "https://cdn.example.com/users/987/avatar.png",
  "updated_at": "2026-02-26T13:45:12+09:00",
  "category": "NOTICE",
  "location_name": "대륭17차",
  "location": [234234,344954],
  "like_count": 27,
  "is_like": true,
  "comment_count": 4
}
```

---

## 게시글 신규 작성 
1. 용도 : 
> 1.1) 클라이언트에서 내용 채워서 전달하면 전달받은 내용으로 게시글 신규 추가


2. 기대결과 : 
> 2.1) 게시글 신규 추가 요청 -> 전달받은 게시글 DB에 추가 (실행으로 끝 -> 회신 없음)
> 2.2) 게시글 등록 시 작성날짜는 현재 시간으로
> 2.3) 게시글 등록 시 수정일자는 현재 시간으로

3. api 요청 시 추가 인자
> 1. 제목 (50자) : str 
> 2. 내용 (500자) : str
> 3. 이미지 Url : str 
> 4. 작성자 이름 : str 
> 5. 작성자 아이콘 : str 
> 6. 카테고리 타입 : enum 
> 7. 위치 테그 : str
> 8. 위치 좌표 : list [0,0]

```json
{
  "title": "제목은 최대 50자까지",
  "content": "내용은 최대 500자까지.",
  "image_url": "https://cdn.example.com/posts/12345/main.jpg",  
  "author_name": "김경수",
  "author_icon_url": "https://cdn.example.com/users/987/avatar.png",
  "category": "NOTICE",
  "location_name": "대륭17차",
  "location": [234234,344954],
}
```

4. 받을 데이터 포멧 (json) -> 없음

```json

```

---

## 특정 ID 게시글 조회 (댓글 이외 정보 업데이트)
1. 용도 : 
> 1.1) 클라이언트에서 특정 ID의 게시글의 상세정보 확인을 위해 조회 요청


2. 기대결과 : 
> 2.1) 특정ID의 게시글에 대한 정보 조회 요청 -> 전달받은 ID의 게시글 정보 회신
> 2.2) 댓글은 별도 업데이트로 따로 호출함 (데이터 량도 달라서 분리 -> 다만 게시글 오픈 시 api를 2번 보내는게 괜찮은지는 모르겠음)

3. api 요청 시 추가 인자
> 1. 게시글 ID : int 


4. 받을 데이터 포멧 (json) -> 지정한 dict 1개 전달.
> 1. 게시글 ID : int 
> 2. 제목 (30자) : str 
> 3. 내용(120자) : str 
> 4. 이미지 Url : str 
> 5. 작성자 이름 : str 
> 6. 작성자 아이콘 : str 
> 7. 마지막 업데이트 날짜 : datetime 
> 8. 카테고리 타입 : enum 
> 9. 위치 테그 : str
> 10. 위치 좌표 : list [0,0] # json에서는 튜플이 없음음
> 9. 좋아요 개수 : int 
> 10. 좋아요 설정 여부 (is_like) : bool 
> 11. 댓글 개수 : int

```json
{
  "post_id": 12345,
  "title": "제목은 최대 30자까지",
  "content": "내용은 최대 120자까지. UI 카드/리스트에 바로 넣기 좋게 짧게 유지.",
  "image_url": "https://cdn.example.com/posts/12345/main.jpg",
  "author_name": "김경수",
  "author_icon_url": "https://cdn.example.com/users/987/avatar.png",
  "updated_at": "2026-02-26T13:45:12+09:00",
  "category": "NOTICE",
  "location_name": "대륭17차",
  "location": [234234,344954],
  "like_count": 27,
  "is_like": true,
  "comment_count": 4
}
```

---

## 특정 ID의 게시글 댓글 목록 업데이트
1. 용도 : 
> 1.1) 클라이언트에서 특정 ID의 게시글의 댓글 목록 업데이트를 위해 요청 


2. 기대결과 : 
> 2.1) 특정ID의 게시글에 대한 댓글 목록 조회 요청 -> 전달받은 ID의 게시글 댓글 목록 회신

3. api 요청 시 추가 인자
> 1. 게시글 ID : int 
> 2. 표시할 댓글 index : int


4. 받을 데이터 포멧 (json) -> 수정한 날짜 내림차순 정렬 한 다음 index 부터 추가 100번 째 까지 지정한 dict 100개 전달.
> 1. 댓글 ID : int 
> 2. 댓글 제목 (50자) : str 
> 3. 댓글 내용(500자) : str 
> 4. 작성자 이름 : str 
> 5. 작성자 아이콘 : str 
> 6. 마지막 업데이트 날짜 : datetime 

```json
{
  "comment_id": 1001,
  "title": "제목은 최대 50자까지",
  "content": "내용은 최대 500자까지",
  "author_name": "이철수",
  "author_icon_url": "https://cdn.example.com/users/111/avatar.png",
  "updated_at": "2026-02-26T14:01:10+09:00"
}
```

---


## 댓글 신규 작성
1. 용도 : 
> 1.1) 클라이언트에서 특정 ID의 게시글의 댓글 추가 요청 


2. 기대결과 : 
> 2.1) 특정ID의 게시글에 대한 댓글 목록 추가 요청 

3. api 요청 시 추가 인자
> 1. 게시글 ID : int 
> 2. 표시할 댓글 제목 : str(50자 까지)
> 2. 표시할 댓글 내용 : str(500자 까지)


4. 받을 데이터 포멧 (json) -> 수정한 날짜 내림차순 정렬 한 다음 index 부터 추가 100번 째 까지 지정한 dict 100개 전달.
> 1. 댓글 ID : int 
> 2. 댓글 제목 (50자) : str 
> 3. 댓글 내용(500자) : str 
> 4. 작성자 이름 : str 
> 5. 작성자 아이콘 : str 
> 6. 마지막 업데이트 날짜 : datetime 

```json
{
  "comment_id": 1001,
  "title": "제목은 최대 50자까지",
  "content": "내용은 최대 500자까지",
  "author_name": "이철수",
  "author_icon_url": "https://cdn.example.com/users/111/avatar.png",
  "updated_at": "2026-02-26T14:01:10+09:00"
}
```

## 주변 위치 게시글 마크 업데이트
1. 용도 : 
> 1.1) 지도에서 화면 중앙 기준 일정 반경 내 게시글 위치 마커 요청
> 1.2) 주변것만 표시 -> 화면 이동 시 동적 로딩
> 1.3) 마커 표시만 따로 요청하고 마커 클릭 시는 이벤트 분리 (지도 표시 용인데 제목이나 내용 같은 정보는 필요 없음)



2. 기대결과 : 
> 2.1) 특정ID의 게시글에 대한 댓글 목록 조회 요청 -> 전달받은 ID의 게시글 댓글 목록 회신

3. api 요청 시 추가 인자
> 1. 게시글 ID : int 
> 2. 표시할 댓글 index : int


4. 받을 데이터 포멧 (json) -> 수정한 날짜 내림차순 정렬 한 다음 index 부터 추가 100번 째 까지 지정한 dict 100개 전달.
> 1. 댓글 ID : int 
> 2. 댓글 제목 (50자) : str 
> 3. 댓글 내용(500자) : str 
> 4. 작성자 이름 : str 
> 5. 작성자 아이콘 : str 
> 6. 마지막 업데이트 날짜 : datetime 

```json
{
  "comment_id": 1001,
  "title": "제목은 최대 50자까지",
  "content": "내용은 최대 500자까지",
  "author_name": "이철수",
  "author_icon_url": "https://cdn.example.com/users/111/avatar.png",
  "updated_at": "2026-02-26T14:01:10+09:00"
}
```

## 게시글 마크 정보 요청
1. 용도 : 
> 1.1) 클라이언트에서 특정 ID의 게시글의 댓글 목록 업데이트를 위해 요청 


2. 기대결과 : 
> 2.1) 특정ID의 게시글에 대한 댓글 목록 조회 요청 -> 전달받은 ID의 게시글 댓글 목록 회신

3. api 요청 시 추가 인자
> 1. 게시글 ID : int 
> 2. 표시할 댓글 index : int


4. 받을 데이터 포멧 (json) -> 수정한 날짜 내림차순 정렬 한 다음 index 부터 추가 100번 째 까지 지정한 dict 100개 전달.
> 1. 댓글 ID : int 
> 2. 댓글 제목 (50자) : str 
> 3. 댓글 내용(500자) : str 
> 4. 작성자 이름 : str 
> 5. 작성자 아이콘 : str 
> 6. 마지막 업데이트 날짜 : datetime 

```json
{
  "comment_id": 1001,
  "title": "제목은 최대 50자까지",
  "content": "내용은 최대 500자까지",
  "author_name": "이철수",
  "author_icon_url": "https://cdn.example.com/users/111/avatar.png",
  "updated_at": "2026-02-26T14:01:10+09:00"
}
```