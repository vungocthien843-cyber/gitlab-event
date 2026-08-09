from app.core.db import get_engine, session_scope
from app.models.tables import InputJson

with session_scope() as session:
    records = session.query(InputJson).all()
    for r in records:
        print(f"ID: {r.id}, sources: {r.content['scope']['sources']}")
