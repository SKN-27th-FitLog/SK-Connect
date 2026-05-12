from src.core.policy.reason_code import ReasonCode
from src.core.policy.resolver import Action, PolicyResolver


def test_recipe_menu_reason_codes_are_defined():
    assert ReasonCode.AMBIGUOUS_MENU_NAME.value == "AMBIGUOUS_MENU_NAME"
    assert ReasonCode.LOW_CONFIDENCE_MENU_NORMALIZATION.value == "LOW_CONFIDENCE_MENU_NORMALIZATION"
    assert ReasonCode.REVIEW_CANDIDATE_MENU_NORMALIZATION.value == "REVIEW_CANDIDATE_MENU_NORMALIZATION"
    assert ReasonCode.RECIPE_SEARCH_EMPTY.value == "RECIPE_SEARCH_EMPTY"
    assert ReasonCode.RECIPE_SELECTOR_MISMATCH.value == "RECIPE_SELECTOR_MISMATCH"
    assert ReasonCode.INGREDIENT_PARSE_FAILED.value == "INGREDIENT_PARSE_FAILED"
    assert ReasonCode.INGREDIENT_NORMALIZATION_FAILED.value == "INGREDIENT_NORMALIZATION_FAILED"
    assert ReasonCode.KAG_GRAPH_BUILD_FAILED.value == "KAG_GRAPH_BUILD_FAILED"


def test_recipe_menu_reason_codes_map_to_resolver_actions():
    resolver = PolicyResolver()

    assert resolver.resolve(ReasonCode.AMBIGUOUS_MENU_NAME.value, "validation_normalization") == Action.WARN
    assert resolver.resolve(ReasonCode.LOW_CONFIDENCE_MENU_NORMALIZATION.value, "validation_normalization") == Action.WARN
    assert resolver.resolve(ReasonCode.REVIEW_CANDIDATE_MENU_NORMALIZATION.value, "validation_normalization") == Action.WARN
    assert resolver.resolve(ReasonCode.RECIPE_SEARCH_EMPTY.value, "raw_collection") == Action.WARN
    assert resolver.resolve(ReasonCode.RECIPE_SELECTOR_MISMATCH.value, "candidate_parsing") == Action.REPROCESS
    assert resolver.resolve(ReasonCode.INGREDIENT_PARSE_FAILED.value, "candidate_parsing") == Action.REPROCESS
    assert resolver.resolve(ReasonCode.INGREDIENT_NORMALIZATION_FAILED.value, "validation_normalization") == Action.REPROCESS
    assert resolver.resolve(ReasonCode.KAG_GRAPH_BUILD_FAILED.value, "load") == Action.REPROCESS
