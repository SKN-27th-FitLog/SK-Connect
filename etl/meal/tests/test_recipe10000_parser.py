from src.services.parsers.recipe10000_parser import Recipe10000Parser


def test_recipe10000_parser_extracts_only_main_ingredient_names():
    html = """
    <div class="ready_ingre3" id="divConfirmedMaterialArea">
      <ul>
        <b class="ready_ingre3_tt">[재료]</b>
        <li>
          <div class="ingre_list_name">돼지고기 앞다리살</div>
          <span class="ingre_list_ea">600g</span>
        </li>
        <li>
          <div class="ingre_list_name">양파</div>
          <span class="ingre_list_ea">1/2개</span>
        </li>
      </ul>
    </div>
    """

    ingredients = Recipe10000Parser().parse_ingredients(html)

    assert ingredients == [
        {"ingredient_name": "돼지고기 앞다리살"},
        {"ingredient_name": "양파"},
    ]


def test_recipe10000_parser_removes_quantity_when_name_text_contains_it():
    html = """
    <div id="divConfirmedMaterialArea">
      <li><div class="ingre_list_name">대파 1대</div></li>
      <li><div class="ingre_list_name">고춧가루 2큰술</div></li>
      <li><div class="ingre_list_name">물 약간</div></li>
    </div>
    """

    ingredients = Recipe10000Parser().parse_ingredients(html)

    assert ingredients == [
        {"ingredient_name": "대파"},
        {"ingredient_name": "고춧가루"},
        {"ingredient_name": "물"},
    ]


def test_recipe10000_parser_deduplicates_ingredient_names():
    html = """
    <div id="divConfirmedMaterialArea">
      <li><div class="ingre_list_name">양파</div></li>
      <li><div class="ingre_list_name">양파</div></li>
    </div>
    """

    ingredients = Recipe10000Parser().parse_ingredients(html)

    assert ingredients == [{"ingredient_name": "양파"}]
