from locust import HttpUser, between, task


class HealthUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @task
    def health(self):
        self.client.get("/health")