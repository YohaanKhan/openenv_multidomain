"""Build system prompts from tool schema documentation for domain environments."""

from __future__ import annotations

from typing import Any, Iterable

JSON_INSTRUCTION = """---
Respond ONLY with a valid JSON object in this exact format:
{"tool_name": "<name>", "tool_args": {<args>}, "thought": "<your reasoning>"}
Do not include any text outside the JSON object.
"""


class SystemPromptBuilder:
    """Helper for rendering tool schemas into system prompt text."""

    @staticmethod
    def build(template: str, tools: dict[str, dict[str, Any]]) -> str:
        """
        Fill `{tool_docs}` in the template with markdown generated from tool schemas.

        Raises ValueError when the placeholder is missing.
        """
        if "{tool_docs}" not in template:
            raise ValueError("Template must include '{tool_docs}' placeholder.")

        tool_sections: list[str] = []
        for tool_name, tool_meta in tools.items():
            schema = tool_meta["schema"]
            description = (schema.__doc__ or "").strip()
            if description:
                header = f"### `{tool_name}`\n{description}"
            else:
                header = f"### `{tool_name}`"

            field_lines: list[str] = []
            for field_name, field in schema.model_fields.items():
                type_name = getattr(field.annotation, "__name__", repr(field.annotation))
                required = field.is_required()
                description = (field.description or "").strip()
                default = field.default
                status = "required" if required else "optional"
                line = f"- **{field_name}** ({type_name}) — {status}"
                if description:
                    line += f"; {description}"
                if not required and default is not None:
                    line += f" (default: {default!r})"
                field_lines.append(line)

            section = "\n".join([header, "", *field_lines])
            tool_sections.append(section)

        tool_docs = "\n\n".join(tool_sections)
        return template.format(tool_docs=tool_docs) + "\n" + JSON_INSTRUCTION
