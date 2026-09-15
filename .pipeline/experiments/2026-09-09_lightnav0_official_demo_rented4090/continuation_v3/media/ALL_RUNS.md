# All runs: media index

Absolute local paths are listed in `continuation_v3/OPUS_RETURN.md`.
New cohort (v3) and legacy cohort (round 1) are reported separately.

## New cohort: rep_04, rep_05, rep_06 (complete capture, exact state replay)

| run | primary film | share copy | native front | native chase | state replay | decision review | d(requested trashcan) | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rep_04 | [overview_wall.mp4](rep_04/overview_wall.mp4) | [share](rep_04/overview_share.mp4) | [front](rep_04/native_front_wall.mp4) | [chase](rep_04/native_third_wall.mp4) | [topdown](rep_04/topdown_state_replay_wall.mp4) | [decisions](rep_04/model_decisions.mp4) | 5.192 m | other_object |
| rep_05 | [overview_wall.mp4](rep_05/overview_wall.mp4) | [share](rep_05/overview_share.mp4) | [front](rep_05/native_front_wall.mp4) | [chase](rep_05/native_third_wall.mp4) | [topdown](rep_05/topdown_state_replay_wall.mp4) | [decisions](rep_05/model_decisions.mp4) | 5.190 m | other_object |
| rep_06 | [overview_wall.mp4](rep_06/overview_wall.mp4) | [share](rep_06/overview_share.mp4) | [front](rep_06/native_front_wall.mp4) | [chase](rep_06/native_third_wall.mp4) | [topdown](rep_06/topdown_state_replay_wall.mp4) | [decisions](rep_06/model_decisions.mp4) | 2.435 m | other_object |

## Legacy cohort: rep_01..03 (round-1 frame losses preserved, no exact state replay)

| run | third person (surviving frames) | model decision overlay | XY trajectory | overwritten frames | d(requested trashcan) |
| --- | --- | --- | --- | --- | --- |
| rep_01 | [third person](legacy_rep_01/third_person_surviving_frames.mp4) | [overlay](legacy_rep_01/first_person_model_overlay.mp4) | [xy](legacy_rep_01/trajectory_xy.png) | 31 | 2.414 m |
| rep_02 | [third person](legacy_rep_02/third_person_surviving_frames.mp4) | [overlay](legacy_rep_02/first_person_model_overlay.mp4) | [xy](legacy_rep_02/trajectory_xy.png) | 28 | 2.274 m |
| rep_03 | [third person](legacy_rep_03/third_person_surviving_frames.mp4) | [overlay](legacy_rep_03/first_person_model_overlay.mp4) | [xy](legacy_rep_03/trajectory_xy.png) | 32 | 2.609 m |

Every MP4 fully decodes with ffmpeg (`media/media_qa.json`, 24 files, failures: none).
Primary films carry recorded wall time; `model_decisions.mp4` and the legacy overlays are
explicitly labelled DECISION REVIEW / NOT WALL TIME.

