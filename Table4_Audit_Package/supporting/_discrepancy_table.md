| dataset | method | metric | manuscript | locked_analog | locked_mean | locked_sd | difference | relative_pct |
|---|---|---|---|---|---|---|---|---|
| ciciot | FedAvg | F1 | 0.9921 | scenario_fedavg_random | 0.9904 | 0.0010 | 0.0017 | 0.2000 |
| ciciot | FedAvg | ROC-AUC | 0.9935 | scenario_fedavg_random | 0.9930 | 0.0015 | 0.0005 | 0.1000 |
| ciciot | FedAvg | FPR | 0.1453 | scenario_fedavg_random | 0.1400 | 0.0108 | 0.0053 | 3.8000 |
| ciciot | FedAvg | Delay (ms) | 89.3400 | scenario_fedavg_random | 71.2721 | 5.0589 | 18.0679 | 25.4000 |
| ciciot | FedAvg | PDR | 0.7364 | scenario_fedavg_random | 0.7818 | 0.0319 | -0.0454 | -5.8000 |
| ciciot | FedAvg | Path stability | 0.5601 | scenario_fedavg_random | 0.8545 | 0.0228 | -0.2944 | -34.5000 |
| ciciot | FedAvg | Transfer efficiency (Mbit/s) | 6.8100 | scenario_fedavg_random | 9.3832 | 0.5802 | -2.5732 | -27.4000 |
| ciciot | Robust no-DP | F1 | 0.9939 | robust_random_no_imputation | 0.9933 | 0.0003 | 0.0006 | 0.1000 |
| ciciot | Robust no-DP | ROC-AUC | 0.9961 | robust_random_no_imputation | 0.9962 | 0.0003 | -0.0001 | -0.0000 |
| ciciot | Robust no-DP | FPR | 0.1478 | robust_random_no_imputation | 0.1473 | 0.0122 | 0.0005 | 0.3000 |
| ciciot | Robust no-DP | Delay (ms) | 89.6300 | robust_random_no_imputation | 71.2721 | 5.0589 | 18.3579 | 25.8000 |
| ciciot | Robust no-DP | PDR | 0.7275 | robust_random_no_imputation | 0.7818 | 0.0319 | -0.0543 | -6.9000 |
| ciciot | Robust no-DP | Path stability | 0.5466 | robust_random_no_imputation | 0.8545 | 0.0228 | -0.3079 | -36.0000 |
| ciciot | Robust no-DP | Transfer efficiency (Mbit/s) | 6.7600 | robust_random_no_imputation | 9.3832 | 0.5802 | -2.6232 | -28.0000 |
| ciciot | Proposed eps~10 | F1 | 0.9919 | reference_gaussian | 0.9911 | 0.0004 | 0.0008 | 0.1000 |
| ciciot | Proposed eps~10 | ROC-AUC | 0.9934 | reference_gaussian | 0.9930 | 0.0014 | 0.0004 | 0.0000 |
| ciciot | Proposed eps~10 | FPR | 0.1453 | reference_gaussian | 0.1407 | 0.0184 | 0.0046 | 3.3000 |
| ciciot | Proposed eps~10 | Delay (ms) | 65.5100 | reference_gaussian | 65.9000 | 6.1851 | -0.3900 | -0.6000 |
| ciciot | Proposed eps~10 | PDR | 0.8358 | reference_gaussian | 0.8511 | 0.0146 | -0.0153 | -1.8000 |
| ciciot | Proposed eps~10 | Path stability | 0.9124 | reference_gaussian | 0.9231 | 0.0070 | -0.0107 | -1.2000 |
| ciciot | Proposed eps~10 | Transfer efficiency (Mbit/s) | 9.9200 | reference_gaussian | 10.9356 | 0.8955 | -1.0156 | -9.3000 |
| unsw | FedAvg | F1 | 0.7754 | scenario_fedavg_random | 0.7217 | 0.2069 | 0.0537 | 7.4000 |
| unsw | FedAvg | ROC-AUC | 0.8542 | scenario_fedavg_random | 0.8752 | 0.0863 | -0.0210 | -2.4000 |
| unsw | FedAvg | FPR | 0.3456 | scenario_fedavg_random | 0.1464 | 0.0158 | 0.1992 | 136.1000 |
| unsw | FedAvg | Delay (ms) | 99.0400 | scenario_fedavg_random | 81.5278 | 5.5757 | 17.5122 | 21.5000 |
| unsw | FedAvg | PDR | 0.7350 | scenario_fedavg_random | 0.7818 | 0.0319 | -0.0468 | -6.0000 |
| unsw | FedAvg | Path stability | 0.5579 | scenario_fedavg_random | 0.8545 | 0.0228 | -0.2966 | -34.7000 |
| unsw | FedAvg | Transfer efficiency (Mbit/s) | 11.1100 | scenario_fedavg_random | 14.9304 | 0.8362 | -3.8204 | -25.6000 |
| unsw | Robust no-DP | F1 | 0.8383 | robust_random_no_imputation | 0.9526 | 0.0026 | -0.1143 | -12.0000 |
| unsw | Robust no-DP | ROC-AUC | 0.9281 | robust_random_no_imputation | 0.9825 | 0.0018 | -0.0544 | -5.5000 |
| unsw | Robust no-DP | FPR | 0.3463 | robust_random_no_imputation | 0.1431 | 0.0143 | 0.2032 | 141.9000 |
| unsw | Robust no-DP | Delay (ms) | 98.3300 | robust_random_no_imputation | 81.5278 | 5.5757 | 16.8022 | 20.6000 |
| unsw | Robust no-DP | PDR | 0.7183 | robust_random_no_imputation | 0.7818 | 0.0319 | -0.0635 | -8.1000 |
| unsw | Robust no-DP | Path stability | 0.5438 | robust_random_no_imputation | 0.8545 | 0.0228 | -0.3107 | -36.4000 |
| unsw | Robust no-DP | Transfer efficiency (Mbit/s) | 11.1300 | robust_random_no_imputation | 14.9304 | 0.8362 | -3.8004 | -25.5000 |
| unsw | Proposed eps~10 | F1 | 0.8106 | reference_gaussian | 0.9005 | 0.0335 | -0.0899 | -10.0000 |
| unsw | Proposed eps~10 | ROC-AUC | 0.8801 | reference_gaussian | 0.9419 | 0.0166 | -0.0618 | -6.6000 |
| unsw | Proposed eps~10 | FPR | 0.3145 | reference_gaussian | 0.1488 | 0.0102 | 0.1657 | 111.3000 |
| unsw | Proposed eps~10 | Delay (ms) | 74.5300 | reference_gaussian | 76.6499 | 6.5535 | -2.1199 | -2.8000 |
| unsw | Proposed eps~10 | PDR | 0.8348 | reference_gaussian | 0.8511 | 0.0146 | -0.0163 | -1.9000 |
| unsw | Proposed eps~10 | Path stability | 0.9118 | reference_gaussian | 0.9231 | 0.0070 | -0.0113 | -1.2000 |
| unsw | Proposed eps~10 | Transfer efficiency (Mbit/s) | 15.9400 | reference_gaussian | 17.2382 | 1.0719 | -1.2982 | -7.5000 |