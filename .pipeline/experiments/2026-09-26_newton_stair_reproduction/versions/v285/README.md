# v285 local terrain search and phase — frozen, acceptance unmet

Native qualification passes 174 test executions (164 normalized GTest names). Complete offline acceptance passes: 49/50 legal cases (98%), 3/3 illegal controls refused, admitted global median 1.346993 s and all-50-legal median 1.359352 s. Exact 0.35 m and 0.1 s remain unchanged, with no scene/coordinate navigation branches.

All ten physical routes run once, followed by recorded-only analysis and ten full local videos. Six pass goal/PD; five also pass all-recorded sampled physical support/source/raw geometry (D07, S04, CM07, CS03, CE03). CD12 reaches but crosses source solids by 1.8423 cm. A04, G05, CU06 and CM02 fail. Remaining A-star and optimizer errors prevent physical acceptance; -1008 mentions increase from 664 to 4915. No actual retry or baseline promotion.

All 81 frozen execution source/snapshot pairs, 480 compact files, twelve analysis sources and ten MP4 hashes are locally verified. All videos fully decode, with twenty temporal visual samples inspected. [Complete report](../../audits/2026-10-19_v285_local_search_tracking/RESULTS.md), [ten full videos](../../audits/2026-10-19_v285_local_search_tracking/delivered/README.md), [delivery verification](../../audits/2026-10-19_v285_local_search_tracking/results/local_physical_delivery_verification.json).
