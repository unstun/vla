# Approved precommit compiler-metadata retention

83 redundant generated files (3,126,128 bytes) were removed from the local
v225-v228 delivery after SHA-256 verification of their original gpu5070ti
execution paths. These are 43 compiler configuration logs under CMakeFiles and
40 generated rosidl argument JSON files. Main build/test logs, XML results,
failed attempts, source/configuration, summaries and every frozen manifest are
unchanged. This does not change a planner version or any validation result.

The original frozen manifests/receipts still name the historical relative paths.
retention.json maps each missing path to its original SHA-256, size and durable
remote path; remote_verification.json records live verification. A legacy full
expanded-file validator requires restoration; a locator alone is not a pass.

Verify all remaining bytes and the omitted remote bytes:
`python3 verify.py`

Restore exactly the omitted files (83-file allowlist, no build-tree download):
`python3 verify.py --restore`

Restored metadata remains excluded by version-specific .gitignore entries.
Regeneration uses each original build.sh with a NEW attempt ID; regenerated
metadata need not be byte-identical to the historical compiler logs.
