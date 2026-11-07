import asyncio
import sys
from sqlalchemy import select
from app.auth import generate_key, hash_key
from app.db import Base, SessionLocal, engine
from app.models import ApiKey, Tenant

async def main(tenant_name: str):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        tenant = await session.scalar(select(Tenant).where(Tenant.name == tenant_name))
        if tenant is None:
            tenant = Tenant(name=tenant_name)
            session.add(tenant)
            await session.flush()
        key = generate_key()
        session.add(ApiKey(tenant_id=tenant.id, key_hash=hash_key(key), prefix=key[:8]))
        await session.commit()
    print(f"Tenant: {tenant_name}\nAPI key (shown once, save it): {key}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))