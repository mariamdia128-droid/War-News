from datetime import datetime, time
from sqlalchemy import select
from app.core.database import SessionLocal
import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.news.models import Incident, RawMessage
from app.news.services.clustering.clustering_service import cosine_similarity
from app.news.services.dedup.text_similarity import event_token_similarity
from app.core.text_normalization import normalize_arabic_text
from app.news.services.clustering.raw_message_embedding_service import strip_boilerplate
from app.core.text_sanitizer import strip_emoji_and_pictographs

PAIR_LABELS = [
    ("#7 09:21 house+car", "711adf5b-5d46-4a5c-8e21-1554c7d975b1"),
    ("#1 11:33 full MoH", "1a5b73de-fb96-4c4a-ae64-7f71b73c9a12"),
    ("#3 11:00 MoH car", "2c255b6b-875c-4f3e-bb2f-43c12918521e"),
    ("#8 07:04 drone car", "9f5855d0-e7ff-4a68-b706-4d6b79a137b4"),
    ("#10 02:22 prelim car", "4b0a525e-070e-44c1-8fc9-dc64a5b3a3e3"),
    ("#11 02:21 casualties", "a7d8a296-3be8-46f8-9328-f5bca76f8917"),
    ("Zahraa 11:31 named", "e6ee7bfa-3f45-4457-82cf-54d6cdda95a0"),
    ("early 02:12 raid", "b301b647-3f3d-415c-af52-e1c53775eef4"),
    ("02:26 building", "15477afa-51e2-49f4-a9b6-fbceafa1c95c"),
]


def word_sim(a: str, b: str) -> float:
    left = set(normalize_arabic_text(strip_boilerplate(strip_emoji_and_pictographs(a or ""))).split())
    right = set(normalize_arabic_text(strip_boilerplate(strip_emoji_and_pictographs(b or ""))).split())
    if not left or not right:
        return 0.0
    return len(left & right) / float(len(left | right))


db = SessionLocal()
try:
    incidents = {}
    for label, iid in PAIR_LABELS:
        row = db.execute(select(Incident).where(Incident.id == iid)).scalar_one()
        raw = db.get(RawMessage, row.raw_message_id) if row.raw_message_id else None
        incidents[label] = (row, raw)
        print(
            label,
            "event",
            row.event_time,
            "msg_dt",
            None if raw is None else raw.message_datetime,
            "emb_inc",
            row.khabar_embedding is not None,
            "emb_raw",
            None if raw is None else raw.content_embedding is not None,
        )

    pairs = [
        ("#7 vs #1", "#7 09:21 house+car", "#1 11:33 full MoH"),
        ("#1 vs #3", "#1 11:33 full MoH", "#3 11:00 MoH car"),
        ("#1 vs #8", "#1 11:33 full MoH", "#8 07:04 drone car"),
        ("#3 vs #8", "#3 11:00 MoH car", "#8 07:04 drone car"),
        ("#1 vs #10", "#1 11:33 full MoH", "#10 02:22 prelim car"),
        ("#1 vs #11", "#1 11:33 full MoH", "#11 02:21 casualties"),
        ("#1 vs Zahraa", "#1 11:33 full MoH", "Zahraa 11:31 named"),
        ("#7 vs Zahraa", "#7 09:21 house+car", "Zahraa 11:31 named"),
        ("#10 vs #8", "#10 02:22 prelim car", "#8 07:04 drone car"),
        ("#10 vs #3", "#10 02:22 prelim car", "#3 11:00 MoH car"),
        ("#11 vs #10", "#11 02:21 casualties", "#10 02:22 prelim car"),
        ("#7 vs #3", "#7 09:21 house+car", "#3 11:00 MoH car"),
    ]
    print("PAIRS")
    for name, a, b in pairs:
        ia, ra = incidents[a]
        ib, rb = incidents[b]
        emb_a = ia.khabar_embedding or (ra.content_embedding if ra else None)
        emb_b = ib.khabar_embedding or (rb.content_embedding if rb else None)
        print(
            name,
            "emb",
            round(cosine_similarity(emb_a, emb_b), 4),
            "jaccard",
            round(word_sim(ia.khabar, ib.khabar), 4),
            "token",
            event_token_similarity(ia.khabar, ib.khabar),
        )

    print("MERGE_SOURCES_FOR_#7")
    for raw_id in (5050, 5052, 5046, 4423):
        raw = db.get(RawMessage, raw_id)
        if raw is None:
            print(raw_id, "MISSING")
            continue
        print(raw_id, raw.message_datetime, (raw.raw_text or "").replace("\n", " ")[:140])
finally:
    db.close()
