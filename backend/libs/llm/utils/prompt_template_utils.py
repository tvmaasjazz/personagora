import re
from collections.abc import Mapping

from libs.llm.constants import PROMPT_TEMPLATE_PLACEHOLDER_PATTERN


class PromptTemplateUtils:
    """Finds and fills the {{name}} placeholders of a prompt template."""

    @staticmethod
    def find_placeholder_names(template: str) -> frozenset[str]:
        """Returns the name of every {{name}} placeholder in the template."""
        return frozenset(PROMPT_TEMPLATE_PLACEHOLDER_PATTERN.findall(template))

    @staticmethod
    def render(template: str, variables: Mapping[str, str]) -> str:
        """Fills each {{name}} found in variables and leaves any other placeholder as it is."""

        def replace_placeholder(placeholder_match: re.Match[str]) -> str:
            return variables.get(placeholder_match.group(1), placeholder_match.group(0))

        # One pass, so a value that holds {{...}} is never rendered again
        return PROMPT_TEMPLATE_PLACEHOLDER_PATTERN.sub(replace_placeholder, template)
