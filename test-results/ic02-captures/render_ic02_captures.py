from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(r"C:\dev\Project\SK-Connect\test-results\ic02-captures")
ROOT = Path(r"C:\dev\Project\SK-Connect")
OUT.mkdir(parents=True, exist_ok=True)


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


F_TITLE = load_font(r"C:\Windows\Fonts\malgunbd.ttf", 34)
F_H2 = load_font(r"C:\Windows\Fonts\malgunbd.ttf", 24)
F_BODY = load_font(r"C:\Windows\Fonts\malgun.ttf", 20)
F_SMALL = load_font(r"C:\Windows\Fonts\malgun.ttf", 17)
F_MONO = load_font(r"C:\Windows\Fonts\malgun.ttf", 17)
F_MONO_SMALL = load_font(r"C:\Windows\Fonts\malgun.ttf", 14)

COLORS = {
    "bg": "#f6f7f9",
    "panel": "#ffffff",
    "ink": "#17202a",
    "muted": "#5d6d7e",
    "line": "#d7dde5",
    "blue": "#1f77b4",
    "green": "#1e8e5a",
    "amber": "#9a6700",
    "code_bg": "#101418",
    "code_fg": "#e8edf2",
}


def rounded(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], radius: int = 14,
            fill: str = "#fff", outline: str = "#d7dde5", width: int = 1) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str,
         fill: str | None = None, font_obj: ImageFont.ImageFont | None = None) -> None:
    draw.text(xy, value, fill=fill or COLORS["ink"], font=font_obj or F_BODY)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int],
          color: str = "#74808c") -> None:
    draw.line([start, end], fill=color, width=3)
    x1, y1 = start
    x2, y2 = end
    if abs(x2 - x1) >= abs(y2 - y1):
        sign = 1 if x2 >= x1 else -1
        points = [(x2, y2), (x2 - sign * 12, y2 - 7), (x2 - sign * 12, y2 + 7)]
    else:
        sign = 1 if y2 >= y1 else -1
        points = [(x2, y2), (x2 - 7, y2 - sign * 12), (x2 + 7, y2 - sign * 12)]
    draw.polygon(points, fill=color)


def render_flow() -> Path:
    img = Image.new("RGB", (1600, 1050), COLORS["bg"])
    draw = ImageDraw.Draw(img)
    text(draw, (60, 42), "IC02 실제 처리 흐름: 무엇을 보고, 어떻게 저장하는가", font_obj=F_TITLE)
    text(draw, (60, 88), "DB 변경 없이 현재 코드 기준 dry-run으로 확인한 저장 형태", fill=COLORS["muted"], font_obj=F_BODY)

    rounded(draw, (60, 140, 510, 430), fill=COLORS["panel"])
    text(draw, (90, 166), "1. 대상 row 조회", font_obj=F_H2, fill=COLORS["blue"])
    sql_lines = [
        "FROM analysis AS a",
        "WHERE information_cd = 'IC02'",
        "AND title/content 중 하나 유효",
        "AND (sentimental 비어있음 OR score IS NULL)",
        "SELECT crawling_id, title, content,",
        "       keywords, information_cd,",
        "       sentimental, score",
    ]
    y = 205
    for line in sql_lines:
        text(draw, (90, y), line, font_obj=F_MONO, fill=COLORS["ink"])
        y += 28

    rounded(draw, (575, 140, 1030, 430), fill=COLORS["panel"])
    text(draw, (605, 166), "2. row 처리에서 보는 값", font_obj=F_H2, fill=COLORS["blue"])
    items = [
        ("회사 매칭", "title + content"),
        ("감성 분석", "title only"),
        ("사용 사전", "OpenAI, Anthropic, Google,\nMicrosoft, Apple, NVIDIA, Samsung"),
        ("외부 LLM", "사용 안 함"),
    ]
    y = 210
    for label, value in items:
        text(draw, (605, y), label, font_obj=F_BODY, fill=COLORS["ink"])
        value_lines = value.split("\n")
        text(draw, (735, y), f"→ {value_lines[0]}", font_obj=F_BODY, fill=COLORS["muted"])
        if len(value_lines) > 1:
            text(draw, (755, y + 28), value_lines[1], font_obj=F_BODY, fill=COLORS["muted"])
            y += 66
        else:
            y += 44

    rounded(draw, (1095, 140, 1540, 430), fill=COLORS["panel"])
    text(draw, (1125, 166), "3. merge payload", font_obj=F_H2, fill=COLORS["green"])
    payload = """{
  crawling_id: 101,
  keywords: '#OpenAI#ai_company#NVIDIA#'
            'semiconductor',
  sentimental: 'positive',
  score: 0.91
}"""
    rounded(draw, (1125, 205, 1510, 390), radius=8, fill=COLORS["code_bg"], outline=COLORS["code_bg"])
    y = 225
    for line in payload.split("\n"):
        text(draw, (1145, y), line, font_obj=F_MONO_SMALL, fill=COLORS["code_fg"])
        y += 27

    arrow(draw, (510, 285), (575, 285))
    arrow(draw, (1030, 285), (1095, 285))

    rounded(draw, (60, 500, 1540, 840), fill=COLORS["panel"])
    text(draw, (90, 526), "Dry-run 샘플", font_obj=F_H2, fill=COLORS["ink"])
    rows = [
        ("title", "OpenAI updates ChatGPT with NVIDIA GPU support"),
        ("content", "ChatGPT 개발사와 NVIDIA가 AI 인프라를 확장했다."),
        ("회사 매칭 결과", "OpenAI(ai_company), NVIDIA(semiconductor)"),
        ("감성 입력", "title 전체 문장"),
        ("저장 keywords", "#OpenAI#ai_company#NVIDIA#semiconductor"),
        ("저장 sentimental / score", "positive / 0.91"),
    ]
    x0, y0 = 90, 575
    col1, col2 = 260, 1120
    draw.rectangle((x0, y0, x0 + col1 + col2, y0 + 42), fill="#edf3fa")
    text(draw, (x0 + 16, y0 + 10), "컬럼/단계", font_obj=F_BODY)
    text(draw, (x0 + col1 + 16, y0 + 10), "값", font_obj=F_BODY)
    y = y0 + 42
    for index, (label, value) in enumerate(rows):
        fill = "#ffffff" if index % 2 == 0 else "#fbfcfd"
        draw.rectangle((x0, y, x0 + col1 + col2, y + 42), fill=fill, outline=COLORS["line"])
        text(draw, (x0 + 16, y + 10), label, font_obj=F_SMALL, fill=COLORS["ink"])
        text(draw, (x0 + col1 + 16, y + 10), value, font_obj=F_SMALL, fill=COLORS["ink"])
        y += 42

    rounded(draw, (60, 885, 1540, 990), fill="#fff8e8", outline="#f1d391")
    text(draw, (90, 912), "로그 정책", font_obj=F_H2, fill=COLORS["amber"])
    text(draw, (90, 950), "정상 진행/성공/summary INFO 로그는 남기지 않음. row 처리 실패 시 logger.exception 으로 원인만 기록.",
         font_obj=F_BODY, fill=COLORS["ink"])

    output = OUT / "sk-connect-ic02-storage-flow.png"
    img.save(output)
    return output


def render_code_points() -> Path:
    img = Image.new("RGB", (1600, 1200), COLORS["bg"])
    draw = ImageDraw.Draw(img)
    text(draw, (60, 42), "IC02 실제 코드 위치 캡쳐", font_obj=F_TITLE)
    text(draw, (60, 88), "조회 조건, row 처리, 저장 payload가 들어있는 실제 파일/라인", fill=COLORS["muted"], font_obj=F_BODY)

    snippets = [
        ("조회 조건", ROOT / "ai/post_analysis/postgresql/run_query.py", 132, 156),
        ("row에서 보는 값", ROOT / "ai/post_analysis/analyze_it_keywords.py", 84, 101),
        ("저장 payload + merge", ROOT / "ai/post_analysis/analyze_it_keywords.py", 150, 190),
        ("회사 사전", ROOT / "ai/post_analysis/common/it_company_registry.py", 18, 25),
    ]
    positions = [(60, 140, 770, 520), (830, 140, 1540, 520), (60, 570, 770, 1120), (830, 570, 1540, 1120)]
    for (title, path, start, end), box in zip(snippets, positions):
        x1, y1, x2, y2 = box
        rounded(draw, box, fill=COLORS["panel"])
        text(draw, (x1 + 24, y1 + 20), title, font_obj=F_H2, fill=COLORS["blue"])
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        text(draw, (x1 + 24, y1 + 54), f"{rel}:{start}", font_obj=F_SMALL, fill=COLORS["muted"])
        rounded(draw, (x1 + 24, y1 + 86, x2 - 24, y2 - 24), radius=8, fill=COLORS["code_bg"], outline=COLORS["code_bg"])
        lines = path.read_text(encoding="utf-8").splitlines()
        yy = y1 + 104
        for lineno in range(start, min(end, len(lines)) + 1):
            raw = lines[lineno - 1]
            if len(raw) > 74:
                raw = raw[:71] + "..."
            line = f"{lineno:>3}  {raw}"
            color = "#d7f7d0" if any(
                token in raw for token in [
                    "sentimental", "score", "keywords", "title", "content",
                    "merge_analysis_data", "match_it_companies", "predict_sentiment",
                ]
            ) else COLORS["code_fg"]
            text(draw, (x1 + 42, yy), line, font_obj=F_MONO_SMALL, fill=color)
            yy += 22
            if yy > y2 - 46:
                break

    output = OUT / "sk-connect-ic02-code-points.png"
    img.save(output)
    return output


if __name__ == "__main__":
    print(render_flow())
    print(render_code_points())
