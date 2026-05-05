# 로그 
import logging
logging.basicConfig(level=logging.INFO)

# 패키지
import pandas as pd
from kiwipiepy import Kiwi

#########################################

def main():

    # 형태소 분석기
    kiwi = Kiwi()

    # 데이터 로드 
    data = pd.read_csv("analysis.csv")
    df = pd.DataFrame(data)
    # 빈 칸만 있으면 keywords 열이 float64로 잡혀 문자열 대입 시 오류가 난다.
    df["keywords"] = df["keywords"].astype("object")

    # 데이터에서 content 컬럼 값을 가져와서 row 별로 형태소 분석 진행한 뒤 keywords 컬럼에 적용한다. 
    for index, row in df.iterrows():
        text = row["content"]
        tokens = kiwi.analyze(text)[0][0]
        keywords = [
            token.form
            for token in tokens
            if token.tag.startswith("N") or token.tag.startswith("V") or token.tag.startswith("VA")
        ]

        df.at[index, "keywords"] = "#".join(keywords)
        print(keywords)

    df.to_csv("analysis_keywords.csv", index=False)
    
    print("완료")



########################################################
if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    main() 