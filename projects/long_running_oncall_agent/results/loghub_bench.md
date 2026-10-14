# LogHub component bench

Window: first 2000 lines per system. Tokens: cl100k. `abnormal` = distinct WARN/ERROR/FATAL ground-truth templates with at least one line kept verbatim. `identical` = ScaleDown returned the input unchanged while reporting success.

| system | GT templates | raw | log_fold | sd_compress | fold+sd_compress |
|---|---|---|---|---|---|
| OpenStack | 43 | 295,240 tok, abnormal 2/2 | 8,555 tok (-97%), abnormal 2/2 | 147,985 tok (-50%), abnormal 2/2, 22263ms | 2,584 tok (-99%), abnormal 1/2, 1071ms |
| HDFS | 14 | 96,789 tok, abnormal 1/1 | 1,803 tok (-98%), abnormal 1/1 | 18,263 tok (-81%), abnormal 1/1, 9385ms | 1,803 tok (-98%), abnormal 1/1, 1807ms |
| Hadoop | 114 | 132,034 tok, abnormal 12/12 | 7,931 tok (-94%), abnormal 12/12 | 2,585 tok (-98%), abnormal 4/12, 12329ms | 1,144 tok (-99%), abnormal 4/12, 1013ms |
| BGL | 120 | 143,497 tok, abnormal 77/77 | 12,028 tok (-92%), abnormal 73/77 | 143,497 tok (-0%), abnormal 77/77, 1755ms, identical | 8,048 tok (-94%), abnormal 49/77, 1720ms |
| Apache | 6 | 65,360 tok, abnormal 4/4 | 468 tok (-99%), abnormal 4/4 | 65,360 tok (-0%), abnormal 4/4, 8765ms, identical | 468 tok (-99%), abnormal 4/4, 322ms, identical |
| Zookeeper | 50 | 108,915 tok, abnormal 12/12 | 3,693 tok (-97%), abnormal 12/12 | 108,915 tok (-0%), abnormal 12/12, 19311ms, identical | 3,693 tok (-97%), abnormal 12/12, 736ms |
