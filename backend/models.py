"""The API contract: request and response models, validated by Pydantic and shown in /docs."""

from typing import Annotated, Literal

from fastapi import Path
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import MAX_OUTPUTS, MAX_PARTS, NAME_PATTERN

Attribute = Literal["pressure", "velocity"]
Stat = Literal["min", "max", "average", "median", "p95"]

UserId = Annotated[str, Path(pattern=NAME_PATTERN, description="user id, e.g. 0")]
Simulation = Annotated[str, Path(pattern=NAME_PATTERN, description="simulation name, e.g. dambreak")]


class StatsQuery(BaseModel):
    """Query parameters of /stats. Lists accept outputs=0,1,2 as well as outputs=0&outputs=1."""

    model_config = ConfigDict(extra="forbid")  # a misspelled parameter is an error, not silently ignored

    attribute: Attribute
    stat: Stat
    outputs: list[Annotated[int, Field(ge=0)]] = Field(
        min_length=1, max_length=MAX_OUTPUTS, description="output numbers, e.g. 0,1,2"
    )
    parts: list[str] = Field(
        min_length=1, max_length=MAX_PARTS, description="part names, e.g. housing,obstacle"
    )

    @field_validator("outputs", "parts", mode="before")
    @classmethod
    def split_commas(cls, value):
        values = [value] if isinstance(value, str) else value
        return [item.strip() for v in values for item in str(v).split(",") if item.strip()]

    @field_validator("outputs")
    @classmethod
    def unique_outputs(cls, value: list[int]) -> list[int]:
        return sorted(set(value))  # duplicates would count the same particles twice

    @field_validator("parts")
    @classmethod
    def unique_parts(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))  # drop duplicates, keep the client's order


class StatsResponse(BaseModel):
    user_id: str
    simulation: str
    attribute: Attribute
    stat: Stat
    outputs: list[int]
    parts: list[str]
    count: int = Field(description="number of particle values the statistic was computed over")
    value: float


class Health(BaseModel):
    status: Literal["ok"]
