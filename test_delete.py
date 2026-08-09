from app.core.db import get_engine, session_scope
from app.models.tables import InputJson
from app.services.ingest import delete_catalog
from app.services.store import store

with session_scope() as session:
    store.load_from_db()
    
    records = session.query(InputJson).all()
    for r in records:
        print(f"ID: {r.id}, sources: {r.content['scope']['sources']}")

    try:
        delete_catalog('banking-api-gateway.catalog.yaml', 'test-req')
        print("Delete successful!")
    except Exception as e:
        print("Delete failed:", str(e))
        
    records = session.query(InputJson).all()
    print(f"Remaining records: {len(records)}")
