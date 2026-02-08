import redis.asyncio as redis
import os
import ssl

from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# connection pool
redis_pool = redis.ConnectionPool.from_url(
  REDIS_URL,
  ssl_cert_reqs=None # Aiven certs handles it
)


async def get_redis():
  """
  Used to get the redis connection
  """
  
  client = redis.Redis(connection_pool=redis_pool)
  
  try:
    yield client
  
  finally:
    await client.close()