"""Closed-run artifact retention. Never alter simulation or frozen source bytes."""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time
import zipfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
AUDIT = BASE / "audits/2026-10-01_artifact_storage"


def signature(path):
    s = path.lstat()
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def digest(path):
    before = signature(path)
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    if signature(path) != before:
        raise RuntimeError(f"Changed while hashing: {path}")
    return h.hexdigest()


def atomic_json(path, data):
    temporary = path.with_name(path.name + ".pending")
    with temporary.open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def record(data):
    AUDIT.mkdir(parents=True, exist_ok=True)
    with (AUDIT / "operations.jsonl").open("a") as f:
        f.write(json.dumps({"wall_time": time.time(), **data}) + "\n")
        f.flush()
        os.fsync(f.fileno())


def regular(path):
    if path.resolve() != path.absolute() or not path.is_file() or path.is_symlink():
        raise ValueError(f"Not a regular non-symlink path: {path}")


def metadata(path):
    # macOS Python builds need not expose os.listxattr. The native CLI hides
    # filesystem-internal compression attributes, retaining application xattrs.
    attributes=subprocess.check_output(["/usr/bin/xattr","-lx",str(path)])
    acl=subprocess.check_output(["/bin/ls","-le",str(path)]).splitlines()[1:]
    return attributes,acl


def closed_run(run):
    regular(run / "result.json")
    if run.parent != (BASE / "runs").resolve() or run.resolve() != run:
        raise ValueError("Only direct experiment run directories are allowed")
    if (run / ".artifact-active").exists() or (AUDIT / "active" / run.name).exists():
        raise RuntimeError("Run is active")
    # Supplement the completion marker with an open-writer check. Unsupported
    # lsof/proc visibility must fail closed, never count as no writer.
    names = [p for p in run.iterdir() if p.is_file() and p.suffix in (".jsonl", ".log")]
    if names:
        command = [shutil.which("lsof") or "/usr/sbin/lsof", "-nP", "-F", "fan", "--", *map(str, names)]
        checked = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if checked.returncode not in (0, 1) or checked.stderr.strip():
            raise RuntimeError("Cannot verify closed files: " + checked.stderr)
        access = None
        for line in checked.stdout.splitlines():
            if line.startswith("f"): access = None
            if line.startswith("a"): access = line[1:]
            if line.startswith("n") and access in ("w", "u"):
                raise RuntimeError("Open output writer: " + line[1:])


def archive_members(run):
    """Read and verify every archived member against its original byte hash."""
    path=run/'raw_capture.zip'
    receipt=json.loads((run/'raw_capture_manifest.json').read_text())
    if digest(path)!=receipt['archive_sha256']:raise ValueError('Archive identity mismatch')
    with zipfile.ZipFile(path) as archive:
        if set(archive.namelist())!=set(receipt['members']):raise ValueError('Archive membership mismatch')
        for name,row in receipt['members'].items():
            p=run/name
            if p.resolve()!=p.absolute() or not p.is_relative_to(run) or '..' in Path(name).parts or Path(name).is_absolute():
                raise ValueError('Unsafe archive member')
            with archive.open(name) as f:
                h=hashlib.sha256();size=0
                for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block);size+=len(block)
            if h.hexdigest()!=row['sha256'] or size!=row['bytes']:raise ValueError('Archive member mismatch')
    return receipt


def pack_raw(run):
    closed_run(run)
    archive_path=run/'raw_capture.zip';receipt_path=run/'raw_capture_manifest.json'
    if archive_path.exists() or receipt_path.exists():raise FileExistsError('Existing archive; verify or restore it explicitly')
    protected=set()
    for manifest in (BASE/'versions').glob('v*/manifest.json'):
        protected.update(json.loads(manifest.read_text()).get('source_files',{}))
    root=BASE.parents[2]
    paths=[p for p in sorted(run.rglob('*')) if p.is_file() and
           (p.suffix=='.npz' or p.suffix in ('.jsonl','.log') and p.stat().st_size>=4*1024*1024)]
    if not paths:raise ValueError('No raw payloads to archive')
    rows={};identities={};allocated=0
    for p in paths:
        regular(p)
        if str(p.relative_to(root)) in protected:raise ValueError('Frozen source fixture cannot be archived')
        s=p.stat();rows[str(p.relative_to(run))]=dict(bytes=s.st_size,sha256=digest(p),mtime_ns=s.st_mtime_ns,mode=stat.S_IMODE(s.st_mode))
        identities[p]=signature(p);allocated+=s.st_blocks*512
    # NPZ is already deflated. Reserve its entire size plus a conservative log
    # allowance; one closed run at a time, never build an uncompressed TAR.
    reserve=sum(p.stat().st_size for p in paths if p.suffix=='.npz')+256*1024*1024
    if shutil.disk_usage(run).free<reserve:raise RuntimeError('Insufficient archive reserve')
    temporary=run/'raw_capture.pending.zip'
    with zipfile.ZipFile(temporary,'x',allowZip64=True) as archive:
        for p in paths:
            archive.write(p,str(p.relative_to(run)),compress_type=zipfile.ZIP_STORED if p.suffix=='.npz' else zipfile.ZIP_LZMA)
    with temporary.open('rb') as f:os.fsync(f.fileno())
    temporary.replace(archive_path)
    receipt=dict(schema_version=1,status='packed_not_pruned',members=rows,archive_sha256=digest(archive_path),
        original_allocated_bytes=allocated,archive_bytes=archive_path.stat().st_size,
        restore='python versions/v51/artifacts.py restore --run '+run.name,
        claim='Lossless original bytes; NPZ stored without recompression; large text uses ZIP LZMA. Restore before legacy readers requiring expanded paths.')
    atomic_json(receipt_path,receipt)
    archive_members(run)
    closed_run(run)
    if any(signature(p)!=identities[p] for p in paths):raise RuntimeError('Source changed; archive kept and originals retained')
    record(dict(kind='pack_raw',run=run.name,status='verified_before_prune',members=len(rows),archive_sha256=receipt['archive_sha256']))
    for p in paths:
        if signature(p)!=identities[p]:raise RuntimeError('Source changed during archive pruning')
        p.unlink()
    receipt['status']='completed';atomic_json(receipt_path,receipt)
    record(dict(kind='pack_raw',run=run.name,status='completed',members=len(rows),allocated_before=allocated,allocated_after=archive_path.stat().st_blocks*512))
    return receipt


def restore_raw(run):
    closed_run(run);receipt=archive_members(run)
    missing={n:r for n,r in receipt['members'].items() if not (run/n).exists()}
    if shutil.disk_usage(run).free<sum(r['bytes'] for r in missing.values())+256*1024*1024:
        raise RuntimeError('Insufficient restore reserve')
    with zipfile.ZipFile(run/'raw_capture.zip') as archive:
        for name,row in receipt['members'].items():
            path=run/name
            if path.exists():
                regular(path)
                if digest(path)!=row['sha256']:raise ValueError('Refusing to overwrite changed restored file')
                continue
            path.parent.mkdir(parents=True,exist_ok=True)
            temporary=path.with_name(path.name+'.restore-pending')
            with archive.open(name) as source,temporary.open('xb') as target:shutil.copyfileobj(source,target,4*1024*1024)
            if digest(temporary)!=row['sha256']:raise ValueError('Restored content mismatch')
            os.chmod(temporary,row['mode']);os.utime(temporary,ns=(row['mtime_ns'],row['mtime_ns']))
            temporary.replace(path)
    return dict(status='restored',members=len(receipt['members']),archive_retained=True)


def open_text(run,name):
    """Read either an expanded original or its lossless archived member."""
    path=run/name
    if path.exists():return path.open()
    archive=zipfile.ZipFile(run/'raw_capture.zip')
    raw=archive.open(name)
    # Keep archive ownership attached until the text stream closes.
    class ArchivedText(io.TextIOWrapper):
        def close(self):
            try:super().close()
            finally:archive.close()
    return ArchivedText(raw,encoding='utf-8')


def artifact_exists(run,name):
    if (run/name).is_file():return True
    if not (run/'raw_capture.zip').is_file():return False
    with zipfile.ZipFile(run/'raw_capture.zip') as archive:return name in archive.namelist()


def video_check(video, count, fps=None):
    regular(video)
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("FFmpeg and FFprobe are required")
    info = json.loads(subprocess.check_output([ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=nb_read_frames,width,height,avg_frame_rate,duration", "-of", "json", str(video)], timeout=300))
    stream = info["streams"][0]
    if int(stream["nb_read_frames"]) != count:
        raise ValueError("Video frame count mismatch")
    n, d = map(float, stream["avg_frame_rate"].split("/"))
    if fps is not None and abs(n/d - fps) > 1e-5:
        raise ValueError("Video frame rate mismatch")
    decoded = subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-xerror", "-i", str(video),
        "-map", "0:v:0", "-f", "null", "-"], capture_output=True, timeout=300)
    if decoded.returncode or decoded.stderr:
        raise RuntimeError("Video decode failed: " + decoded.stderr.decode(errors="replace"))
    return stream


def prune_frames(run, apply=False):
    closed_run(run)
    result = json.loads((run / "result.json").read_text())
    manifest_path = run / "frames.json"
    rows = json.loads(manifest_path.read_text())
    if not rows or len(rows) != result["frames"]:
        raise ValueError("Frame manifest/result mismatch")
    video = run / Path(result["video"]).name
    video_hash = digest(video)
    if video_hash != result["video_sha256"]:
        raise ValueError("MP4 identity mismatch")
    source = BASE / "runs" / result["source_run"] / "video_states.json"
    regular(source)
    if digest(source) != result["source_states_sha256"]:
        raise ValueError("Original recorded states changed")
    paths = [run / row["file"] for row in rows]
    if any(p.parent != run / "frames" or p.suffix != ".png" for p in paths) or len(set(paths)) != len(paths):
        raise ValueError("Unexpected frame path or duplicate")
    if set(paths) != set((run / "frames").iterdir()):
        raise ValueError("Incomplete/unexpected frame directory")
    identities = {}
    allocated = logical = 0
    for p, row in zip(paths, rows):
        regular(p)
        if digest(p) != row["sha256"]:
            raise ValueError("PNG hash mismatch: " + str(p))
        identities[p] = signature(p)
        logical += p.stat().st_size
        allocated += p.stat().st_blocks * 512
    stream = video_check(video, len(rows), result["fps"])
    proof = dict(kind="prune_frames", run=run.name, frame_count=len(rows),
        logical_bytes=logical, allocated_bytes=allocated, video_sha256=video_hash,
        original_frames_manifest_sha256=digest(manifest_path), source_states_sha256=digest(source),
        decoded_video=stream, retained_sample_indices=sorted({0, len(rows)//2, len(rows)-1}),
        claim="Remove verified derived PNGs; original per-frame hashes, video and recorded states remain. MP4 is lossy, not an exact PNG archive.")
    if not apply:
        return {**proof, "status":"verified_dry_run"}
    receipt = run / "frame_retention.json"
    if receipt.exists():
        raise FileExistsError(receipt)
    closed_run(run)
    if any(signature(p) != identities[p] for p in paths) or digest(video) != video_hash:
        raise RuntimeError("Artifact changed before prune")
    samples = run / "frame_samples"
    samples.mkdir(exist_ok=True)
    for i in proof["retained_sample_indices"]:
        shutil.copy2(paths[i], samples / paths[i].name)
        if digest(samples / paths[i].name) != rows[i]["sha256"]:
            raise RuntimeError("Preview copy mismatch")
    atomic_json(receipt, {**proof, "status":"verified_before_prune"})
    record({**proof, "status":"prepared"})
    for p in paths:
        if signature(p) != identities[p]:
            raise RuntimeError("Frame changed during pruning; receipt preserves progress")
        p.unlink()
    (run / "frames").rmdir()
    proof.update(status="completed", retained_sample_bytes=sum(p.stat().st_blocks*512 for p in samples.iterdir()))
    atomic_json(receipt, proof)
    record(proof)
    return proof


def compress_log(path):
    """macOS transparent compression preserves paths, bytes, mtimes and readers."""
    regular(path)
    before = path.stat()
    if before.st_flags or before.st_nlink != 1:
        return {"path":str(path), "status":"skipped_existing_flags_or_links"}
    if before.st_size < 4*1024*1024:
        return {"path":str(path), "status":"skipped_small"}
    if shutil.disk_usage(path.parent).free < before.st_size + 256*1024*1024:
        raise RuntimeError("Insufficient temporary-space reserve")
    identity, expected = signature(path), digest(path)
    old_metadata = metadata(path)
    directory = Path(tempfile.mkdtemp(prefix=".log-compaction-", dir=path.parent))
    backup = directory / "rollback.original"
    try:
        with tempfile.TemporaryFile() as errors:
            producer = subprocess.Popen(["/usr/bin/bsdtar", "--mac-metadata", "-cf", "-", "-C", str(path.parent), path.name], stdout=subprocess.PIPE, stderr=errors)
            extracted = subprocess.run(["/usr/bin/bsdtar", "--mac-metadata", "--hfsCompression", "-xpf", "-", "-C", str(directory)], stdin=producer.stdout, capture_output=True, timeout=300)
            producer.stdout.close()
            code = producer.wait(timeout=300)
            errors.seek(0)
            if code or extracted.returncode or errors.read() or extracted.stderr:
                raise RuntimeError("Transparent compression failed")
        candidate = directory / path.name
        after = candidate.stat()
        if digest(candidate) != expected or (after.st_size,after.st_mode,after.st_uid,after.st_gid,after.st_mtime_ns) != (before.st_size,before.st_mode,before.st_uid,before.st_gid,before.st_mtime_ns) or metadata(candidate) != old_metadata:
            raise RuntimeError("Compression content or metadata mismatch")
        if not after.st_flags & stat.UF_COMPRESSED or after.st_blocks >= before.st_blocks:
            return {"path":str(path), "status":"skipped_no_saving"}
        if signature(path) != identity:
            raise RuntimeError("Log changed during compression")
        row = dict(kind="compress_log", path=str(path.relative_to(BASE)), sha256=expected, logical_bytes=before.st_size,
            allocated_before=before.st_blocks*512, allocated_after=after.st_blocks*512,
            mtime_ns=before.st_mtime_ns, status="prepared")
        os.link(path,backup)
        record(row)
        os.replace(candidate,path)
        if digest(path) != expected:
            os.replace(backup,path)
            raise RuntimeError("Post-replacement mismatch; original restored")
        backup.unlink()
        row["status"]="completed"
        record(row)
        return row
    finally:
        # An unexpected error after replacement retains the original rollback.
        if not backup.exists():shutil.rmtree(directory)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=["prune-frames","compress-logs","pack-raw","verify-archive","restore"])
    parser.add_argument("--run",required=True)
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    run=(BASE/"runs"/args.run).absolute()
    AUDIT.mkdir(parents=True,exist_ok=True)
    with (AUDIT/"maintenance.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        closed_run(run)
        if args.mode in ('pack-raw','restore','verify-archive'):
            if args.mode!='verify-archive' and not args.apply:raise ValueError('Use --apply for archive or restore')
            answer={'pack-raw':pack_raw,'restore':restore_raw,'verify-archive':archive_members}[args.mode](run)
            print(json.dumps({k:v for k,v in answer.items() if k!='members'}),flush=True)
        elif args.mode=="prune-frames":
            print(json.dumps(prune_frames(run,args.apply)),flush=True)
        else:
            for p in sorted(run.rglob("*")):
                if p.suffix not in (".jsonl",".log") or p.stat().st_size<4*1024*1024:continue
                row=compress_log(p) if args.apply else {"path":str(p),"bytes":p.stat().st_size,"status":"candidate"}
                print(json.dumps(row),flush=True)


if __name__=="__main__":main()
