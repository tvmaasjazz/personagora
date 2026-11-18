from tests.factories.llm import build_get_llm_config_result, build_resolve_llm_config_result


def test_resolve_llm_config_result_served_config_exposes_its_variation() -> None:
    llm_config_source_result = build_get_llm_config_result(
        variation_key="variation-a", variation_version=7
    )

    resolve_llm_config_result = build_resolve_llm_config_result(
        llm_config_source_result=llm_config_source_result
    )

    assert resolve_llm_config_result.variation_key == "variation-a"
    assert resolve_llm_config_result.variation_version == 7


def test_resolve_llm_config_result_code_default_has_no_variation() -> None:
    resolve_llm_config_result = build_resolve_llm_config_result(llm_config_source_result=None)

    assert resolve_llm_config_result.variation_key is None
    assert resolve_llm_config_result.variation_version is None
