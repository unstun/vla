"""Build only the pinned SDK's unchanged scalar spline, without robot I/O."""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE.parents[2] / "references/upstream/2026-09-27_lite3_pd_startup"
OUTPUT = BASE / "runtime/lite3_sdk_spline"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    identity = json.loads((SOURCE / "source_identity.json").read_text())
    for item in identity["files"]:
        if digest(SOURCE / item["path"]) != item["sha256"]:
            raise ValueError("Pinned SDK source mismatch: " + item["path"])
    source = (SOURCE / "src/motionexample.cpp").read_text()
    start = source.index("void MotionExample::CubicSpline(")
    # This is the final method in the pinned source. Keep its bytes unchanged.
    method = source[start:]
    declaration = method[:method.index("{")].replace("MotionExample::", "").strip() + ";"
    wrapper = '''
extern "C" void lite3_spline(double initial, double goal, double elapsed,
                              double dt, double duration, double *out) {
  MotionExample example;
  example.CubicSpline(initial, 0., goal, 0., elapsed, dt, duration,
                      out[0], out[1], out[2]);
}
'''
    OUTPUT.mkdir(parents=True, exist_ok=True)
    generated = OUTPUT / "sdk_spline.cpp"
    generated.write_text('#include <cmath>\nusing std::pow;\nclass MotionExample { public:\n'
                         + declaration + '\n};\n' + method + wrapper)
    library = OUTPUT / "liblite3_spline.dylib"
    command = ["/usr/bin/clang++", "-std=c++11", "-O2", "-dynamiclib",
               str(generated), "-o", str(library)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (OUTPUT / "build.log").write_text(completed.stdout + completed.stderr)
    completed.check_returncode()
    record = {"commit": identity["commit"], "source_sha256": digest(SOURCE / "src/motionexample.cpp"),
              "method_sha256": hashlib.sha256(method.encode()).hexdigest(),
              "generated_sha256": digest(generated), "library_sha256": digest(library),
              "command": command, "compiler": subprocess.check_output(
                  ["/usr/bin/clang++", "--version"], text=True),
              "scope": "Unmodified SDK scalar spline + local C ABI; no receiver/sender linked"}
    (OUTPUT / "build_identity.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    build()
