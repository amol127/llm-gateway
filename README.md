# llm-gateway

## Authentication Cache Performance

| Run               | Requests | Median | p95      | p99      | Failures |
|-------------------|----------|--------|----------|----------|----------|
| Before auth cache | 4,488    | 550 ms | 950 ms   | 2,500 ms | 0%       |
| With auth cache   | 4,741    | 460 ms | 1,400 ms | 2,200 ms | 0%       |

### Observations
- Median latency improved by 16.36%.
- p99 latency improved by 12%.
- p95 latency increased by 47.37%.
- No request failures observed.