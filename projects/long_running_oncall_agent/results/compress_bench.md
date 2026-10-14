# Component bench: tool-output reduction

Tokens are cl100k. `evidence` = grading-relevant strings present in the raw output that survive the treatment. Latency is median of ScaleDown calls.

| scenario | tool | raw | log_fold | sd_compress | fold+sd_compress |
|---|---|---|---|---|---|
| db-pool-exhaustion | query_logs | 18,361 tok (ev 2/2) | 1,731 tok (-91%, ev 2/2) | 18,361 tok (-0%, ev 2/2, 7338ms) | 1,731 tok (-91%, ev 2/2, 574ms) |
| db-pool-exhaustion | query_logs | 18,324 tok (ev 1/1) | 2,063 tok (-89%, ev 1/1) | 18,324 tok (-0%, ev 1/1, 7536ms) | 2,063 tok (-89%, ev 1/1, 749ms) |
| db-pool-exhaustion | search_runbooks | 1,802 tok (ev 2/2) | 1,802 tok (-0%, ev 2/2) | 229 tok (-87%, ev 2/2, 372ms) | 229 tok (-87%, ev 2/2, 475ms) |
| bad-feature-flag | query_logs | 18,203 tok (ev 1/1) | 2,058 tok (-89%, ev 1/1) | 18,203 tok (-0%, ev 1/1, 7372ms) | 2,058 tok (-89%, ev 1/1, 729ms) |
| bad-feature-flag | get_k8s_events | 5,700 tok (ev 1/1) | 5,700 tok (-0%, ev 1/1) | 5,700 tok (-0%, ev 1/1, 1427ms) | 5,700 tok (-0%, ev 1/1, 1541ms) |
| bad-feature-flag | search_runbooks | 1,841 tok (ev 3/3) | 1,841 tok (-0%, ev 3/3) | 187 tok (-90%, ev 3/3, 604ms) | 187 tok (-90%, ev 3/3, 443ms) |
| red-herring-drift | query_logs | 17,456 tok (ev 1/1) | 1,883 tok (-89%, ev 1/1) | 17,456 tok (-0%, ev 1/1, 6957ms) | 1,883 tok (-89%, ev 1/1, 622ms) |
| red-herring-drift | get_k8s_events | 5,812 tok (ev 1/1) | 5,812 tok (-0%, ev 1/1) | 5,812 tok (-0%, ev 1/1, 1588ms) | 5,812 tok (-0%, ev 1/1, 366ms) |
| log-flood | query_logs | 68,706 tok (ev 2/2) | 1,980 tok (-97%, ev 2/2) | 26,402 tok (-62%, ev 2/2, 15272ms) | 1,951 tok (-97%, ev 1/2, 672ms) |
| log-flood | query_logs | 65,418 tok (ev 1/1) | 1,562 tok (-98%, ev 1/1) | 65,418 tok (-0%, ev 1/1, 46135ms) | 1,562 tok (-98%, ev 1/1, 572ms) |
