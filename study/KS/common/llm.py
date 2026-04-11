from .constants import LLM_NM, PARSER_NM, PROMPT_NM

# llm class 로드 
def get_llm(model_nm:str='ollama'):

    # check validation
    if model_nm not in LLM_NM.__members__:
        raise Exception("잘못된 모델명입니다.")

    return LLM_NM[model_nm].value[1]


# prompt template 로드 
def get_prompt(prompt_template_nm:str=''):

    # check validation
    if prompt_template_nm not in PROMPT_NM.__members__:
        raise Exception("잘못된 프롬프트 템플릿명입니다.")

    return PROMPT_NM[prompt_template_nm].value[1]


# parser type 로드 
def get_parser(parser_type_nm:str='output_str'):

    # check validation
    if parser_type_nm not in PARSER_NM.__members__:
        raise Exception("잘못된 파서 타입명입니다.")

    return PARSER_NM[parser_type_nm].value[1]
