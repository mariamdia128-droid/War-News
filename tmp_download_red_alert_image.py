from sqlalchemy import text
import httpx

from app.core.database import SessionLocal


db = SessionLocal()
url = db.execute(
    text(
        """
        select raw_payload->'image_urls'->>0
        from raw_messages
        where external_message_id = :external_id
        """
    ),
    {"external_id": "telegram:redlinkleb:45673"},
).scalar()
db.close()
print(url)
response = httpx.get(url, timeout=30)
response.raise_for_status()
with open("/tmp/red_alert_45673.jpg", "wb") as handle:
    handle.write(response.content)
print(len(response.content))
