import { spawn } from "node:child_process";
import { once } from "node:events";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";

export async function startFixture() {
  const child = spawn("python3", [fileURLToPath(new URL("../serve_fixture.py", import.meta.url))], {
    stdio: ["ignore", "pipe", "pipe"], env: { PATH: process.env.PATH, PYTHONUNBUFFERED: "1" },
  });
  let stderr = "";
  child.stderr.on("data", (data) => { stderr += data; });
  const lines = createInterface({ input: child.stdout });
  let timer;
  try {
    const info = await Promise.race([
      once(lines, "line").then(([line]) => JSON.parse(line)),
      once(child, "exit").then(([code]) => { throw new Error(`fixture_exited_${code}: ${stderr}`); }),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("fixture_start_timeout")), 5000); }),
    ]);
    return {
      url: info.url,
      close: async () => {
        lines.close();
        if (child.exitCode === null && child.signalCode === null) {
          const exited = once(child, "exit");
          child.kill("SIGTERM");
          await exited;
        }
      },
    };
  } catch (error) {
    child.kill("SIGTERM");
    lines.close();
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
