import pandas as pd


def main():

    analysis = pd.read_csv("analysis.csv")
    analysis_sentimental = pd.read_csv("analysis_sentimental.csv")
    analysis_keywords = pd.read_csv("analysis_keywords.csv")
    analysis_keywords_classified = pd.read_csv("analysis_keywords_classified.csv")

    df = pd.DataFrame(analysis)
    df_sentimental = pd.DataFrame(analysis_sentimental)
    df_keywords = pd.DataFrame(analysis_keywords)
    df_keywords_classified = pd.DataFrame(analysis_keywords_classified)

    df["sentimental"] = df_sentimental["sentimental"]
    df["score"] = df_sentimental["score"]
    df["keywords"] = df_keywords["keywords"]
    df["positive_kw"] = df_keywords_classified["positive_kw"]
    df["negative_kw"] = df_keywords_classified["negative_kw"]

    # 가져온 데이터 수정
    df["positive_kw"].map(lambda x: x.replace("\"",""))
    df["negative_kw"].map(lambda x: x.replace("\"",""))

    
    
    df.to_csv("analysis_all.csv", index=False)

if __name__ == "__main__":
    main()