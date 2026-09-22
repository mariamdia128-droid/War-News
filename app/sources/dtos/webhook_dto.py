from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class CnrsWebhookPostDTO(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    external_message_id: str = Field(
        validation_alias=AliasChoices("external_message_id", "id"),
    )
    message_datetime: datetime = Field(
        validation_alias=AliasChoices("message_datetime", "post_date"),
    )
    raw_text: str | None = Field(
        default=None,
        validation_alias=AliasChoices("raw_text", "post_text"),
    )
    source_platform: str | None = None
    source_name: str | None = Field(default=None, min_length=1)
    origin_account: str | None = None

    @field_validator("external_message_id", mode="before")
    @classmethod
    def _stringify_external_message_id(cls, value: object) -> object:
        if value is None:
            return value
        return str(value)


CnrsWebhookPayload = CnrsWebhookPostDTO | list[CnrsWebhookPostDTO]
