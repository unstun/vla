"""Acquire and verify the selected official checkpoint without loading it."""
import hashlib
import json
import subprocess
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
def main():
    manifest = json.loads((EXP/'setup/selected_model.json').read_text())
    destination = EXP/'models'/manifest['file']
    destination.parent.mkdir(exist_ok=True)
    partial = destination.with_suffix(destination.suffix+'.part')
    if not destination.exists():
        subprocess.run(['curl','--fail','--location','--retry','3','--continue-at','-',
            '--max-time','600','--silent','--show-error',
            f"https://huggingface.co/{manifest['id']}/resolve/{manifest['revision']}/{manifest['file']}",
            '--output',str(partial)],check=True)
        source = partial
    else:
        source = destination
    digest = hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
    if digest != manifest['sha256'] or source.stat().st_size != manifest['bytes']:
        raise RuntimeError('Official checkpoint size/SHA-256 mismatch')
    if source == partial:
        partial.rename(destination)
    print(json.dumps({'file':str(destination),'sha256':digest,'bytes':destination.stat().st_size}))

if __name__ == '__main__':main()
