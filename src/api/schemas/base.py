"""
Base schemas với camelCase serialization cho Frontend.

Tất cả schemas nên kế thừa từ CamelCaseBaseModel để đảm bảo
JSON response dùng camelCase (phù hợp với JavaScript convention).
"""

from pydantic import BaseModel, ConfigDict
from typing import Any


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(x.capitalize() for x in components[1:])


class CamelCaseBaseModel(BaseModel):
    """
    Base model tự động serialize/deserialize giữa snake_case và camelCase.

    - Python code: Dùng snake_case (PEP8)
    - JSON response: camelCase (JavaScript convention)
    """

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel_case,
    )

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Override để mặc định by_alias=True."""
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs) -> str:
        """Override để mặc định by_alias=True."""
        kwargs.setdefault("by_alias", True)
        return super().model_dump_json(**kwargs)
