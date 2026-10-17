"""Preserve each attempt's XML and test stdout before another build overwrites it."""
from pathlib import Path
import shutil,sys
work=Path(sys.argv[1]);attempt=work/'evidence'/sys.argv[2]
assert attempt.is_dir()
for package in (work/'build').iterdir():
    if not package.is_dir():continue
    for folder,suffix in [('test_results','.xml'),('ament_cmake_gtest','.txt')]:
        for path in (package/folder).rglob('*'):
            if path.is_file() and path.suffix==suffix:
                target=attempt/folder/package.name/path.relative_to(package/folder)
                target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists():assert target.read_bytes()==path.read_bytes(),target
                else:shutil.copyfile(path,target)
