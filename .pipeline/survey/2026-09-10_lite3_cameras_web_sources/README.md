# Lite3 / RealSense / InternVLA-N1 camera facts — primary-source verification

- Fetch date: 2026-09-10 (all fetches between 13:58 and 14:05 UTC).
- Task: `.trellis/tasks/09-10-internvla-n1-camera-ablation-sim`.
- Method: `curl` + `pdftotext -layout` (poppler, /opt/homebrew/bin) for PDFs,
  `WebFetch`/`WebSearch` for HTML, shallow `git clone` for InternNav. Page
  numbers below are PDF page indices from `pdftotext` form feeds; line numbers
  (`L`) refer to the `-layout` text files kept in this directory.
- Label rules: `primary` = manufacturer / author document (own site, own
  OSS bucket, own GitHub, own tech report). `secondary` = anything else
  (search-engine snippet, distributor prose, community repo). Only `primary`
  rows count as verified. `derived` = computed by me from a primary number,
  never quoted by the source itself.
- Budget: 25 fetches/searches used (log at the end). No further fetches.

## 1. Intel RealSense D435i and D455

Source A (primary): *Intel RealSense Camera 400 Series Product Family
Datasheet*, Document Number 337029-017, Revision 021, PDF dated 2025-09-30,
downloaded 2026-09-10 from
`https://realsenseai.com/wp-content/uploads/2025/09/Intel-RealSense-D400-Series-Datasheet-October-2025.pdf`
(realsenseai.com is the current RealSense manufacturer site after the
spin-out from Intel; the PDF still carries the Intel document number).
Local copy: `Intel-RealSense-D400-Series-Datasheet-October-2025.pdf` (160 pages).
Note: page footers inside the PDF still show older revision codes on some
pages (e.g. p15 footer reads `337029-012`); the cover states 337029-017.

| Fact | Value | Verbatim quote | Where | Label |
|---|---|---|---|---|
| D435i colour (RGB) FOV | H 69° x V 42° (D 77°) | `Color Camera FOV                H:69 /V:42 /D:77               H:69 /V:42 /D:77               H:90 /V:65 /D:98               H:84 / V:58 / D:92` (columns: D415, D435/D435i/D435f/D435if, D455/D455f/D456, D405) | Table 3-49 "Depth Camera SKU Properties", p67 L27 | primary |
| D455 colour (RGB) FOV | H 90° x V 65° (D 98°) | same row as above, third column | Table 3-49, p67 L27 | primary |
| D455 colour sensor property table | HFOV 90°, VFOV 65°, DFOV 98° | `Horizontal Field of View  90o` / `Vertical Field of View  65o` / `Diagonal Field of View  98o` | Table 3-19 "Color Sensor Properties – D450" (D450 is the depth module inside D455 per Table 3-49 p67 L6-7), p44 L11-15 | primary |
| D435i depth FOV (HD 16:9) | H 87° x V 58° (D 95°) | `Depth FOV HD (16:9) (degrees)  H:65 / V:40 / D:72   H:87 / V:58 / D:95   H:87 / V:58 / D:95   H:84 / V:58 / D:92` | Table 3-49, p67 L13-15 | primary |
| D455 depth FOV (HD 16:9) | H 87° x V 58° (D 95°) | same row, third column | Table 3-49, p67 L13-15 | primary |
| D435i / D455 depth FOV (VGA 4:3) | H 75° x V 62° (D 89°) for both | `Depth FOV VGA (4:3) (degrees)  H:50/ V:40 / D:61   H:75 / V:62 / D:89   H:75 / V:62 / D:89   N/A` | Table 3-49, p67 L17-19 | primary |
| FOV tolerance note | ±5 % mechanical, ~±3° lens-to-lens | `Due to mechanical tolerances of +/- 5%, Max and Min FOV values can vary from lens to lens and module to module by ~ +/- 3 degrees`; `Depth FOV specified at 20 cm for D401 and at 2 m for other modules` | Table 3-49 notes, p67 L40-42 | primary |
| D435i colour sensor | OmniVision OV2740 | `Color Sensor   OV2740   OV2740   OV9782   OV9782` | Table 3-49, p67 L25 | primary |
| D455 colour sensor | OmniVision OV9782, global shutter | `Image Sensor  OmniVision Technologies OV9782` / `Shutter Type  Global Shutter` | Table 3-19, p43 L55 and p44 L7 | primary |
| D435i RGB resolution | up to 1920 x 1080 | `RealSense™ Depth Camera D435/D435i D435f/D435if Features` ... `•   Up to 1920 x 1080 RGB resolution` | Feature list, p16 L1-4; also Table 4-2 colour stream `1920 x 1080  6, 15, 30` for `D415 & D435/D435i/D435f/D435if`, p76 L35-43 | primary |
| D455 RGB resolution | up to 1280 x 800 | `D455/D455f/D456 Features` ... `•   Up to 1280 x 800 RGB resolution` / `•   RGB global shutter sensor for up to 90 FPS` | Feature list, p16 L13-17; also Table 4-3 (D450/D455/D455f/D456) colour stream `1280 x 800  5, 15, 30`, p77 L41 | primary |
| D435i / D455 depth resolution | up to 1280 x 720 | `•   Up to 1280 x 720 stereo depth resolution` (both feature lists) | p16 L3 and p16 L13 | primary |
| D435i colour sensor detailed table | none for D435i specifically | Table 3-18 (p43) is labelled `Color Sensor Properties – D415` (OV2740, `Active Pixels 1920 x 1080`, HFOV `69.4o`, VFOV `42.5o`, DFOV `77o`). D435i uses the same OV2740 sensor per Table 3-49, but the datasheet does not print a D435i-labelled colour-sensor table, so 69.4/42.5 is NOT claimed for D435i here; use the Table 3-49 row (69/42/77). | p43 L16-46 | primary (for D415 only) |

Product pages `https://www.intelrealsense.com/depth-camera-d435i/` and
`.../depth-camera-d455/` could not be reached (see failures), so the datasheet
is the only primary source used. Intel ARK was not attempted (budget).

## 2. DEEP Robotics Jueying Lite3 built-in wide-angle camera

Result: **no primary source found that specifies a "wide-angle camera"
(FOV, resolution, frame rate, sensor model or mounting) for any Lite3
variant.** Every manufacturer document fetched lists perception *functions*
and (for Pro/LiDAR) the RealSense D435i, but no wide-angle camera row.

| Fact | Value | Verbatim quote | Where | Label |
|---|---|---|---|---|
| Depth camera on Lite3 Pro / LiDAR | Intel RealSense D435i | `Jueying Lite3 Pro/LiDAR is equipped with Intel RealSense D435i.` | *Jueying Lite3 Perception Development Manual (beta) V2.2.2-0, 2024.12.31*, DEEP Robotics, hosted by distributor generation-robots.com: `https://static.generation-robots.com/media/lite-3-perception-development-manual.pdf`, section 4 "Depth Camera", text L402-404 (PDF p13 per TOC) | primary (manufacturer-authored document, distributor-hosted) |
| Depth camera on Lite3 (US site) | Intel RealSense D435i | `Lite3 integrates an Intel RealSense D435i depth camera and optional Livox or Leishen LiDAR modules for 3D mapping` | `https://www.deeprobotics.us/products/lite-3/` FAQ "How can researchers perform perception and SLAM development?" (saved `deeprobotics_us_lite3_page.html`, text lines 220-225) | primary |
| Perception host | NVIDIA Jetson Xavier NX (Pro/LiDAR) | `NVIDIA Jetson Xavier NX for its perception host (Pro/LiDAR versions)` | same page, text lines 152-157 | primary |
| Variant perception functions (EN brochure, 2025-07) | Basic/Venture: front/rear obstacle stop + visual following; Pro: + forward obstacle avoidance; LiDAR: + auto navigation | `Perception Functions   Front/Rear Obstacle Stop，Visual Following   Front/Rear Obstacle Stop，Visual Following   ...Forward Obstacle Avoidance   ...Auto Navigation` | `DEEPRobotics-Lite3-Quadruped-Robot-ENV-7.2.2025.pdf` (from deeprobotics.us), p2 | primary |
| Variant perception functions (CN one-pager, 2025-10) | 体验版/探索版: 前后停障、识别跟随; 专业版: + 前向避障; 激光版: + 自主导航 | `感知功能  前后停障、识别跟随  前后停障、识别跟随  前后停障、识别跟随 前向避障  前后停障、识别跟随 前向避障、自主导航` | `lite3_zhongwen_danye_yinshua_cn.pdf` (`https://deep-website.oss-cn-hangzhou.aliyuncs.com/app/lite3中文单页-印刷.pdf`, linked from deeprobotics.cn 下载中心), p2 | primary |
| Variant names (CN 2023 brochure) | 体验版 Lite3, 探索版 Lite3V, 专业版 Lite3P, 激光版 Lite3L | `体验版 (Lite3)  探索版 (Lite3V)  专业版 (Lite3P)  激光版 (Lite3L)` | `JueyingLite3_sanzheye_brochure_cn.pdf` (`https://deep-website.oss-cn-hangzhou.aliyuncs.com/file/绝影Lite3 三折页.pdf`), p1 | primary |
| Wide-angle camera FOV / resolution / fps / sensor / mount | **unverified** | A WebSearch result summary (search engine synthesis, no attributable page) stated "the 绝影 Lite3 features a 1080P wide-angle camera". No fetched manufacturer page or PDF contains the words 广角 / wide-angle / 1080P / FOV / 视场. | WebSearch `绝影 Lite3 广角相机 视场角 参数 deeprobotics.cn` | secondary, unattributed — NOT verified |
| Video stream used by people-tracking demo | h264 720p RTSP | `Hardware decoding based on DeepStream is used to obtain an h264-encoded 720p resolution rtsp video stream` (camera source not named) | Perception manual section 6.1, text L909-912 (PDF p24) | primary, but does not identify the camera |

Notes on the manufacturer pages:
- `https://www.deeprobotics.cn/robot/index/lite3.html` and
  `https://www.deeprobotics.cn/en/index/lite3.html` return HTTP 200 but the
  product-detail area is composed of images (`/public/static/robot/images/lite3/p1.jpg` … `p6.jpg`)
  and the only text is the purchase/warranty/privacy boilerplate; no spec
  text is present in HTML. Spec images were not OCR'd.
- `https://www.deeprobotics.cn/robot/index/support.html` (下载中心) lists
  `lite3中文单页-印刷.pdf` and `绝影Lite3 三折页.pdf` (both fetched) plus
  teaching videos; no Lite3 user manual PDF is listed.
- `https://shop.deeprobotics.us/products/lite-3` (WebFetch): fully rendered;
  five variants (Basic, Basic AI, Venture, Pro, LiDAR); no camera hardware text.
- The perception manual (58 pp.) only documents the D435i (section 4) and the
  LiDAR; no chapter on a wide-angle / fisheye / front camera.

## 3. Camera used by the InternVLA-N1 / InternNav authors on the real robot

Source (primary, authors): *InternVLA-N1: An Open Dual-System Vision-Language
Navigation Foundation Model with Learned Latent Plans*, Intern Robotics,
Shanghai AI Laboratory, dated 2025-9-11, 25 pp., downloaded from
`https://internrobotics.github.io/internvla-n1.github.io/static/pdfs/InternVLA_N1.pdf`
(link given in the InternNav README). Local copy `InternVLA_N1_technical_report.pdf`.

| Fact | Value | Verbatim quote | Where | Label |
|---|---|---|---|---|
| Real-robot camera model | Intel RealSense D455 (all three robots) | `We perform real-world experiments on a wheeled (Turtlebot4), quadruped (Unitree Go2) and humanoid (Unitree G1) robots. All robots are equipped with Intel Realsense D455 cameras, which are mounted at different height but angled downward at 15°.` | Section 5.5 "Real-World Experiments", p14 L31-33 | primary |
| Camera pitch | 15° downward | same quote | p14 L33 | primary |
| Camera mounting height | not stated numerically ("different height" per robot) | same quote; also `variation in camera height, vibration and tracking performance, InternVLA-N1 still finishes the VLN` | p14 L33, p15 L55 | primary (absence) |
| Real-robot FOV | not stated | no FOV/HFOV text in the report (grep `field of view|FOV|HFOV` -> none) | — | unverified |
| Training-data camera settings (sim) | height 125 cm with pitch 0/30 or 0/45, and 60 cm with pitch 15/15 or 30/30 | `R2R_125CM_0_30 = {"height": 125, "pitch_1": 0, "pitch_2": 30}` … `R2R_60CM_15_15 = {"height": 60, "pitch_1": 15, "pitch_2": 15}` (dict literals) | InternNav `internnav/dataset/internvla_n1_lerobot_dataset.py` L51-80, commit `7a5c62400ac45b313d9b709c740b64191556a242` (2026-03-10), shallow clone in scratchpad, not kept | primary (code) |
| Real-world image size and stream | 640 x 480 colour and depth at 30 fps, depth aligned to colour | `color_res: Tuple[int, int, int] = (640, 480, 30),  # (w,h,fps)` / `depth_res: Tuple[int, int, int] = (640, 480, 30)` / `self.align = rs.align(rs.stream.color)` | `internnav/env/utils/agilex_extensions/cam.py` class `AlignedRealSense` L11-15, L49 | primary (code) |
| Real-world ROS topics | `/camera/camera/color/image_raw`, `/camera/camera/aligned_depth_to_color/image_raw` | verbatim topic strings | `scripts/realworld/http_internvla_client.py` L203-204 | primary (code) |
| Intrinsics hard-coded in the server | fx = fy = 386.5, cx = 328.9, cy = 244 at 640 x 480 | `args.camera_intrinsic = np.array([[386.5, 0.0, 328.9, 0.0], [0.0, 386.5, 244, 0.0], ...` | `scripts/realworld/http_internvla_server.py` L90-92 | primary (code) |
| HFOV implied by those intrinsics | ≈ 79.2° horizontal, ≈ 63.7° vertical | 2·atan(320/386.5), 2·atan(240/386.5) | computed | derived — not stated by the authors; consistent with a D455 colour stream at 4:3 crop, but that is my inference |
| Go2 mount | a STEP file `assets/3d_printing_files/go2_stand.STEP` and `downwards_slope.3mf` exist; README says `Upload 3D printing files for Unitree Go2` | README News 2025/09 | InternNav README L46 | primary (artifact; geometry not extracted) |
| Community deployment guide | `https://github.com/cmjang/InternNav-deploy` (ShanghaiTech) | listed under "Community Deployment & Best Practices" | InternNav README L224-226 | secondary (not authors), not fetched |

The InternNav docs site (`https://internrobotics.github.io/user_guide/internnav/index.html`)
has no real-robot hardware page (sidebar: installation, simulation, dataset,
training, evaluation, tutorials, benchmarks).

## URLs that failed

| URL | Failure |
|---|---|
| `https://www.intelrealsense.com/wp-content/uploads/2020/06/Intel-RealSense-D400-Series-Datasheet-June-2020.pdf` | curl: `LibreSSL SSL_connect: SSL_ERROR_SYSCALL` (TLS handshake dropped; site appears offline/blocked from this host) |
| `https://www.intelrealsense.com/` (diagnostic) | same SSL_ERROR_SYSCALL, HTTP 000 |
| `https://www.intelrealsense.com/depth-camera-d435i/` | WebFetch: `Socket is closed` |
| `https://www.intelrealsense.com/depth-camera-d455/` | WebFetch: `Socket is closed` |
| `https://www.intel.com/content/dam/support/us/en/documents/emerging-technologies/intel-realsense-technology/Intel-RealSense-D400-Series-Datasheet.pdf` | HTTP 403 (HTML error body) |
| `https://cdrdv2-public.intel.com/841984/Intel-RealSense-D400-Series-Datasheet.pdf` | HTTP 403 (XML AccessDenied body) |
| `https://static.generation-robots.com/media/lite-3-user-manual.pdf` (guessed name) | HTTP 404 |
| `https://www.deeprobotics.cn/robot/index/lite3.html`, `/en/index/lite3.html` | HTTP 200 but spec content is image-only; no spec text (not JS-rendered, plain jQuery page) |

## Unresolved

1. Lite3 built-in wide-angle camera: FOV, resolution, frame rate, sensor,
   mounting — no primary text found. Next candidates (not fetched, budget):
   OCR the spec images `https://www.deeprobotics.cn/public/static/robot/images/lite3/p1.jpg`…`p6.jpg`;
   the official Lite3 *User Manual* (not listed in 下载中心; may ship with the
   robot or be on `docs.deeprobotics.cn`); the DEEP Robotics GitHub
   (`github.com/DeepRoboticsLab`) for a camera launch/config file; the
   Scribd copy "绝影Lite3感知开发手册 (beta) V2.1.1" is secondary and was not used.
2. Whether the wide-angle camera and the "识别跟随 / Visual Following" 720p RTSP
   stream are the same device.
3. InternVLA-N1 real-robot camera height per robot and the D455 stream
   resolution/FOV actually used (only 640x480 in code; no FOV text).
4. Intel product pages / ARK were unreachable; datasheet used instead.

## Files and SHA-256

Sizes: `lite3_zhongwen_danye_yinshua_cn.pdf` is 50 MB (print-resolution
artwork); consider a path-specific ignore + provenance note if it must not be
committed. All others are < 7 MB.

```
bc674a26f86a64de12ca6eb371eb4e068e73f7c6b293eae41606eb9860fe5a47  DEEPRobotics-Lite3-Quadruped-Robot-ENV-7.2.2025.pdf
d0156b43a82da64e809c6ae45a5b5d41f34d8697363534ed81f2e4407f38eaa4  Intel-RealSense-D400-Series-Datasheet-October-2025.pdf
f7075acc42efc645450a551838e33a1e967e9612b584842245cd15fd2e0c9e39  InternVLA_N1_technical_report.pdf
bfdf1016f9835351f30ad08db9f9cc6662129bb2aa06c9b859df69f459c97bd8  JueyingLite3_sanzheye_brochure_cn.pdf
525a74d680ab13250008d36a34b67b215ada528577f11691df0b81f619b303a2  lite-3-perception-development-manual.pdf
d4f881528fa6d2959962268cf2e8f1cba46bd1349a3702b3dfd42197b7f2ba0b  lite3_zhongwen_danye_yinshua_cn.pdf
5b85f39f88328ef91befd5e6ad3afdbcfbd4797c4867c9c7f64e0b3ff09564c3  DEEPRobotics-Lite3-Quadruped-Robot-ENV-7.2.2025.txt
3fe2d822f277864931d026a95c894e9cd0c5080eccd5bb938c956886670f39bf  Intel-RealSense-D400-Series-Datasheet-October-2025.txt
e9c1379e37a2980d228726a51f19d42cf4c9056289c3a0860182c91a6dece931  InternVLA_N1_technical_report.txt
301da0109efd81e62cbabcc8317fa2f3e53337e5cf19d2e2c6db9fc601fe1dec  JueyingLite3_sanzheye_brochure_cn.txt
df5763cd5e28d4f6ae8fe821a8194ed66d29bfdfef253bd2f06ea67c6c4c5d51  lite-3-perception-development-manual.txt
6ece7ceb1893108f571b83f88efb1daf6a17337a4d0459f7bc5df8d01c68ae10  lite3_zhongwen_danye_yinshua_cn.txt
f94fe660ecbd3fb63ff8e0b7b1f74889a43dc703a6321767e0daea78c515bd55  deeprobotics_cn_en_lite3_page.html
4db582fce60b8f0cb3914b108a0f33ce9c7a7657f9d6007967912933eda02fb4  deeprobotics_cn_lite3_page.html
e3dac1f9de63c8bb8d1cdadbaca80adf58d8d897545ed99206d228c3c1e83419  deeprobotics_cn_support_page.html
6c12b6fafa03d9c110387f4a7ef8e961f455ac6407463be9c3fecd2927b5f7b5  deeprobotics_us_lite3_page.html
```

Same list in `SHA256SUMS.txt` (verify with `shasum -a 256 -c SHA256SUMS.txt`).
The `.txt` files are `pdftotext -layout` outputs; `.html` files are raw
`curl` captures. The InternNav shallow clone lives only in the session
scratchpad and is not part of this directory; the commit hash above pins it.

## Fetch log (25 of 25)

1. curl intelrealsense.com June-2020 datasheet — SSL fail
2. curl generation-robots perception manual — OK
3. WebFetch intelrealsense D435i page — socket closed
4. WebFetch intelrealsense D455 page — socket closed
5. WebFetch deeprobotics.us/products/lite-3 — OK
6. WebFetch github.com/InternRobotics/InternNav — OK
7. curl intelrealsense.com root (diag) — SSL fail
8. curl intel.com datasheet — 403
9. curl deeprobotics.us/products/lite-3 (raw HTML) — OK
10. git clone --depth 1 InternNav — OK (7a5c624)
11. WebSearch "Intel RealSense D400 Series Product Family Datasheet pdf D435i D455 RGB FOV" — OK
12. WebSearch "绝影 Lite3 广角相机 视场角 参数 deeprobotics.cn" — OK
13. WebFetch internrobotics.github.io user_guide index — OK
14. curl realsenseai.com October-2025 datasheet — OK
15. curl cdrdv2-public.intel.com datasheet — 403
16. curl deeprobotics.us Lite3 brochure PDF — OK
17. curl OSS 绝影Lite3 三折页.pdf — OK
18. curl deeprobotics.cn/robot/index/lite3.html — OK (image-only specs)
19. curl deeprobotics.cn/en/index/lite3.html — OK (image-only specs)
20. WebFetch shop.deeprobotics.us/products/lite-3 — OK
21. WebSearch InternVLA-N1 arXiv / D455 — OK (arXiv 2512.08186 noted, not fetched)
22. curl InternVLA_N1.pdf tech report — OK
23. curl deeprobotics.cn/robot/index/support.html — OK
24. curl generation-robots lite-3-user-manual.pdf (guess) — 404
25. curl OSS lite3中文单页-印刷.pdf — OK

## 2b. Wide-angle camera: GitHub, papers, forums (round 2, 2026-09-10)

- Fetch window: 2026-09-10 ~15:10-15:40 UTC. Tools: `gh` (repo list, code
  search API), shallow / sparse `git clone` into the session scratchpad,
  `curl` + `pdftotext -layout` + `pdftoppm` (poppler), `WebFetch`, `WebSearch`.
- Trust labels for this section (as requested by the task): `primary` =
  DEEP Robotics official (own sites, own docs, `github.com/DeepRoboticsLab`,
  manufacturer-authored manuals hosted by a distributor);
  `secondary-technical` = third-party code/logs with measured or configured
  values; `secondary-prose` = distributor / forum / press text without
  measurement; `derived` = computed by me from a quoted number. Nothing below
  is promoted to `verified`.
- Budget: the 30-operation target was overrun by one (31 network operations,
  plus one sparse-checkout completion of an already-counted clone); log at
  the end of this section.

### 2b.1 Findings

| # | Fact | Value | Verbatim quote | Source (URL; repo path @ commit) | Trust |
|---|---|---|---|---|---|
| 1 | Wide-angle camera exists on Lite3 Pro; counted in the perception system | `Wide Angle Camera ×1` (with `Ultrasonic Radar ×2`, `Depth Camera ×1`, `AI Computer NVIDIA Jetson Xavier NX`) | `Perception System` / `Wide Angle Camera                                     ×1` / `Ultrasonic Radar                                      ×2` / `Depth Camera                                          ×1` / `AI Computer                                           NVIDIA Jetson Xavier NX` | *Jueying Lite3 Pro User Manual V2.0.0-0*, dated `2026/02/27`, DEEP Robotics, hosted by generation-robots: `https://static.generation-robots.com/media/deep-robotics-lite3-user-manual.pdf` (35 pp.), §1.4 "Main Specifications", text L244-252 (PDF p9). Local copy `deep-robotics-lite3-user-manual.pdf` / `.txt` | primary |
| 2 | Mounting position (qualitative) | On the front face of the head, below the Depth Camera (which sits on a bracket on top of the front) and above the front Ultrasonic Radar; a second Ultrasonic Radar is on the rear face | Part-name diagram labels `Depth Camera`, `Wide Angle Camera`, `Ultrasonic Radar` pointing at the head front, top-to-bottom in that order | same manual, §1.3 "Part Name", PDF p8; rendered page kept as `deep-robotics-lite3-user-manual_p8_part_name.png` | primary (diagram only; no dimensions, no pitch) |
| 3 | FOV / resolution / fps / sensor / lens in the official manual | **absent** | The only camera-related sentences are `㉚ Video Stream            Show the live stream of robot camera` (App control page, L644), `Q3: What if the video stream gets stuck after the robot falls?` (L1106) and the warranty row `Wide Angle Camera, Ultrasonic Radars, Control System, Other Electronic Components  One year` (L1166-1168). `grep -i "fov\|resolution\|fps\|1920\|1080\|130"` finds no camera spec. | same manual | primary (absence) |
| 4 | The RTSP stream `rtsp://<motion host>:8554/test` *is* the wide-angle camera | yes, per the motion-host interface document V1.0.7 | `若运动主机 IP 地址为 \`192.168.1.120\`，则拉取机器人广角相机视频流的地址为 \`rtsp://192.168.1.120:8554/test\`。若运动主机 IP 地址为 \`192.168.2.1\`，则拉取机器人广角相机视频流的地址为 \`rtsp://192.168.2.1:8554/test\`。` Version table: `V1.0.4 | 更正拉流地址 | 2023-10-17`, `V1.0.7 | 通信地址说明同步 GitHub | 2024-05-15`; header: `原手册版本：V1.0.7，发布日期：2024-05-15。适用运动程序：jy_exe_87(20230531)` | Markdown transcription of *绝影 Lite3 运动主机通讯接口 (beta) V1.0.7* in `github.com/Mplus0/Dog-Machine-2026`, path `src/message_transformer/docs/lite3_motion_host_udp_interface_beta_v1_0_7.md` L1-3, L18-27, L349 @ `65813801724597f6a6a47dfbdf7ed505c9f6b226`. Same sentence in `github.com/laojiahuo2003/lite3_sdk` `运动主机通讯接口.md` L296 @ `cea5a5593cceea21501222644551d7b8ffadb93f`. The original PDF is on Scribd (`https://www.scribd.com/document/838272320/...`) but WebFetch returned only the page description. Local copy: `github_Mplus0_Dog-Machine-2026_6581380_lite3_motion_host_udp_interface_beta_v1_0_7.md` | secondary-technical (third-party transcription of an official document; two independent transcriptions agree) |
| 5 | Stream codec | H.264 over RTSP | `gst-launch-1.0 rtspsrc location=rtsp://192.168.1.120:8554/test ! rtph264depay ! h264parse config-interval=1 ! nvv4l2decoder ! ...` (pull.sh L5); `pipeline_str = "rtspsrc location=rtsp://192.168.1.120:8554/test ! rtph264depay ! h264parse ! nvv4l2decoder ! ... ! videoscale ! video/x-raw,width=1280,height=720 ! ..."` (pull.py L19); GStreamerWrapper.py L24 scales to `width=640,height=360` | `github.com/DeepRoboticsLab/Lite3_Track` `src/test/pull.sh`, `src/test/pull.py`, `src/GStreamerWrapper/GStreamerWrapper.py` @ `28db02f3c91b3cdfbcba51a0645fd8daffbf683e`. Local copies `github_DeepRoboticsLab_Lite3_Track_28db02f_*` | primary (official code). Note: the `videoscale` targets are downstream resizes, not the native size; the commented-out `v4l2src device=/dev/video0 ... YUY2,width=640,height=480` lines are for a USB camera on the Jetson, not this stream. |
| 6 | Stream codec + resolution as described by the perception manual | h264, 720p | `Hardware decoding based on DeepStream is used to obtain an h264-encoded 720p resolution rtsp video stream` (round 1, §6.1). Combined with rows 4-5 this 720p H.264 RTSP stream is the wide-angle camera stream. | `lite-3-perception-development-manual.pdf` text L909-912 | primary (camera identity is cross-referenced through row 4, which is secondary-technical) |
| 7 | Decoded RTSP frame size, measured on the robot | 1280 x 720 (BGR) | `| camera input | \`rtsp://127.0.0.1:8554/test\` |` / `| actual RTSP frame size | 1280x720 BGR |`; `vendor UVC camera -> vendor local RTSP publisher`; `The deployment consumes the existing vendor RTSP publisher. It does not take over \`/dev/video0\` or change the vendor GStreamer process.`; README: `10 1280x720 frames, zero camera read errors` (2026-08-25, on the motion host) | `github.com/armwaheed/mappo-arm-cloud-physical-ai` `lite3-chair-bin-live-readiness-20260825.md` L11-16, L49-52 and `robot-stack/deep_robotics/lite3/README.md` L521-522, L537-538 @ `dc4c50c6e11c00776f4a49c40dcffed4b8d40212`. Local copy `github_armwaheed_..._lite3-chair-bin-live-readiness-20260825.md` | secondary-technical (measured; robot = Lite3 **Venture**, `platform: deep-robotics-lite3-venture`) |
| 8 | Intrinsic matrix of the wide-angle camera at 1280 x 720 | fx 508.74, fy 494.93, cx 640.90, cy 339.51; distortion (OpenCV k1,k2,p1,p2,k3) = -0.01785, -0.03947, 0.00526, 0.00407, 0.00858; RMS 2.94 px | `"camera_matrix": [[508.74343769196315, 0.0, 640.8972102871645], [0.0, 494.93297523678166, 339.5051069783413], [0.0, 0.0, 1.0]]`, `"measured": "2026-09-01, cv2.calibrateCamera over 26 ArUco grid-board views (2x3, 75 mm markers, ids 10-15) captured from this robot's own RTSP feed"`, `"limits": "inherits the pinhole fit: RMS 2.94 px, fx/fy 1.028, no coverage of the frame's top third..."` | same repo, `robot-stack/deep_robotics/lite3/visual_nav/lite3_front_camera_rectify_20260901.json` @ `dc4c50c`. Local copy `github_armwaheed_..._lite3_front_camera_rectify_20260901.json` | secondary-technical (measured) |
| 9 | Lens projection type | nearly rectilinear (pinhole + polynomial distortion), **not** fisheye/equidistant | `"why_pinhole": "cv2.fisheye.calibrate (equidistant, the shared stack's model) gave RMS 52.9 px on the same correspondences; pinhole+distortion gave 2.9. This lens is nearly rectilinear, not equidistant."`; `"The raw lens is nearly rectilinear (fx 508.7, fy 494.9, HFOV 103 deg)."` | same JSON; and `lite3_front_camera_equidistant_20260901.json` `calibration_limits[1]` | secondary-technical (measured) |
| 10 | HFOV / VFOV implied by row 8 | HFOV ≈ 103.0°, VFOV ≈ 72.1° (pinhole part; the k1/k2 terms are small and negative, so the true edge angle is within a few degrees) | 2·atan(640/508.74) = 103.04°, 2·atan(360/494.93) = 72.07°. The third party quotes `HFOV 103 deg` for the same numbers. | computed from row 8 | derived |
| 11 | Caution: `hfov_deg 134.34` in the same repo is **not** the lens FOV | 134.34° describes a synthetic equidistant re-projection (`focal_out_px 545.92`, 2·(640/545.92) rad = 134.3°), and an earlier shipped block `{"focal_px": 469.63, ..., "hfov_deg": 156.16, "width": 1280, "height": 720}` is flagged by the authors as self-contradictory (`focal_px implies a 107.46° field, hfov_deg says 156.16° — 48.7° apart`) and superseded | `"THIS FILE IS ONLY TRUE WITH --camera-rectify. focal_px 545.9 describes the SYNTHETIC equidistant projection ... not the raw lens."`; `"SUPERSEDES focal_px 469.63 (shipped), 888.85 (spin), 660 and 392.4 (both fitted by hand on 2026-08-31)."` | `lite3_front_camera_equidistant_20260901.json` L3-6; `LITE3-COMMISSIONING-PROMPT.md` L275-284 @ `dc4c50c` | secondary-technical (authors' own caveat) — do not quote 134° or 156° as the camera FOV |
| 12 | Mounting height above ground (Venture, standing) | 0.37 m standing, 0.115 m prone (measured); the shipped 0.40 m value is called wrong | `\`height_m\` **0.40** contradicts the measured **0.37** standing / **0.115** prone;` | `LITE3-COMMISSIONING-PROMPT.md` L281 @ `dc4c50c` | secondary-technical (measured, no method given) |
| 13 | Mounting pitch | two third-party figures disagree: "fixed ~11°" (commissioning note) vs `pitch_rad -0.2625` = -15.04° (two-station elevation fit, residual -0.57°) | `**no pitch**, where the mount is a fixed **~11°**;` / `"pitch_rad": -0.262519298362` + `"pitch_rad and height_m are the physical mounting ... carry over from the two-station elevation fit (residual -0.57 deg)."` | `LITE3-COMMISSIONING-PROMPT.md` L282; `lite3_front_camera_equidistant_20260901.json` L5, L15 @ `dc4c50c` | secondary-technical (two inconsistent measurements; sign = downward) |
| 14 | Forward offset from torso origin | not found in any source | — | — | unresolved |
| 15 | Distributor spec row | `horizontal FOV 130°, 1920×1080@30fps` | `1 set of built-in wide-angle camera: horizontal FOV 130°, 1920×1080@30fps`; also `Improved FPV image transmission, less lag errors` and `2 sets of integrated front and rear automatic stopping ultrasonic radars` | Leobotics (FR distributor) Lite3 Pro page `https://en.leobotics.com/comparateur-robot/robot-quadrupede-jueying-lite3-pro-deep-robotics-inspection-securite` (WebFetch 2026-09-10) | secondary-prose. The WebSearch engine attributed the same figure to the Leobotics LiDAR/Basic-Venture pages and RobotShop, but only the Pro page was fetched; RobotShop returned HTTP 403. |
| 16 | Consistency of row 15 with row 8 | **inconsistent** | A rectilinear 130° HFOV at 1280 px width would need fx ≈ 640/tan(65°) ≈ 298 px; measured fx is 509 px (103°). Even the diagonal from row 8 is only ≈ 111°. So 130° is either a nominal lens spec before sensor crop / a diagonal figure / a marketing number, or the RTSP stream is a cropped or differently scaled view of a 1920x1080 sensor. Cannot be resolved from the sources found. | rows 8, 15 | derived (comparison) |
| 17 | Latency of the RTSP stream | not measured by any source found; third parties only warn about decoder buffering | `OpenCV timestamps a network frame when it is decoded, not when its shutter fired. Measure end-to-end frame age on the installed endpoint; an RTSP decoder queue can otherwise make fresh-looking frames old.`; frame-server measured JPEG size only: `one GET returns HTTP 200 with a **127-135 KB** JPEG at the default quality` | mappo `README.md` L422-424, `visual_nav/lite3_frame_server.py` L15-17 @ `dc4c50c` | secondary-technical (absence) |
| 18 | V4L2 device / UVC name / sensor model | not found; only that the vendor GStreamer publisher owns `/dev/video0` (same as the project's `start_stream.sh`) | `On the staged motion host, \`/dev/video0\` is already owned by the vendor GStreamer publisher.`; readiness doc calls it `vendor UVC camera` | mappo `README.md` L521 @ `dc4c50c` | secondary-technical; no `v4l2-ctl --list-formats-ext` output found anywhere |
| 19 | Official URDF / MJCF / USD camera link | **none** | `deep_robotics_model/Lite3/urdf/Lite3.urdf` links: TORSO, {FL,FR,HL,HR}_{HIP,THIGH,SHANK,FOOT} only; `Lite3/mjcf/Lite3.xml` has only viewer cameras `front_camera`/`side_camera` (`mode="track" fovy="90.0"`, placed 2 m from the body — scene cameras, not sensors); `strings Lite3_sensor.usd` has no `camera`/`fov` | `github.com/DeepRoboticsLab/deep_robotics_model` @ `549eb9ac08ab0674ad388202f0a276a1b140833b` | primary (absence) |
| 20 | Official ROS package camera node | none for the wide-angle camera; only a RealSense liveness check | `realsense_ = std::make_shared<Sensor<sensor_msgs::msg::PointCloud2>>(nh, "realsense", "/camera/depth/color/points", ...)` | `github.com/DeepRoboticsLab/Lite3_ROS` `src/transfer/src/SensorChecker.cpp` L82 @ `e4ab5dc1c7f3ff46274162a1ef302253936578aa` | primary (absence) |
| 21 | Other official repos | `Lite3_LLM`, `Lite3_Navigation` (shallow clones) contain no `rtsp`/`video0`/`camera_info`/`8554` strings outside vendored third-party code; org has 27 repos (`gh repo list DeepRoboticsLab`), none named for the camera | — | `github.com/DeepRoboticsLab/Lite3_LLM` @ `6af0356f294727a1b14ce89cacd3581e86020d4e`, `Lite3_Navigation` @ `b091cee10a11ea8b43459f906a91ff07f5dbb417` | primary (absence) |
| 22 | Third-party clients (no spec, confirm URL/port only) | default `rtsp://192.168.1.120:8554/test` or `rtsp://192.168.2.1:8554/test` | `RTSP_URL = f"rtsp://{ROBOT_IP}:8554/test"`; `DEFAULT_RTSP_URLS = ["rtsp://192.168.2.1:8554/test", "rtsp://192.168.2.1:8554/live", "rtsp://192.168.2.1:554/live", "rtsp://192.168.1.120:8554/test"]`; `| 8554/tcp | 运动主机 RTSP 广角相机流 | 厂家文档 / 去年工程 |` | `NestorKrdona/lite3-local-web-control` `app.py` L35 @ `a1a97095b7bb27d29105fd061f023b9bc362414f`; `liusiqi05/Lite3_dog` `gesture_control.py` L300-304 @ `5001640243ba9ccf3615ded0d274a1cdba0667f3`; `Mplus0/Dog-Machine-2026` `README_NETWORK_TOPOLOGY.md` L224 @ `6581380`; `laojiahuo2003/lite3_sdk` `lite3_sdk/camera_client.py` L22 @ `cea5a55` | secondary-technical (configuration only) |
| 23 | Distributor brochure and product pages | no camera row | generation-robots brochure `https://static.generation-robots.com/media/brochure-lite-3-deep-robotics.pdf` (2 pp., image-only; rendered and read): parameter table Basic/Venture/Pro/LiDAR with PERCEPTION = front & rear auto-stop / object following / (Pro+) obstacle avoidance / (LiDAR) auto-navigation, plus `Enhanced FPV image transmission, fewer lag errors`; generation-robots product page: no camera spec, links the user manual (row 1), the brochure, and a DingTalk "Development Manual" (`https://alidocs.dingtalk.com/i/p/OlnXRxOLAljEbGLp/docs/YndMj49yWjPnDl2nIM65wX17J3pmz5aA`, not fetched). `deeprobotics.cn/robot/wap/product1.html` is image-only (1.6 kB of text, no 广角/相机). | — | primary (absence) for the manufacturer artwork; brochure not kept (1.9 MB, no camera fact) |
| 24 | Papers / theses using the Lite3 head camera with a calibration | none found | WebSearch "Jueying Lite3 quadruped onboard camera field of view fisheye paper" returned only distributor pages and unrelated patents; GitHub code search `jueying camera_matrix` = 0 hits | — | unresolved |

### 2b.2 Single most credible figures (all remain secondary)

- Stream: H.264 RTSP at 1280 x 720 (primary code for the codec, primary
  manual for "720p", third-party measurement for the decoded size), sourced
  from the vendor GStreamer publisher on `/dev/video0` of the motion host.
- Lens: nearly rectilinear, HFOV ≈ 103° / VFOV ≈ 72° at 1280 x 720
  (secondary-technical, one ArUco calibration of one Lite3 Venture, RMS
  2.94 px; `derived` from fx/fy). The distributor's "130°, 1920x1080@30fps"
  (secondary-prose) is not consistent with that calibration.
- Mount: front face of the head, below the D435i bracket (primary diagram);
  ≈ 0.37 m above ground when standing, pitched down ≈ 11-15° (secondary-technical,
  two inconsistent third-party numbers, Venture variant).

### 2b.3 Queries and URLs tried (31 network operations + 1 completion)

| # | Operation | Outcome |
|---|---|---|
| 1 | `gh repo list DeepRoboticsLab --limit 100` | 27 repos listed |
| 2-6 | `git clone --depth 1` DeepRoboticsLab/{Lite3_ROS, deep_robotics_model, Lite3_Track, Lite3_LLM, Lite3_Navigation} | OK; commits in rows 5, 19-21 |
| 7 | `gh api search/code q="lite3 rtsp 8554"` | 633 hits; useful: armwaheed/mappo-arm-cloud-physical-ai, laojiahuo2003/lite3_sdk, liusiqi05/Lite3_dog, NestorKrdona/lite3-local-web-control, Mplus0/Dog-Machine-2026 |
| 8 | `gh api search/code q="lite3 camera_info"` | 1732 hits, none Lite3-specific (DeepRoboticsLab/fast-livo2-deep-robotics README only) |
| 9 | `gh api search/code q="jueying camera_matrix"` | 0 hits |
| 10 | `gh api search/code q="lite3 usb_cam"` | 219 hits, only SwanChann/visualnav-transformer relevant (uses a generic `/usb_cam/image_raw` LoCoBot stack, no Lite3 camera value) |
| 11 | `gh api search/code q="deeprobotics video0"` | 12 hits; only mappo README relevant |
| 12 | `gh api search/code q="start_stream.sh rtsp 8554 test"` | 5 hits, none Lite3 |
| 13 | WebSearch `绝影 Lite3 广角相机 视场角 分辨率 参数` | no spec; Scribd copies of the perception manual V2.1.1 and interface doc V1.0.7 |
| 14 | WebSearch `"Lite3" DeepRobotics quadruped wide-angle camera 130° 1920x1080` | engine summary attributes 130°/1920x1080@30fps to RobotShop and Leobotics pages |
| 15 | WebSearch `Jueying Lite3 quadruped onboard camera field of view fisheye paper` | no paper |
| 16 | WebSearch `Lite3 rtsp 8554 test 云深处 摄像头 视频流 192.168.1.120` | nothing Lite3-specific |
| 17-19 | `git clone --depth 1` laojiahuo2003/lite3_sdk, liusiqi05/Lite3_dog, NestorKrdona/lite3-local-web-control | OK (row 22) |
| 20 | sparse clone armwaheed/mappo-arm-cloud-physical-ai (`--filter=blob:none`) | OK @ dc4c50c; first `sparse-checkout set` failed on file paths, later completed with `robot-stack/deep_robotics/lite3` (counted as completion of this clone) |
| 21 | sparse clone Mplus0/Dog-Machine-2026 `src/message_transformer/docs` | OK @ 6581380 (row 4) |
| 22 | sparse clone SwanChann/visualnav-transformer | OK @ 0f1284acea885d661f171413d58f713ef6c00767; no Lite3 camera value |
| 23 | WebFetch `https://www.robotshop.com/products/deep-robotics-lite3-pro-quadruped-robot` | HTTP 403 |
| 24 | WebFetch Leobotics Lite3 Pro page | OK (row 15) |
| 25 | WebFetch `https://www.generationrobots.com/en/404276-lite-3-quadruped-robot.html` | OK; gave the user-manual and brochure URLs (rows 1, 23) |
| 26 | WebFetch Scribd `绝影Lite3运动主机通讯接口 (beta) V1.0.7` | only page description, no body text |
| 27 | curl `https://static.generation-robots.com/media/deep-robotics-lite3-user-manual.pdf` | HTTP 200, 7.0 MB, 35 pp. (round 1 had guessed `lite-3-user-manual.pdf` -> 404) |
| 28 | curl `https://static.generation-robots.com/media/brochure-lite-3-deep-robotics.pdf` | HTTP 200, 1.9 MB, image-only |
| 29 | curl `https://deeprobotics.cn/robot/wap/product1.html` | HTTP 200, image-only mobile page |
| 30 | WebSearch `"Lite3" 云深处 "广角相机" 水平视场角 130° 1920×1080@30fps` | Chinese press/Zhihu launch articles listed, none showing the figure in the snippet; not fetched |
| 31 | WebSearch `Lite3 "wide-angle camera" 130° 1920×1080 30fps` restricted to deeprobotics.us/.cn/shop | no official page carries the figure; surfaced `https://www.deeprobotics.us/wp-content/uploads/2025/08/Jueying-Lite3-AI-User-Manual-V1.0.3-0.pdf` (Lite3 AI variant manual, 2025/5/20) — not fetched |

Not attempted (budget): RobotShop via curl with a browser UA; Leobotics
LiDAR/Basic pages; the Sohu/Zhihu/leaderobot 2023 launch articles; the
`deeprobotics.cn/public/static/robot/images/lite3/p1..p6.jpg` spec images
(no OCR tool on this host; `Read` could view them if fetched); the DingTalk
development manual; the Lite3 AI user manual on deeprobotics.us; ROS
Answers/Discourse (no Lite3 hits appeared in any search).

### 2b.4 Unresolved after round 2

1. Native sensor resolution / frame rate / module or UVC name of the
   wide-angle camera: no primary or measured source. Only the distributor's
   "1920x1080@30fps" (secondary-prose) vs the vendor stream at 1280x720.
   A `v4l2-ctl --list-formats-ext -d /dev/video0` on the project robot would
   settle it (secondary-technical, own measurement).
2. FOV: measured ≈ 103° x 72° at 1280x720 on one Venture (secondary-technical)
   vs 130° (secondary-prose). No primary figure anywhere.
3. Mount geometry relative to the torso origin (forward offset, exact
   height, pitch): only third-party ground-height (0.37 m) and two
   conflicting pitch values (≈ 11° vs 15°); no official drawing.
4. Stream latency: not measured by anyone found.
5. Whether the Pro/LiDAR wide-angle camera is the same module as the
   Venture one (the manual's parts list and the brochure's "object
   following" row imply every variant has it, but no source says the module
   is identical).
6. Primary leads not yet fetched: the Lite3 AI user manual V1.0.3-0 on
   deeprobotics.us; the DingTalk development manual; the deeprobotics.cn spec
   images.

### 2b.5 Files added in round 2 (SHA-256 appended to `SHA256SUMS.txt`)

```
3ecb1eea94d9781d67076bd7a04acc275425dd5f1b2457deb17ef53f0c2ab7ee  deep-robotics-lite3-user-manual.pdf
adc36503da02b780c58d1ffc44539f666e57df07ff6d930bacdab726ad47eb09  deep-robotics-lite3-user-manual.txt
3e22a6c5aa7040be1ffdd1ae8c92f266f4e1bc9b7c863485c7d4060f2a0f0e3b  deep-robotics-lite3-user-manual_p8_part_name.png
2519ae627ee1051ce59119512b6ef7d2dad37b4cf9b2cd4050771635e608ba32  github_DeepRoboticsLab_Lite3_Track_28db02f_src_test_pull.py
4c1d7db67d334c5f6f79813dec7d185588aa96ddec59d80576b37754d77e0f7c  github_DeepRoboticsLab_Lite3_Track_28db02f_src_test_pull.sh
3d9fea051b68f78c2d32ad7ce806b938b7e3fab9ea4842dcec8f005f331e4af3  github_DeepRoboticsLab_Lite3_Track_28db02f_src_GStreamerWrapper_GStreamerWrapper.py
f04529012758984b6781558cfd9f42552a166bf1e04fbb9daa66e20759200fc8  github_armwaheed_mappo-arm-cloud-physical-ai_dc4c50c_lite3-chair-bin-live-readiness-20260825.md
a05bd29cefea49b29bc112c8375198f5bd6cd3e4119ba5a1f36dcd17fdc85c30  github_Mplus0_Dog-Machine-2026_6581380_lite3_motion_host_udp_interface_beta_v1_0_7.md
e7d2b9283695cd3fa07a936fb8225ca878562b38ff036a893af29fce7b9900b8  github_armwaheed_mappo-arm-cloud-physical-ai_dc4c50c_lite3_front_camera_rectify_20260901.json
1f9c47e90228be0070dc8fef3e9faee8992d5a7ef7327124ac88c73d0785389f  github_armwaheed_mappo-arm-cloud-physical-ai_dc4c50c_lite3_front_camera_equidistant_20260901.json
```

Total new bytes ≈ 7.1 MB. The user manual `.txt` is `pdftotext -layout`
output; the `.png` is `pdftoppm -r 110` of PDF page 8. Third-party files are
verbatim copies at the stated commits (licences: mappo files carry
`Apache-2.0` headers in code; the Markdown transcriptions carry none — treat
as quotation for research use). The shallow clones live only in the session
scratchpad.

## 2c. Prior art: Lite3 head camera in robot models (2026-09-10)

Question: has anyone modelled the Lite3 built-in wide-angle head camera (or
any camera on the Lite3 head/torso) in a robot description file, and with what
pose? Method: GitHub code search, raw-file grep of every Lite3 URDF/xacro/MJCF
the searches surfaced, DeepRoboticsLab org enumeration, one shallow clone, three
web searches, two paper fetches. Labels: primary = DEEP Robotics official;
secondary-technical = third-party model file or measurement; secondary-prose =
text only.

### 2c.1 Answer

**Nobody models the built-in wide-angle head camera in any URDF, xacro, SDF,
MJCF or USD found.** Every camera element that exists on a Lite3 description is
either (a) a MuJoCo viewer/chase camera 2 m away from the torso (vendor), or
(b) an add-on Intel RealSense D435/D435i bolted to the top of the torso
(third-party). The armwaheed repository, the only source with a measured
built-in-camera pose, keeps that pose in JSON (already saved in 2b), not in a
model file.

### 2c.2 Evidence: searches that returned nothing

GitHub code search, all 0 hits: `lite3 camera_link`, `lite3 camera_joint`,
`jueying camera urdf`, `lite3 xacro camera`, `lite3 gazebo camera plugin`,
`deeprobotics camera` (ext urdf / xacro), `lite3 horizontal_fov`,
`lite3 fovy`, `lite3_description camera`, `jueying camera`, `lite3 camera`
(ext xml / usda), `Lite3 camera sensor` (ext xacro). Extension-scoped
`lite3` ext:urdf and ext:xacro each returned 40 files (cap), ext:sdf 0.

Raw-file grep (`camera`, later also `d435|realsense`) of 38 Lite3 model files
from 30 repositories, all with **no camera**: DeepRoboticsLab/deep_robotics_model
`Lite3/urdf/Lite3.urdf`; DeepRoboticsLab/Lite3_VMC (6 xacro: Gazebo IMU + 4
foot-contact sensors only); DeepRoboticsLab/Lite3_rl_training; fan-ziqi/robot_lab
and rl_sar_zoo; legubiao/quadruped_ros2_control `urdf/robot.urdf` and
`robot.xacro`; TopHillRobotics/quadruped-robot lite3 xacro; shanchaicn/
Lite3_Model_Control and its copy mobilio7/Lite3_simulation; syedshaihan/
deeplitesim; xyz2555/Lite3_ws `Lite3_ros.urdf`; DedSecer/lite_cog and
zhshui/slma_nav (navigation stacks, Lite3.urdf unchanged); ecstayalive/
VisionServoGrasp; causiniris/matrix_robotac_2026; openverse-orca/OrcaGym_Assets;
LuwuDynamics/luwu_mjlab (`lite3.xml` + urdf); twilgrove/legged_control_ros2_humble;
fiveages-sim/robot-descriptions-quadruped; enffft/3d-nav; arclab-hku/MGDP
`lite3_base.urdf`; Tian-Shu-Huang/parkour_lite3; priest-yang/ABS-DeepRobotics-Lite3
and Deep-Tracking-Control; linqi-ye/robot-universe; Mr-Zqr/rl_sar_zqr.

Vendor org (primary, 27 repos enumerated 2026-09-10; trees of 12 grepped):
`Lite3_ROS` (ros2-foxy @ e4ab5dc, 16 files, no description package),
`Lite3_Navigation`, `Lite3_SLAM`, `Lite3_Track`, `Lite3_LLM` (no model files),
`rl_training` (Isaac Lab; `deeprobotics_lite3/rough_env_cfg.py` has no camera),
`deep-robotics-simulation` (MuJoCo, DR02 only), `deep-robotics-sdk2`
(`CAMERA.md` exists but only for `dr02_pro`), `Lite3_rl_deploy` and
`sdk_deploy` (MJCF, see below). `Lite3/usd/Lite3.usd` in deep_robotics_model is
a 1454-byte USDC crate with no `camera` string. No DeepRobotics camera
calibration yaml exists in any SDK repo.

### 2c.3 Evidence: camera elements that do exist

| # | Source / label | File (saved copy) | Parent | Pose | Optics | Measured? |
|---|---|---|---|---|---|---|
| V1 | DeepRoboticsLab/deep_robotics_model @ `549eb9a` (BSD-3), **primary** | `Lite3/mjcf/Lite3.xml` lines 148-149 | body `TORSO` | `front_camera` pos `0 2.0 0.5`, `side_camera` pos `-2.0 0 0.5`, both `mode="track"` | `fovy="90"` | n/a: viewer/chase cameras 2 m from the torso, not a sensor |
| V1' | DeepRoboticsLab/sdk_deploy @ `2367375` (BSD-3), **primary** | `src/Lite3_sdk_deploy/Lite3_description/lite3_mjcf/mjcf/Lite3.xml` | same | identical camera lines; file differs from V1 only in mesh paths (lines 27-39) | same | same |
| T1 | legubiao/quadruped_ros2_control @ `5434c58` (Apache-2.0), **secondary-technical** | `descriptions/deep_robotics/lite3_description/xacro/gazebo.xacro` lines 274-282, macro in `libraries/gz_quadruped_playground/models/D435/model.xacro` | link `base` (xacro root, joined to `TORSO`) | RealSense D435 `xyz="0.23 0 0.06"` `rpy="0 0.1 0"` (pitch 0.1 rad = 5.7 deg down); gated by `EXTERNAL_SENSORS` arg, default `false` | Gazebo Sim `rgbd_camera`, `horizontal_fov 1.0472` (60 deg), 640x480, fx = fy = 554.25469, cx 320.5, cy 240.5, noise sd 0.007 | no comment. Go2 in the same repo uses `xyz="0.28 0 0.093"` with the same `rpy`, so the 0.1 rad pitch is a shared default and the xyz is an unexplained per-robot guess |
| T2 | LaoGordon/lite3_gazebo_classic @ `f42239b` (no licence file; ROS 2 Gazebo-Classic port of T1's stack, not a GitHub fork), **secondary-technical** | `lite3_description/xacro/sensors/load_sensors.xacro` + `sensors/d435i_sensor.xacro`, included unconditionally from `robot.xacro` line 91-92 | `TORSO` (`load_all_sensors parent="TORSO"`) | RealSense D435i `xyz="0.18 0.0 0.0525"` `rpy="0 0 0"`; colour optical frame offset `xyz="0.005 0.0175 0"` `rpy="-pi/2 0 -pi/2"`; Livox Mid360 at `xyz="0 0 0.08"` | Gazebo Classic `libgazebo_ros_camera.so`, RGB only (for FAST-LIVO colouring), `horizontal_fov 1.211` rad (= 69.4 deg; the inline comment says "87 deg", which would be 1.518 rad: comment and value disagree), 1280x720, 30 Hz | Chinese comment: "D435i mounted below the front of the LiDAR, its underside touching the robot top": an add-on mount, placed by reasoning, no measurement stated. Also still carries T1's `EXTERNAL_SENSORS` D435 block at `0.23 0 0.06` |
| T2' | oldgorden/lite3_gazebo_classic2 @ `e3f5e92` (no licence), **secondary-technical** | same files as T2 | same | identical numbers (`gazebo.xacro` differs from T2 only in the `$(find ...)` package name) | same | same |

Checked and negative: TopHillRobotics/quadruped-robot `mpc-wbc` @ `4b648d3`:
the README's `use_camera` launch argument only loads
`go1_description/xacro/depthCamera.xacro` (parent `trunk`); `lite3_description`
has no camera. armwaheed/mappo-arm-cloud-physical-ai @ `dc4c50c` (Apache-2.0):
no Lite3 URDF/xacro/SDF/MJCF/USD at all (its only model file is
`robot-stack/unitree/go2/d1_arm/urdf/d1_description.urdf`); the built-in camera
pose lives in `robot-stack/deep_robotics/lite3/visual_nav/lite3_front_camera_equidistant_20260901.json`
(`height_m 0.4`, `pitch_rad -0.2625` = -15.04 deg, nose-down positive) and the
runbook (`LIVE-RUN-RUNBOOK.md` line 201) notes that `height_m 0.40` contradicts
their measured 0.37 m standing / 0.115 m prone. Both JSON files and the
readiness note were saved in round 2b; not duplicated here.

Papers (secondary-prose): PUMA, arXiv 2601.15995 (fetched HTML), trains the
Lite3 in Isaac Gym with a Warp depth renderer and deploys with "the onboard
Intel RealSense D435i camera" at 10 Hz; no mount position, height, pitch, FOV
or simulator camera pose is stated. Three web searches ("Lite3" urdf
camera_link; "Jueying Lite3" camera extrinsic; DeepRoboticsLab Lite3
simulation camera) surfaced no Lite3 head-camera extrinsic in any paper or
forum.

### 2c.4 What this means for the project

1. There is no reusable model-file pose for the built-in wide-angle camera.
   Any simulator camera for it must be placed from our own measurement or
   from armwaheed's provisional JSON (0.40 m or 0.37 m height, -15 deg pitch;
   both secondary-technical, neither an official drawing).
2. The two third-party D435 placements (`0.23 0 0.06` and `0.18 0 0.0525` on
   `TORSO`) are for a RealSense on top of the torso; they say nothing about
   the built-in camera in the head's front face, but `x = 0.23` is a usable
   sanity bound for where the head front face is relative to `TORSO`.
3. The vendor MJCF `front_camera` must not be mistaken for a sensor.

### 2c.5 Network operations (24 tool calls, budget 30)

3 batched `gh search code` rounds (29 queries; 10 hit the 10/min code-search
limit and were re-run), 1 rate check, 6 `gh search repos`, 1 org listing,
19 `git/trees` listings, 1 `git clone --depth 1` (armwaheed, checked out at
`dc4c50c`), ~60 raw.githubusercontent.com file fetches (no API quota), 3
WebSearch, 2 WebFetch (arXiv abs + html), 7 licence lookups.

### 2c.6 Files added in 2c (SHA-256 appended to `SHA256SUMS.txt`)

```
e8c2b7c2f137110ca131fb6eb4e9568c214543c5cf5ddf15909248044494623a  github_legubiao_quadruped_ros2_control_5434c58_lite3_description_xacro_gazebo.xacro
3c489823517442cbbf93d442d7742b9b762b8eeea0c3ca429a6e6ae4c520d66f  github_legubiao_quadruped_ros2_control_5434c58_gz_quadruped_playground_models_D435_model.xacro
aa793e7438a3d91e265a6cb2664e86d44b2ea10826802b2a5aaa227b12666c9a  github_legubiao_quadruped_ros2_control_5434c58_go2_description_xacro_gazebo.xacro
44ef182d89f572e35be5326a16230c29a49ce12dec41c2c3163ef03a71d23b57  github_LaoGordon_lite3_gazebo_classic_f42239b_lite3_description_xacro_robot.xacro
b1bdffd98bce9d143d98d53e94e09404ddc7f5f23280a1e7af4cc8a9a20ff1ba  github_LaoGordon_lite3_gazebo_classic_f42239b_lite3_description_xacro_gazebo.xacro
bf49861eab88d015249b73f50527f8204f9008f057967966dc37a8190c4d5db3  github_LaoGordon_lite3_gazebo_classic_f42239b_lite3_description_xacro_sensors_load_sensors.xacro
4a206c34342b8c6d9682035589ce99f106b6d7383ce508bd2663ada576ace47c  github_LaoGordon_lite3_gazebo_classic_f42239b_lite3_description_xacro_sensors_d435i_sensor.xacro
512a93c353e111c4bf595eba429344599c4b0b617bb917c281d1e7cd648b2aed  github_DeepRoboticsLab_deep_robotics_model_549eb9a_Lite3_mjcf_Lite3.xml
3632cb09785ca796d28b2568ef22d5c451c14c06eb539aeed28b229b80ba1006  github_DeepRoboticsLab_sdk_deploy_2367375_Lite3_description_lite3_mjcf_mjcf_Lite3.xml
```

All nine are verbatim raw copies fetched by commit SHA (each byte-identical to
the branch-head copy fetched minutes earlier). Licences: legubiao Apache-2.0,
DeepRoboticsLab BSD-3-Clause, LaoGordon none (quotation for research use).

## 2d. Research that used the Lite3 built-in wide-angle camera (2026-09-10)

Question: has anyone used the Lite3 **built-in** head camera (not the add-on
D435i, not an external camera) as the perception input in a paper, thesis,
course project, or open-source project? Method: `WebSearch` (EN + ZH), arXiv
HTML via `WebFetch`, Semantic Scholar and arXiv APIs via `curl`, `gh search
code` / `gh search repos`, then shallow clones of every candidate repository
into the session scratchpad and local `grep` for `rtsp|8554|video0|
VideoCapture|realsense|d435|wide-angle|广角|摄像头`. Labels: `primary` = the
work's own code or text; `secondary` = someone else's description (search
snippet, WebFetch summary of a page I did not read verbatim). Known items from
the task brief (vendor `Lite3_Track` demo, `armwaheed` repo, PUMA) are listed
only for completeness and cross-referenced to §2b.

### 2d.1 Answer

**No paper or thesis was found that uses the built-in head camera as its
perception input.** Every consumer of the head camera found is a code project
(vendor demo, one commissioning/visual-navigation repo, three student or hobby
vision projects, two teleoperation UIs, one SDK wrapper). All of them read the
stream with OpenCV/FFmpeg or GStreamer from `rtsp://<motion host>:8554/test`;
none reads `/dev/video0` directly and none exposes a ROS topic for it. The
only calibration remains armwaheed's (§2b rows 8-13). No source reports an
end-to-end latency number. Papers that used a Lite3 either used the add-on
D435i (PUMA, PIE, arXiv 2512.01052) or no camera at all (arXiv 2512.21293).

### 2d.2 Works that consume the built-in head camera (all `primary` = their own code)

| # | Work (owner, date of HEAD, licence) | Type | Camera used for | Access path | Stated resolution / FOV / latency / calibration | How the D435i is distinguished | Evidence (path @ commit; local copy) |
|---|---|---|---|---|---|---|---|
| 1 | `DeepRoboticsLab/Lite3_Track` (vendor, `28db02f`, BSD-3) | official demo | person following on the Jetson | GStreamer `rtspsrc location=rtsp://192.168.1.120:8554/test ! rtph264depay ! h264parse ! nvv4l2decoder` | `videoscale` to 1280x720 / 640x360 (downstream resize); no FOV, latency, or intrinsics | RealSense not used by the tracker | §2b row 5; copies `github_DeepRoboticsLab_Lite3_Track_28db02f_*` |
| 2 | `armwaheed/mappo-arm-cloud-physical-ai` (`dc4c50c`, 2026-08/09) | commissioning + visual navigation ("chair-bin" object-goal task) on a Lite3 **Venture** | RGB input for `visual_nav/lite3_vision_shadow.py`, `test_camera.py`, a JPEG frame server, and the ArUco calibration | vendor RTSP consumed on the motion host itself: `rtsp://127.0.0.1:8554/test`; explicitly does **not** take over `/dev/video0` | measured 1280x720 BGR; fx 508.74 / fy 494.93 / cx 640.90 / cy 339.51, RMS 2.94 px (HFOV ≈ 103°, derived); mount 0.37 m, pitch -11° to -15°; latency not measured, only a decoder-queue warning | Venture variant has no D435i; readiness doc names the source `vendor UVC camera -> vendor local RTSP publisher` | §2b rows 7-13, 17-18; copies `github_armwaheed_*` |
| 3 | `IbrahimXXs/Jueying-Lite-3---Full-Python-Control` (`e5a6715`, 2025-10-01, **no licence file**) | hobby / course-style Python control suite | (a) person following: YOLOv8 `yolov8l.pt`, COCO class 0, constant vx 0.3 m/s, bang-bang yaw ±0.5 rad/s when the box centre leaves a ±50 px band, commands via UDP `0x0140/0x0141/0x0145` to `192.168.1.120:43893` (`Other/Kings_Follower.py`); (b) face tracking with a Haar cascade, yaw ≤ 0.7 rad/s (`Other/Face_Tracker.py`); (c) open-palm "Hello" gesture; (d) object classification; (e) frames sent to a local Mistral LLM every 5 s (`Other/Facial_Detection.py`); (f) live view during keyboard control | `cv2.VideoCapture("rtsp://192.168.1.120:8554/test")`; some scripts add `cv2.CAP_FFMPEG`, `CAP_PROP_BUFFERSIZE 1`, and request 640x480 @ 30 fps (a request; OpenCV cannot resize an RTSP source); `Scripts/wide_angle_camera.py` uses `gst-launch-1.0 rtspsrc ... latency=0 ! rtph264depay ! h264parse ! nvh264dec` | none stated; the code calls it the "wide-angle camera" in docstrings and the window title `Jueying Lite3 Wide-Angle Camera` | RealSense / D435 never mentioned (grep = 0) | `Other/Kings_Follower.py` L39-48, `Other/Face_Tracker.py` L10-11, `Scripts/wide_angle_camera.py` L8-24 @ `e5a67156941123eb83d5e52b572e92b9a8f994d4`; copies `github_IbrahimXXs_*` |
| 4 | `xnymerian/DeepRobotics-Lite3-Tracking-Segment-Algorithm-` (Mehmet Güven, `0b36e83`, 2025-12-18, Apache-2.0; no README) | real-time human detection + segmentation + tracking, **runs on the motion host's Rockchip NPU** (YOLO11n-seg 320x320 `.rknn`, `librknnrt.so`, `librga.so`) | person tracking and following; annotated frames re-encoded at 640x360 H.264 and sent by UDP/RTP to a PC (`PC_IP 192.168.1.50`, port 5000); commands received on port 5001 | `cv::VideoCapture("rtsp://127.0.0.1:8554/test")` on the motion host; motion commands to `127.0.0.1:43893` | `cap.set` 1280x720 with the comment `Set camera to full resolution (1280x720)`; writer 1280x720 @ 30; distance by a heuristic `DISTANCE_FACTOR 10000`, no intrinsics | RealSense / D435 never mentioned | `src/main.cpp` L17-18, L57-78, `src/config.h` @ `0b36e8388a8bc8efb50d09a2114b6f4b86576a17`; copies `github_xnymerian_*`. gh description: "A real-time human detection and tracking system designed for the LITE3 quadruped robot. The system uses YOLO11 segmentat[ion]..." |
| 5 | `liusiqi05/Lite3_dog` (`5001640`, 2026-06-16; `LICENSE` is MIT text with a copied "2018 WuJie" line) | student HRI project: InsightFace `buffalo_m` face ID + VGG19 (FER2013) emotion → action sequences; MediaPipe hand-gesture teleoperation | RGB for face/emotion/gesture recognition | `CAMERA_SOURCE = "rtsp://192.168.1.120:8554/test"  # 机器狗摄像头 RTSP 地址`; `cv2.VideoCapture`, `CAP_PROP_BUFFERSIZE 3` (comment: buffer 1 caused corrupted frames, 花屏), requested 640x480 @ 30, a dedicated grab thread keeps only the newest frame `消除 RTSP 缓冲延迟`, 5 warm-up frames, `FRAME_SKIP 3`; `gesture_control.py` tries `rtsp://192.168.2.1:8554/test`, `.../live`, `:554/live`, then `192.168.1.120:8554/test` | none stated beyond the OpenCV requests; the STABLE_THRESHOLD comment assumes ≈15 fps effective | **explicitly separated**: depth comes from a `depth_guard_client.py` that polls an HTTP server (`http://192.168.2.1:8000`, or `127.0.0.1:8000` through an SSH tunnel) on the perception host (`Jetson Nano/Orin/NX`) for front distance; the RGB path never touches the depth camera | `main_controller1.py` L36-41, L303-340; `depth_guard_client.py` L1-20; `README.md` L39-43, L54 @ `5001640243ba9ccf3615ded0d274a1cdba0667f3`; copies `github_liusiqi05_*` |
| 6 | `NestorKrdona/lite3-local-web-control` (`a1a9709`, 2025-10-23, no licence) | Flask web teleoperation UI | live FPV view in the browser (RTSP → MJPEG) | `RTSP_URL = f"rtsp://{ROBOT_IP}:8554/test"`; `cv2.VideoCapture`, `CAP_PROP_BUFFERSIZE 1`, open/read timeout 5 s, 30 fps target, JPEG q80; README: `Camera RTSP URL: rtsp://192.168.1.120:8554/test` | logs the frame size at runtime but does not record it; no FOV/latency | RealSense never mentioned | `app.py` L35-38, `utils/video_streamer.py` L60-80, `README.md` L44-48 @ `a1a97095b7bb27d29105fd061f023b9bc362414f`; copy `github_NestorKrdona_*_video_streamer.py` |
| 7 | `laojiahuo2003/lite3_sdk` (`cea5a55`, 2026-07-11; README badge says MIT, **no LICENSE file**) | Python UDP SDK with a `CameraClient` | generic frame access (blocking read, latest-frame, callback) | default `rtsp://192.168.2.1:8554/test`; forces `OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp`, `CAP_PROP_BUFFERSIZE 1`, prints the decoded resolution on connect | none recorded | RealSense never mentioned. **Caution**: README note 6 claims `摄像头 IP 通常与运动主机 IP 不同（默认 192.168.2.1）`; per the vendor document (§2b row 4) both `192.168.1.120` and `192.168.2.1` are motion-host addresses (wired vs Wi-Fi), so this is a misreading, not a separate camera host | `lite3_sdk/camera_client.py` L13-31, `README.md` L180, L277 @ `cea5a5593cceea21501222644551d7b8ffadb93f`; copy `github_laojiahuo2003_*_camera_client.py` |
| 8 | `jhzv/jueying-teleop-project` (`0238381`, 2025-09-21) and `jhzv/jueying_system_complete` (`de394d9`, 2025-11-11), "Sistema de teleoperación remota ROS-Internet para robot Jueying Lite3 - Skaler S.A", no licence | industrial Internet teleoperation (rosbridge + Node multiplexor + browser) | operator FPV | backup `start_video_proxy.sh`: `ffmpeg -rtsp_transport tcp -i rtsp://192.168.1.120:8554/test -f mjpeg -q:v 5 -r 15 -listen 1 http://127.0.0.1:8081/stream`; the frontend has two buttons `📷 Wide Angle` / `🔍 Depth` that publish `{camera: 'wide'|'depth', enabled}` on ROS topic `/camera_control` (handler node not in the repo) | 15 fps MJPEG proxy; no native spec | the "Depth" button is the only D435i reference. Note: the later `restart-camera.sh.txt` runs MediaMTX on the Jetson (`192.168.1.103`) from `/dev/video2`, i.e. the final system may relay an unspecified perception-host camera instead of the head stream | `jueying-teleop/frontend/backup/start_video_proxy.sh` L14-19, L57-64 @ `de394d9cd89c2eab9c6ddc6f70ef5940727d0774`; `frontend/jueying_enhanced.html` L456-465, L667-680 @ `023838141ee7f4696e1008d982bd034644231282`; copies `github_jhzv_*` |
| 9 | `Mplus0/Dog-Machine-2026` (`6581380`) | course project network doc | not inspected beyond the port table | `8554/tcp | 运动主机 RTSP 广角相机流` | — | — | §2b row 22 (no new fetch) |

Cross-cutting facts from rows 1-8 (all `secondary-technical`, none promoted):
the access pattern is uniform (`rtsp://<motion host>:8554/test`, H.264, via
OpenCV-FFmpeg or GStreamer); the two projects that run on the motion host
(rows 2 and 4) use `127.0.0.1` and treat 1280x720 as the native size; the
others request 640x480 through OpenCV, which does not resize an RTSP source.
Latency mitigation is always client-side (buffer size 1 or 3, a latest-frame
thread, `latency=0` on `rtspsrc`); nobody measured it. Depth, where used, comes
from the perception host over a separate channel (row 5 HTTP, row 8 ROS),
never from the RTSP stream.

### 2d.3 Papers that used a Lite3 (none with the head camera)

| Paper | Platform / camera | Label for this question | Evidence |
|---|---|---|---|
| PUMA, arXiv 2601.15995 | Lite3 + Intel RealSense D435i depth at 10 Hz | **not head camera** | task brief; WebSearch snippet (secondary) |
| PIE: Parkour with Implicit-Explicit Learning Framework, arXiv 2408.13740 (v3 2024-08-25) | abstract: "a low-cost quadruped robot equipped with an unreliable egocentric depth camera"; search snippet: "PIE was deployed on a DEEP Robotics Lite3" | **not head camera** (depth); camera model not named in the abstract | `2d_arxiv_api_idlist.xml` (primary abstract); WebSearch snippet (secondary) |
| Autonomous Grasping on Quadruped Robot with Task Level Interaction, arXiv 2512.01052 (Muhtadin, Rusydiansyah, Purnomo, Purnama, Fatichah; ITS Surabaya; 2025-11-30) | Lite3 + arm; perception input is an Intel RealSense D435i on the arm end-effector (USB to the perception host); the platform paragraph lists "a wide-angle camera for environmental exploration", a body D435i, ultrasonic radar (UART) and LiDAR (Ethernet), but no pipeline consumes the wide-angle stream | **not head camera** (mentioned only in the hardware description) | WebFetch summary of `https://arxiv.org/html/2512.01052` (primary source, summarised, not read verbatim) |
| Quadruped-Legged Robot Movement Plan Generation using Large Language Model, arXiv 2512.21293 (Muhtadin, Gusti, Zaini, Purnomo, Purnama, Fatichah; ITS; 2025-12-24; S2 venue "CENiM") | Lite3; inputs LiDAR (HDL-Localization), IMU, odometry; no camera of any kind | **no camera** | WebFetch summary of `https://arxiv.org/html/2512.21293` |
| RGB-Based Staircase Detection for Quadrupedal Robots, Sensors 25(23):7247, 2025 (Wozniak, Penar, Bielecki; Rzeszow UT; DOI 10.3390/s25237247) | **Unitree Go1**, its two built-in head fisheye cameras (1856x800, 180° FOV, processed to 120° / 608x608) | not Lite3 — the only paper found that builds a perception model on a quadruped's *built-in* wide-angle head camera; methodological analogue only | WebFetch of `https://pmc.ncbi.nlm.nih.gov/articles/PMC12693958/` (summarised) |
| M-SEVIQ dataset, arXiv 2601.02777 | Unitree Go2 with a custom stereo-event rig | not Lite3 | `2d_arxiv_api_idlist.xml` |

Leads surfaced but **not resolved** within budget (platform or sensor not
confirmed): SF-TIM arXiv 2408.00486 (jumping; abstract names no platform);
CK-SLAM, *Agronomy* 2025 (Lite3 in the abstract; sensors unknown, likely LiDAR
+ kinematics); "Quadrupedal Locomotion Control in Complex Terrains Based on
Deep Reinforcement Learning", RCAE 2025 (Lite3 in the abstract; locomotion);
"Monocular Person Localization under Camera Ego-motion", arXiv 2503.02916
(robot not named in the abstract); FSUNav, arXiv 2604.03139 (robot not named);
"Path Planning and Motion Control of Robot Dog Through Rough Terrain Based on
Vision Navigation", PMC11598469 (robot not named in the snippet); "A
Whole-Body Hybrid Control for Quadruped Robots in Deep-Space Exploration",
ScienceDirect (robot not named). None of the snippets mentions a wide-angle
or RTSP camera.

### 2d.4 Searches that returned nothing

- `gh search code`: `"8554/test"`, `"192.168.1.120:8554"`, `"192.168.2.1:8554"`,
  `lite3 VideoCapture`, `8554 lite3`, `rtsp jueying`, `lite3 cv2 camera`,
  `"deeprobotics" rtsp`, `lite3 "video0"` → 0 hits each; only `lite3 rtsp` →
  6 armwaheed files. The legacy code-search index drops punctuation-heavy
  tokens and only covers recently active repositories, so rows 3-8 were found
  through `gh search repos` (`jueying`, `lite3 quadruped`) instead;
  `gh search repos "lite3 camera"` → 0. Log: `2d_gh_code_search_log.txt`,
  `2d_gh_repo_search_log.txt`.
- Semantic Scholar `Jueying Lite3` → 30 results, mostly false positives
  (LiTe3 chemistry, author surname Jueying); Lite3-relevant only CK-SLAM,
  arXiv 2512.21293 and the RCAE 2025 paper. `DeepRobotics Lite3 quadruped
  camera` → 0. Log: `2d_semantic_scholar_search_log.txt`.
- arXiv API `all:"Lite3" OR all:"Jueying"` returned an empty body (http →
  https redirect not followed); the `id_list` call succeeded.
- WebSearch ZH `"绝影Lite3" 学位论文/硕士 视觉 相机` → press releases and the
  Scribd perception-manual upload only; no CNKI thesis surfaced (CNKI is not
  searchable from this environment). WebSearch ZH `Lite3 机器狗 rtsp 8554 广角相机
  拉流 opencv 项目` → generic RTSP/OpenCV tutorials. WebSearch EN
  `"Lite3" ("head camera" OR "front camera" OR "wide-angle camera" OR
  "fisheye") paper OR thesis` → distributor pages plus the Go1/Go2 papers
  above.

### 2d.5 What this means for the project

1. There is no prior paper to cite for "VLA/VLN on the Lite3 head camera";
   the closest published analogue is the Go1 staircase paper (built-in
   fisheye head cameras) and, for Lite3 specifically, only code projects.
2. Every working consumer uses the vendor RTSP publisher; a project camera
   node should do the same (`rtsp://127.0.0.1:8554/test` on the motion host,
   or `192.168.1.120` / `192.168.2.1` off-board) and must not claim
   `/dev/video0`.
3. Expect 1280x720 H.264; treat OpenCV `CAP_PROP_FRAME_WIDTH/HEIGHT` requests
   in rows 3, 5, 6 as no-ops. Frame-age must be measured by us; no source has
   done it.
4. The only intrinsics remain armwaheed's single Venture calibration (§2b);
   the two on-host projects (rows 2, 4) show that consuming and even running
   an NPU detector on the RK3588 motion host is feasible.

### 2d.6 Network operations (31 tool-level; budget 30 overrun by one redirect follow)

1-3 WebSearch (EN arXiv, EN wide-angle/RTSP, ZH 广角相机); 4-8 `gh search
code` x5; 9-10 WebFetch arXiv HTML 2512.21293, 2512.01052; 11-13 Semantic
Scholar API x3 (parser bug, results discarded); 14-18 `gh search code` x5;
19-21 `gh search repos` x3; 22-23 Semantic Scholar API x2 (re-run); 24 arXiv
API keyword query (empty body); 25 one batch of 11 shallow `git clone`s into
the scratchpad (xnymerian, jhzv x2, QuangTrungK22, IbrahimXXs, syswonder,
xuetong530, NestorKrdona, liusiqi05, laojiahuo2003, mobilio7); 26-28 WebSearch
(EN head/front/fisheye, ZH 学位论文, ZH rtsp 8554); 29 arXiv API `id_list` of 5
ids; 30 WebFetch ncbi.nlm.nih.gov PMC12693958 (301 only); 31 WebFetch
pmc.ncbi.nlm.nih.gov PMC12693958. Clones with no camera use: QuangTrungK22
(vendor SDK copy), syswonder (Lite3_ROS copy), xuetong530 (empty), mobilio7
(Gazebo sim with an optional RealSense model only). Summary:
`2d_clone_grep_summary.txt`.

### 2d.7 Files added in 2d (SHA-256 appended to `SHA256SUMS.txt`)

```
4e33c7c144940abfe0ec02e3e10f873f46bae555d21940879c85be580255b5f0  github_xnymerian_DeepRobotics-Lite3-Tracking-Segment-Algorithm_0b36e83_src_main.cpp
741813af575127eb2bdd4e97640e00e2cd5ea6347fe91d5be43b4ec80d1a65e3  github_xnymerian_DeepRobotics-Lite3-Tracking-Segment-Algorithm_0b36e83_src_config.h
e4776071f6f65d56e08166da723424eea5553338656dc0df2bad327222da40a8  github_IbrahimXXs_Jueying-Lite-3---Full-Python-Control_e5a6715_Other_Kings_Follower.py
d5f09ea49c9d5f595855de704b49d7b369fb86608edc22090a2f35cb6d30bc2a  github_IbrahimXXs_Jueying-Lite-3---Full-Python-Control_e5a6715_Other_Face_Tracker.py
1302df08665279ed4c62da4680c902fc80eda8965466c42694e1e1cd2ef8eca4  github_IbrahimXXs_Jueying-Lite-3---Full-Python-Control_e5a6715_Scripts_wide_angle_camera.py
7c943499fb0a4a42aa164c1f7bd03c9949f134bf6bc0d85d23b57d1ee31ea6a5  github_liusiqi05_Lite3_dog_5001640_main_controller1.py
dff41ea4552d727dd240343063ca35a30fbf6dbd5cebd7cc3cfcffce147f4fb6  github_liusiqi05_Lite3_dog_5001640_depth_guard_client.py
c56a2791168d4b687a47ea1a07997850ae1b9cd5cfe5286a57c1143b7fb74f27  github_liusiqi05_Lite3_dog_5001640_README.md
ba77df15b382cd536a1f4a1c02821cb8b084aa2abd29d8f8567f8ffa1ed1bea1  github_jhzv_jueying_system_complete_de394d9_jueying-teleop_frontend_backup_start_video_proxy.sh
61c0cf153fafc4e5bcfb0e345ee12997bd16909ec1a39940b5dfdfb804723644  github_jhzv_jueying-teleop-project_0238381_frontend_jueying_enhanced.html
2ce8386acbf7b7e6a01061902af467f2e4272c5b8d1627f7f3d61cc127d7dd8c  github_laojiahuo2003_lite3_sdk_cea5a55_lite3_sdk_camera_client.py
6c12509821bb5024f4ed7757d6d66a4558ca2d7cb5eeb8adb7257a73e604c3a0  github_NestorKrdona_lite3-local-web-control_a1a9709_utils_video_streamer.py
58b6896646a5279193bbc15c5a942e54c20aba68913f095318e5abdd8576cf88  2d_gh_code_search_log.txt
2e6f83762e44b443f917b7d448165b674d9776023a8947c64bc5c892a35c957e  2d_gh_repo_search_log.txt
5fc3000dd760e20f347cd6775ef639cbe5f4718c118c5a818937a87debe662ad  2d_semantic_scholar_search_log.txt
29b21c9f85898b1940a86c091763fb2053f15d4353ff580ac5fa4e7cd49bf241  2d_arxiv_api_idlist.xml
23960eb8b224945e2738b80565eff3624039290f68650488b66bc9b2af550ee9  2d_clone_grep_summary.txt
```

The twelve `github_*` files are verbatim copies from shallow clones at the
commits named in their filenames. Licences: xnymerian Apache-2.0; liusiqi05
MIT (copied header); IbrahimXXs, jhzv, NestorKrdona, laojiahuo2003 none
(quotation for research use only, do not redistribute).
