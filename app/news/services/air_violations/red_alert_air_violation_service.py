from __future__ import annotations

import re
from collections.abc import Callable

from app.news.dtos import MatchResultDTO, MatchResultStatus
from app.news.dtos.match_result_dto import VillageMatchResult
from app.news.interfaces import AirViolationRepositoryInterface
from app.news.models import MessageStatus, RawMessage, Village
from app.news.services.air_violations.air_violation_exclusions import air_violation_exclusion

ConditionClassifier = Callable[[str], int | None]
VillageMatcher = Callable[[str, list[Village]], tuple[Village, str] | None]
CAZA_ONLY_ALIASES: dict[str, tuple[str, str | None]] = {
    "bekaa": ("West Bekaa", "البقاع الغربي"),
    "west bekaa": ("West Bekaa", "البقاع الغربي"),
    "west beqaa": ("West Bekaa", "البقاع الغربي"),
    "البقاع": ("West Bekaa", "البقاع الغربي"),
    "الجنوب": ("Multiple regions", "مناطق متعددة"),
}


class RedAlertAirViolationService:
    """Apply air-violation rules and route a collected message."""

    def __init__(
        self,
        air_violations: AirViolationRepositoryInterface,
        classify_condition: ConditionClassifier,
        match_village: VillageMatcher,
    ) -> None:
        self.air_violations = air_violations
        self.classify_condition = classify_condition
        self.match_village = match_village

    def process(self, message: RawMessage, villages: list[Village]) -> bool:
        text = message.raw_text or ""
        exclusion = air_violation_exclusion(text)
        if exclusion is not None:
            self.air_violations.discard_for_message(message)
            self._reject(
                message,
                exclusion.reason,
                error=exclusion.evidence_span,
            )
            return False

        condition_id = self.classify_condition(text)
        if condition_id is None:
            self.air_violations.discard_for_message(message)
            self._reject(message, "No supported air-violation keyword")
            return False

        village_matches = self._match_villages(text, villages)
        village_match = village_matches[0] if village_matches else self.match_village(text, villages)
        if village_match is None:
            caza_en, caza_ar = self._match_caza(text, villages)
            if not (caza_en or caza_ar):
                self.air_violations.discard_for_message(message)
                self._reject(message, self._missing_village_reason(message))
                return False
            result = self._match_result(
                text=text,
                condition_id=condition_id,
                village=None,
                raw_location=caza_en or caza_ar,
            )
            message.filter_result = self._result(
                message,
                "relevant",
                "Supported air-violation keyword and caza matched",
            )
            message.match_result = result.model_dump(mode="json")
            message.status = MessageStatus.parsed
            wrote_air_violation = self.air_violations.route_from_match(message, result)
            message.status = MessageStatus.routed_air_violation
            message.error_message = "red_alert: routed to air_violations; not an incident"
            return wrote_air_violation

        village, raw_location = village_match
        result = self._match_result(
            text=text,
            condition_id=condition_id,
            village=village,
            villages=[village for village, _raw_location in village_matches] or [village],
            raw_location=raw_location,
        )
        message.filter_result = self._result(
            message,
            "relevant",
            "Supported air-violation keyword and locality matched",
        )
        message.match_result = result.model_dump(mode="json")
        message.status = MessageStatus.parsed
        wrote_air_violation = self.air_violations.route_from_match(message, result)
        message.status = MessageStatus.routed_air_violation
        message.error_message = "red_alert: routed to air_violations; not an incident"
        return wrote_air_violation

    @staticmethod
    def _normalize_arabic(value: str) -> str:
        value = re.sub(r"[\u064b-\u065f\u0670]", "", value)
        value = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        value = value.replace("ى", "ي").replace("ة", "ه")
        return re.sub(r"[\W_]+", " ", value.casefold()).strip()

    @staticmethod
    def _normalize_latin(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    @classmethod
    def _match_villages(cls, text: str, villages: list[Village]) -> list[tuple[Village, str]]:
        normalized_text = cls._normalize_arabic(text)
        normalized_latin_text = cls._normalize_latin(text)
        matches: dict[int, tuple[Village, str]] = {}
        for village in villages:
            names = (
                getattr(village, "ref_name_ar", None),
                getattr(village, "ref_name_en", None),
                getattr(village, "acs_name", None),
                getattr(village, "cad_name", None),
            )
            for name in names:
                if not name:
                    continue
                normalized_name = (
                    cls._normalize_arabic(name)
                    if re.search(r"[\u0600-\u06ff]", name)
                    else cls._normalize_latin(name)
                )
                normalized_source = (
                    normalized_text
                    if re.search(r"[\u0600-\u06ff]", name)
                    else normalized_latin_text
                )
                if len(normalized_name) >= 4 and re.search(
                    rf"(?<!\w){re.escape(normalized_name)}(?!\w)",
                    normalized_source,
                ):
                    current = matches.get(village.id)
                    if current is None or len(name) > len(current[1]):
                        matches[village.id] = (village, name)
        return list(matches.values())

    @staticmethod
    def _match_caza(text: str, villages: list[Village]) -> tuple[str | None, str | None]:
        normalized_text = text.casefold()
        token_text = re.sub(r"[\W_]+", " ", normalized_text).strip()
        mentioned: set[tuple[str | None, str | None]] = set()
        for village in villages:
            for name in (village.caza_en, village.caza_ar):
                if name and len(name) >= 4 and name.casefold() in normalized_text:
                    mentioned.add((village.caza_en, village.caza_ar))
        for alias, caza in CAZA_ONLY_ALIASES.items():
            alias_token = re.sub(r"[\W_]+", " ", alias.casefold()).strip()
            if re.search(rf"(?<!\w){re.escape(alias_token)}(?!\w)", token_text):
                mentioned.add(caza)
        if len(mentioned) > 1:
            return "Multiple regions", "مناطق متعددة"
        if len(mentioned) == 1:
            return next(iter(mentioned))
        return None, None

    @staticmethod
    def _missing_village_reason(message: RawMessage) -> str:
        text = (message.raw_text or "").casefold()
        if ("آخر تحديث" in text or "اخر تحديث" in text) and "لبنان" in text:
            return "General multi-area alert; no single village applies"
        if (message.raw_payload or {}).get("ocr_text"):
            return "Location could not be identified reliably from the alert image"
        return "No locality was specified in the Red Alert notice"

    @staticmethod
    def _match_result(
        *,
        text: str,
        condition_id: int,
        village: Village | None,
        raw_location: str | None,
        villages: list[Village] | None = None,
    ) -> MatchResultDTO:
        matched_villages = villages or ([village] if village is not None else [])
        village_matches = (
            [
                VillageMatchResult(
                    matched_village_id=matched_village.id,
                    village_confidence=1.0,
                    village_match_status=MatchResultStatus.matched,
                    village_review_required=False,
                    raw_village_text=raw_location if len(matched_villages) == 1 else (
                        getattr(matched_village, "ref_name_en", None)
                        or getattr(matched_village, "acs_name", None)
                        or getattr(matched_village, "cad_name", None)
                        or getattr(matched_village, "ref_name_ar", None)
                    ),
                )
                for matched_village in matched_villages
            ]
            if matched_villages
            else []
        )
        return MatchResultDTO(
            village_matches=village_matches,
            any_village_low_confidence=False,
            matched_condition_id=condition_id,
            condition_confidence=1.0,
            condition_match_status=MatchResultStatus.matched,
            condition_review_required=False,
            raw_condition_text=text,
        )

    @staticmethod
    def _result(
        message: RawMessage, verdict: str, reasoning: str
    ) -> dict[str, object]:
        return {
            "backend": "red_alert_rules",
            "verdict": verdict,
            "reasoning": reasoning,
            "confidence": 1.0,
            "raw_message_id": message.id,
        }

    def _reject(
        self,
        message: RawMessage,
        reasoning: str,
        *,
        verdict: str = "not_relevant",
        error: str | None = None,
    ) -> None:
        message.filter_result = self._result(message, verdict, reasoning)
        message.status = MessageStatus.rejected
        message.error_message = error
