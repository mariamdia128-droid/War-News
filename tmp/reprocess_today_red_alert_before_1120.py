from app.core.database import SessionLocal
from app.news.models import RawMessage, Village
from app.news.repositories.air_violation_repository import AirViolationRepository
from app.news.services.air_violations.red_alert_air_violation_service import (
    RedAlertAirViolationService,
)
from app.sources.services.red_alert_collector import classify_condition, match_village


RAW_MESSAGE_IDS = [804, 805, 806, 807]


def main() -> None:
    with SessionLocal() as db:
        villages = db.query(Village).all()
        service = RedAlertAirViolationService(
            AirViolationRepository(db),
            classify_condition,
            match_village,
        )
        for raw_id in RAW_MESSAGE_IDS:
            message = db.get(RawMessage, raw_id)
            if message is None:
                print(f"{raw_id}: missing")
                continue
            before = message.status.value
            wrote = service.process(message, villages)
            db.flush()
            print(
                f"{raw_id}: {before} -> {message.status.value}; "
                f"wrote={wrote}; reason={(message.filter_result or {}).get('reasoning')}"
            )
        db.commit()


if __name__ == "__main__":
    main()
