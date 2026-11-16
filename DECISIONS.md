Log rows during the outage are lost. Check the count: select count(*) from request_logs; against 18,007. The gap is what was dropped. If this table ever drives billing, those rows need a safer path.
A revoked key keeps working for up to 5 minutes during a database outage, and for 30 seconds normally.
New tenants can’t authenticate while the database is down (a clean 503).
Rate limiting fails open when Redis is down. Your Redis breaker was never re-tested after adding it, so run one Redis chaos test with the new code: uv run python scripts/chaos.py redis 20 60 90.