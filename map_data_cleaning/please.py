import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# =========================
# 설정
# =========================
INPUT_CSV = "input.csv"          # 원본 CSV
OUTPUT_CSV = "output.csv"        # 결과 CSV
FAILED_CSV = "failed.csv"        # 실패 주소 CSV
SITE_URL = "https://www.findlatlng.org/"
ADDRESS_COLUMN = "주소"

# 크롬드라이버를 직접 지정해야 하면 아래 주석 해제
# CHROMEDRIVER_PATH = r"C:\path\to\chromedriver.exe"

# =========================
# 브라우저 실행
# =========================
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

# service = Service(CHROMEDRIVER_PATH)
# driver = webdriver.Chrome(service=service, options=options)
driver = webdriver.Chrome(options=options)

wait = WebDriverWait(driver, 15)

# =========================
# 유틸 함수
# =========================
def clean_address(addr):
    """주소 정제: 너무 긴 부가정보를 조금 줄여서 검색 성공률 보정"""
    if pd.isna(addr):
        return ""
    addr = str(addr).strip()

    # 자주 검색 실패를 만드는 꼬리 정보 제거
    remove_tokens = ["(", "층", "호", "동 ", "센터", "빌딩", "건물"]
    for token in remove_tokens:
        if token in addr:
            # 괄호는 앞부분만 쓰기
            if token == "(":
                addr = addr.split("(")[0].strip()

    return addr.strip()


def find_search_input():
    """
    사이트 구조가 조금 바뀌어도 최대한 찾도록 여러 방식 시도
    """
    candidates = [
        (By.CSS_SELECTOR, "input[type='search']"),
        (By.CSS_SELECTOR, "input[placeholder*='주소']"),
        (By.CSS_SELECTOR, "input[aria-label*='주소']"),
        (By.XPATH, "//input[contains(@placeholder, '주소')]"),
        (By.XPATH, "//input[contains(@aria-label, '주소')]"),
        (By.XPATH, "//input[@type='text']"),
    ]

    for by, selector in candidates:
        try:
            elem = wait.until(EC.presence_of_element_located((by, selector)))
            if elem.is_displayed():
                return elem
        except Exception:
            continue

    raise NoSuchElementException("주소 입력창을 찾지 못했습니다.")


def click_search_if_possible():
    """
    검색 버튼이 있으면 클릭, 없으면 엔터 입력으로 대체
    """
    candidates = [
        (By.XPATH, "//button[contains(., 'Search')]"),
        (By.XPATH, "//button[contains(., '검색')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "input[type='submit']"),
    ]

    for by, selector in candidates:
        try:
            btn = driver.find_element(by, selector)
            if btn.is_displayed() and btn.is_enabled():
                btn.click()
                return True
        except Exception:
            continue
    return False


def get_value_near_label(label_text):
    """
    '위도 (Latitude)', '경도 (Longitude)' 같은 라벨 주변 텍스트를 읽어오려는 함수
    사이트 구조가 고정되지 않아 여러 XPath를 시도함
    """
    xpaths = [
        f"//*[contains(normalize-space(), '{label_text}')]/following::*[1]",
        f"//*[contains(normalize-space(), '{label_text}')]/following-sibling::*[1]",
        f"//*[contains(normalize-space(), '{label_text}')]/parent::*/following-sibling::*[1]",
    ]

    for xp in xpaths:
        try:
            elem = driver.find_element(By.XPATH, xp)
            text = elem.text.strip()
            if text and text != "—":
                return text
        except Exception:
            pass
    return ""


def extract_lat_lng():
    """
    결과 영역에서 위도/경도를 추출
    """
    # 결과가 로드될 때까지 잠깐 대기
    time.sleep(2)

    lat = get_value_near_label("위도")
    lng = get_value_near_label("경도")

    # 혹시 라벨 기반 추출이 실패하면 페이지 전체에서 숫자 패턴을 보조적으로 찾는 방식 추가 가능
    return lat, lng


def search_one_address(addr):
    driver.get(SITE_URL)

    # 페이지 로딩
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # 입력창 찾기
    input_box = find_search_input()
    input_box.clear()
    input_box.send_keys(addr)

    # 버튼 클릭 또는 엔터
    clicked = click_search_if_possible()
    if not clicked:
        input_box.send_keys(Keys.ENTER)

    # 결과 추출
    lat, lng = extract_lat_lng()
    return lat, lng


# =========================
# CSV 처리
# =========================
df = pd.read_csv(INPUT_CSV)

if ADDRESS_COLUMN not in df.columns:
    driver.quit()
    raise ValueError(f'CSV에 "{ADDRESS_COLUMN}" 컬럼이 없습니다.')

if "위도" not in df.columns:
    df["위도"] = ""
if "경도" not in df.columns:
    df["경도"] = ""

failed_rows = []

try:
    for idx, row in df.iterrows():
        raw_addr = row[ADDRESS_COLUMN]
        raw_addr = "" if pd.isna(raw_addr) else str(raw_addr).strip()

        if not raw_addr:
            print(f"[{idx}] 빈 주소")
            failed_rows.append({"index": idx, "주소": raw_addr, "사유": "빈 주소"})
            continue

        print(f"[{idx}] 검색 시작: {raw_addr}")

        # 1차: 원본 주소
        try:
            lat, lng = search_one_address(raw_addr)
        except TimeoutException:
            lat, lng = "", ""

        # 2차: 정제 주소
        if not lat or not lng:
            refined = clean_address(raw_addr)
            if refined and refined != raw_addr:
                print(f"  └ 정제 재시도: {refined}")
                try:
                    lat, lng = search_one_address(refined)
                except TimeoutException:
                    lat, lng = "", ""

        if lat and lng:
            df.at[idx, "위도"] = lat
            df.at[idx, "경도"] = lng
            print(f"  성공 -> 위도: {lat}, 경도: {lng}")
        else:
            failed_rows.append({"index": idx, "주소": raw_addr, "사유": "좌표 추출 실패"})
            print("  실패 -> 좌표를 읽지 못함")

        # 너무 빠른 반복 방지
        time.sleep(1)

finally:
    driver.quit()

# 결과 저장
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

if failed_rows:
    failed_df = pd.DataFrame(failed_rows)
    failed_df.to_csv(FAILED_CSV, index=False, encoding="utf-8-sig")
    print(f"\n완료: {OUTPUT_CSV} 저장")
    print(f"실패 목록: {FAILED_CSV} 저장")
else:
    print(f"\n완료: {OUTPUT_CSV} 저장 (실패 없음)")