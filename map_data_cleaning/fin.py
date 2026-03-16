import pandas as pd
import re

INPUT_CSV = "input.csv"
OUTPUT_CSV = "cleaned.csv"

df = pd.read_csv(INPUT_CSV, dtype={"위도": "string", "경도": "string"})

def is_blank(v):
    return pd.isna(v) or str(v).strip() == ""

def extract_number(text, label):
    """
    text에서 '위도:숫자' 또는 '경도:숫자' 형태의 숫자만 추출
    """
    if pd.isna(text):
        return None

    text = str(text).strip()

    # 예: 위도:37479123 / 경도:126879123 / 위도 37.479123
    pattern = rf"{label}[:\s]*([0-9.]+)"
    m = re.search(pattern, text)
    if m:
        return m.group(1)

    # 혹시 텍스트 없이 숫자만 있으면 그대로 반환
    if re.fullmatch(r"[0-9.]+", text):
        return text

    return None

def fix_lat(num_str):
    """
    위도는 XX.XXXXXX 형태로 맞춤
    """
    if num_str is None:
        return None

    num_str = str(num_str).strip()

    # 이미 정상 소수 형식이면 그대로
    if "." in num_str:
        int_part, frac_part = num_str.split(".", 1)
        if len(int_part) == 2:
            return f"{int_part}.{frac_part}"
        elif len(int_part) > 2:
            # 혹시 점 위치가 잘못되었으면 앞 2자리 기준으로 재배치
            raw = int_part + frac_part
            return f"{raw[:2]}.{raw[2:]}"
        else:
            return num_str

    # 점이 없으면 앞 2자리 뒤에 삽입
    if len(num_str) > 2:
        return f"{num_str[:2]}.{num_str[2:]}"
    return num_str

def fix_lng(num_str):
    """
    경도는 XXX.XXXXXX 형태로 맞춤
    """
    if num_str is None:
        return None

    num_str = str(num_str).strip()

    # 이미 소수점이 있어도 정수부 길이가 3이 아니면 재배치
    if "." in num_str:
        int_part, frac_part = num_str.split(".", 1)
        raw = int_part + frac_part

        if len(int_part) == 3:
            return f"{int_part}.{frac_part}"
        elif len(raw) > 3:
            return f"{raw[:3]}.{raw[3:]}"
        else:
            return num_str

    # 점이 없으면 앞 3자리 뒤에 삽입
    if len(num_str) > 3:
        return f"{num_str[:3]}.{num_str[3:]}"
    return num_str

for i, row in df.iterrows():
    lat_val = row.get("위도")
    lng_val = row.get("경도")

    # -----------------
    # 위도 정리
    # -----------------
    if not is_blank(lat_val):
        lat_num = extract_number(lat_val, "위도")
        if lat_num is not None:
            df.at[i, "위도"] = fix_lat(lat_num)

    # -----------------
    # 경도 정리
    # -----------------
    if not is_blank(lng_val):
        lng_num = extract_number(lng_val, "경도")
        if lng_num is not None:
            df.at[i, "경도"] = fix_lng(lng_num)

    # -----------------
    # 위도 칸 안에 경도까지 같이 들어있고
    # 경도 칸이 비어있는 경우 보완
    # -----------------
    if not is_blank(lat_val) and is_blank(lng_val):
        lng_from_lat = extract_number(lat_val, "경도")
        if lng_from_lat is not None:
            df.at[i, "경도"] = fix_lng(lng_from_lat)

# 숫자형 변환
df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
df["경도"] = pd.to_numeric(df["경도"], errors="coerce")

df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
print(f"완료 -> {OUTPUT_CSV}")