import os
import random

from locust import HttpUser, between, task


class GatewayUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @task
    def chat(self):
        # Unique prompts, so you measure the real request path and not the cache.
        n = random.randint(0, 10**9)
        self.client.post(
            "/v1/chat",
            headers={"Authorization": f"Bearer {os.environ['KEY']}"},
            json={"model": "mock", "messages": [{"role": "user", "content": f"load test {n}"}]},
        )