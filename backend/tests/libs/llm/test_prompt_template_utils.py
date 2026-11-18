import pytest

from libs.llm.utils import PromptTemplateUtils


def test_find_placeholder_names_returns_every_name_once() -> None:
    placeholder_names = PromptTemplateUtils.find_placeholder_names(
        "Hi {{persona_section}}, {{tone_section}} and {{persona_section}} again"
    )

    assert placeholder_names == frozenset({"persona_section", "tone_section"})


@pytest.mark.parametrize(
    "template",
    [
        pytest.param("Hi {{ spaced }}", id="spaced_name"),
        pytest.param("Hi {single}", id="single_braces"),
        pytest.param("Hi {{}}", id="empty_name"),
        pytest.param("Hi {{two words}}", id="name_with_space"),
        pytest.param("No placeholders", id="no_braces"),
    ],
)
def test_find_placeholder_names_not_a_placeholder_returns_empty(template: str) -> None:
    placeholder_names = PromptTemplateUtils.find_placeholder_names(template)

    assert placeholder_names == frozenset()


@pytest.mark.parametrize(
    ("template", "expected_malformed_placeholders"),
    [
        pytest.param("Hi {{ x }}", ["{{ x }}"], id="spaced_name"),
        pytest.param("Hi {{ldctx.key}}", ["{{ldctx.key}}"], id="dotted_name"),
        pytest.param("Hi {{}}", ["{{}}"], id="empty_name"),
        pytest.param(
            "{{ a }} and {{name}} and {{b-c}}", ["{{ a }}", "{{b-c}}"], id="mixed_with_valid"
        ),
    ],
)
def test_find_malformed_placeholders_returns_each_malformed_one(
    template: str, expected_malformed_placeholders: list[str]
) -> None:
    malformed_placeholders = PromptTemplateUtils.find_malformed_placeholders(template)

    assert malformed_placeholders == expected_malformed_placeholders


@pytest.mark.parametrize(
    "template",
    [
        pytest.param("Hi {{name}} and {{other_1}}", id="valid_placeholders"),
        pytest.param("Hi {single}", id="single_braces"),
        pytest.param("No placeholders", id="no_braces"),
    ],
)
def test_find_malformed_placeholders_nothing_malformed_returns_empty(template: str) -> None:
    malformed_placeholders = PromptTemplateUtils.find_malformed_placeholders(template)

    assert malformed_placeholders == []


def test_render_fills_every_known_placeholder() -> None:
    rendered_template = PromptTemplateUtils.render(
        "Hi {{first}}, meet {{second}} and {{first}}", {"first": "Ada", "second": "Grace"}
    )

    assert rendered_template == "Hi Ada, meet Grace and Ada"


def test_render_unknown_placeholder_leaves_it_as_is() -> None:
    rendered_template = PromptTemplateUtils.render("Hi {{first}} {{missing}}", {"first": "Ada"})

    assert rendered_template == "Hi Ada {{missing}}"


def test_render_value_with_placeholder_is_not_rendered_again() -> None:
    rendered_template = PromptTemplateUtils.render(
        "Bio: {{bio}} Name: {{name}}", {"bio": "I love {{name}}", "name": "Ada"}
    )

    assert rendered_template == "Bio: I love {{name}} Name: Ada"


@pytest.mark.parametrize(
    "template",
    [
        pytest.param("Hi {{ first }}", id="spaced_name"),
        pytest.param("Hi {first}", id="single_braces"),
    ],
)
def test_render_not_a_placeholder_leaves_template_unchanged(template: str) -> None:
    rendered_template = PromptTemplateUtils.render(template, {"first": "Ada"})

    assert rendered_template == template
