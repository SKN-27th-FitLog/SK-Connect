# 모듈 
from .constants import LLM_NM, PARSER_NM, PROMPT_NM


############################################################
# constant에서 상수값 가져오기 
############################################################

# llm class 로드 
def get_llm(model_nm:str=LLM_NM.ollama.name):

    # check validation
    if model_nm not in LLM_NM.__members__:
        raise Exception("잘못된 모델명입니다.")

    return LLM_NM[model_nm].value[1]


# prompt template 로드 
def get_prompt(prompt_template_nm:str=PROMPT_NM.general.name):

    # check validation
    if prompt_template_nm not in PROMPT_NM.__members__:
        raise Exception("잘못된 프롬프트 템플릿명입니다.")

    return PROMPT_NM[prompt_template_nm].value[1]


# parser type 로드 
def get_parser(parser_type_nm:str=PARSER_NM.output_str.name):

    # check validation
    if parser_type_nm not in PARSER_NM.__members__:
        raise Exception("잘못된 파서 타입명입니다.")

    return PARSER_NM[parser_type_nm].value[1]
