# Locust Web UI placeholder script
# This file is used to start the Locust Web UI service.
# Use the Web UI to upload your own test scripts.

from locust import HttpUser, task, between

class PlaceholderUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def health_check(self):
        self.client.get("/")
