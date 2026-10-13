# v56 pre-physics qualification-schema failure

Trial01 supervisor exits after0.6s before physics. run_local_episode.py expects legacy qualification keys; component_qualification.json lacks cache_geometry_and_contract_passed and related aliases. Native build and declared safety/corner gates passed, but runtime startup is rejected. Frozen source/manifest remain unchanged. v57 adds metadata compatibility and keeps exact same native source/install. No physics acceptance from this attempt.
