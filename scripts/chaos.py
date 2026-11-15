import subprocess
import sys
import time

service, stop_at, start_at, duration = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])

locust = subprocess.Popen([
    "uv", "run", "locust", "-f", "locustfile.py",
    "--host", "http://127.0.0.1:8000", "--headless",
    "-u", "20", "-r", "5", "-t", f"{duration}s",
    "--csv", f"results/{service}_chaos", "--only-summary",
])
t0 = time.time()

time.sleep(stop_at)
print(f"[{time.time() - t0:.0f}s] stopping {service}", flush=True)
subprocess.run(["docker", "compose", "stop", service])

time.sleep(start_at - stop_at)
print(f"[{time.time() - t0:.0f}s] starting {service}", flush=True)
subprocess.run(["docker", "compose", "start", service])

locust.wait()