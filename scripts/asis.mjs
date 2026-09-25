#!/usr/bin/env node
/**
 * One-command A.S.I.S. launcher: `npm run ASIS`.
 *
 *  1. Ensures `.venv` exists — via `py setup_venv.py` first (uv-based,
 *     WDAC-safe classic layout), falling back to plain `py -3.12 -m venv`
 *     + pip when uv is unavailable. Reinstalls light deps only when the
 *     venv python or the `asis.cli.main` import is broken. Voice extras
 *     (heavy torch stack) are never auto-installed; a hint is printed
 *     when `voice` mode is requested without them.
 *  2. Ensures Ollama is up: connects when already running (never owned),
 *     otherwise starts a detached `ollama serve` it owns, polling
 *     `/api/tags` up to 60s. Then verifies `qwen3:14b` is pulled — fails
 *     fast with the exact `ollama pull` command, never silently pulls GBs.
 *  3. Launches `.venv\Scripts\python.exe -m asis <args>` with inherited
 *     stdio (REPL + voice need a TTY), forwarding the exit code. No args
 *     → interactive REPL via the existing `entry()` default.
 *  4. On exit, stops ONLY a launcher-owned server. A pre-existing server
 *     is left alone.
 *
 * Modes: `voice` starts voice mode; `--check` runs a fast boot probe
 * (`asis --identify`); `--test` runs pytest. Anything after `--`
 * (`npm run ASIS -- --message "hi"`) is forwarded to `python -m asis`.
 *
 * Stdlib only (child_process, fs, http, os, path, url).
 */

import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { get } from "node:http";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import os from "node:os";

const ROOT = resolve(join(dirname(fileURLToPath(import.meta.url)), ".."));
const IS_WINDOWS = os.platform() === "win32";
const VENV_PYTHON = IS_WINDOWS
  ? join(ROOT, ".venv", "Scripts", "python.exe")
  : join(ROOT, ".venv", "bin", "python");
// Launcher used to create the venv: `py` on Windows, `python3` on POSIX.
const PYTHON_LAUNCHER = IS_WINDOWS ? "py" : "python3";
// Overridable for testing (e.g. ASIS_OLLAMA_PORT=1 forces the down-path).
const OLLAMA_HOST = process.env.ASIS_OLLAMA_HOST ?? "127.0.0.1";
const OLLAMA_PORT = Number(process.env.ASIS_OLLAMA_PORT ?? 11434);
// Bind address for a launcher-started `ollama serve` (OLLAMA_HOST format).
// Override for sandbox tests, e.g. ASIS_OLLAMA_SERVE_BIND=127.0.0.1:11435,
// so the live :11434 server is never disturbed.
const SERVE_BIND = process.env.ASIS_OLLAMA_SERVE_BIND ?? "127.0.0.1:11434";
const MODEL = "qwen3:14b";
// Slow machines need longer for first boot (cold GPU discovery under RAM
// pressure); override with ASIS_OLLAMA_SERVE_TIMEOUT_S.
const SERVE_READY_TIMEOUT_MS =
  Number(process.env.ASIS_OLLAMA_SERVE_TIMEOUT_S ?? 120) * 1000;

function fail(message, code = 2) {
  console.error(`asis: ERROR: ${message}`);
  process.exit(code);
}

/** Run a command with inherited stdio; return its exit code. */
function runForeground(cmd, args) {
  const result = spawnSync(cmd, args, { stdio: "inherit", cwd: ROOT });
  if (result.error) {
    fail(`could not run '${cmd}': ${result.error.message}`);
  }
  return result.status ?? 1;
}

/** Run a command quietly; return { status, error }. */
function runQuiet(cmd, args) {
  const result = spawnSync(cmd, args, {
    stdio: "pipe",
    encoding: "utf8",
    cwd: ROOT,
  });
  return { status: result.status ?? 1, error: result.error ?? null };
}

function commandExists(cmd) {
  const probe = IS_WINDOWS
    ? runQuiet("where", [cmd])
    : runQuiet("sh", ["-c", `command -v ${cmd}`]);
  return probe.status === 0;
}

function ensureVenv() {
  if (existsSync(VENV_PYTHON)) {
    const probe = runQuiet(VENV_PYTHON, ["-c", "import asis.cli.main; import textual"]);
    if (probe.status === 0) return; // healthy venv, nothing to do
    console.error(
      "asis: venv python or 'asis' import is broken; reinstalling light deps..."
    );
    const code = runForeground(VENV_PYTHON, [
      "-m",
      "pip",
      "install",
      "-r",
      "requirements.txt",
      "-r",
      "requirements/development.txt",
      "-r",
      "requirements/tui.txt",
    ]);
    if (code !== 0) {
      fail("pip install failed; run setup_venv.py manually and retry.");
    }
    return;
  }
  if (commandExists("uv")) {
    console.error("asis: creating .venv via setup_venv.py (uv) ...");
    const code = runForeground(PYTHON_LAUNCHER, ["setup_venv.py"]);
    if (code === 0 && existsSync(VENV_PYTHON)) return;
    console.error("asis: setup_venv.py failed; falling back to plain venv ...");
  } else {
    console.error("asis: 'uv' not found; falling back to plain venv ...");
  }
  let created = false;
  const fallbacks = IS_WINDOWS
    ? [
        ["py", "-3.12"],
        ["py", "-3"],
      ]
    : [[PYTHON_LAUNCHER]];
  for (const launcher of fallbacks) {
    const result = runQuiet(launcher[0], [
      ...launcher.slice(1),
      "-m",
      "venv",
      ".venv",
    ]);
    if (result.status === 0 && existsSync(VENV_PYTHON)) {
      created = true;
      break;
    }
  }
  if (!created) {
    fail(
      IS_WINDOWS
        ? "could not create .venv. Install uv (https://docs.astral.sh/uv/) or Python 3.12+ with the 'py' launcher and retry."
        : "could not create .venv. Install uv (https://docs.astral.sh/uv/) or have Python 3.12+ available as 'python3' and retry."
    );
  }
  runForeground(VENV_PYTHON, ["-m", "pip", "install", "--upgrade", "pip"]);
  const deps = runForeground(VENV_PYTHON, [
    "-m",
    "pip",
    "install",
    "-r",
    "requirements.txt",
    "-r",
    "requirements/development.txt",
    "-r",
    "requirements/tui.txt",
  ]);
  if (deps !== 0) fail("pip install failed.");
}

function voiceDepsPresent() {
  const probe = runQuiet(VENV_PYTHON, ["-c", "import sounddevice"]);
  return probe.status === 0;
}

function fetchJson(path) {
  return new Promise((resolvePromise, rejectPromise) => {
    const request = get(
      { host: OLLAMA_HOST, port: OLLAMA_PORT, path, timeout: 5000 },
      (response) => {
        let body = "";
        response.on("data", (chunk) => {
          body += chunk;
        });
        response.on("end", () => {
          try {
            resolvePromise(JSON.parse(body));
          } catch (error) {
            rejectPromise(error);
          }
        });
      }
    );
    request.on("timeout", () => {
      request.destroy(new Error("timed out"));
    });
    request.on("error", rejectPromise);
  });
}

async function ollamaUp() {
  try {
    await fetchJson("/api/tags");
    return true;
  } catch {
    return false;
  }
}

function sleep(ms) {
  return new Promise((resolvePromise) => setTimeout(resolvePromise, ms));
}

/**
 * Ensure an Ollama server is reachable. Returns `{ owned, servePid }`:
 * `owned` is true only when this launcher started `ollama serve` itself.
 */
async function ensureOllama() {
  if (await ollamaUp()) {
    return { owned: false, servePid: null };
  }
  console.error("asis: Ollama is down; starting 'ollama serve' ...");
  const server = spawn("ollama", ["serve"], {
    detached: true,
    stdio: "ignore",
    cwd: ROOT,
    env: { ...process.env, OLLAMA_HOST: SERVE_BIND },
  });
  let spawnError = null;
  server.on("error", (error) => {
    spawnError = error;
  });
  // Give spawn a tick to report ENOENT (missing binary) before polling.
  await sleep(500);
  if (spawnError) {
    fail(
      `could not spawn 'ollama' (${spawnError.message}). Install Ollama (https://ollama.com) and ensure it is on PATH, or start it with 'ollama serve' and retry.`
    );
  }
  if (server.exitCode !== null) {
    fail(
      `'ollama serve' exited immediately (code ${server.exitCode}). Start it manually with 'ollama serve' to see why, then retry.`
    );
  }
  server.unref();
  const deadline = Date.now() + SERVE_READY_TIMEOUT_MS;
  while (Date.now() < deadline) {
    await sleep(1000);
    if (await ollamaUp()) {
      console.error("asis: Ollama server is up (launcher-owned).");
      return { owned: true, servePid: server.pid };
    }
  }
  stopServeProcess(server.pid);
  fail(
    `'ollama serve' did not become ready within ${
      SERVE_READY_TIMEOUT_MS / 1000
    }s. Start it manually with 'ollama serve' to see why, then retry.`
  );
}

/** Best-effort kill of a serve PID we started. Never throws. */
function stopServeProcess(pid) {
  try {
    if (pid == null) return;
    if (IS_WINDOWS) {
      spawnSync("taskkill", ["/PID", String(pid), "/F"], { stdio: "ignore" });
    } else {
      process.kill(pid, "SIGTERM");
    }
  } catch {
    // best-effort only
  }
}

/** Best-effort unload of the active model. Never throws. */
function unloadModel(model) {
  try {
    // Scope the CLI to the launcher-owned server so a pre-existing
    // :11434 server is never touched.
    spawnSync("ollama", ["stop", model], {
      stdio: "ignore",
      timeout: 60000,
      env: { ...process.env, OLLAMA_HOST: SERVE_BIND },
    });
  } catch {
    // best-effort only
  }
}

async function checkModel() {
  const tags = await fetchJson("/api/tags");
  const names = new Set((tags.models ?? []).map((model) => model.name));
  const present = [...names].some((name) => name.startsWith(MODEL));
  if (!present) {
    fail(
      `model '${MODEL}' is not pulled. Run 'ollama pull ${MODEL}', then retry.`
    );
  }
}

async function main() {
  const rawArgs = process.argv.slice(2);
  process.chdir(ROOT);
  ensureVenv();

  if (rawArgs.includes("--test")) {
    process.exit(runForeground(VENV_PYTHON, ["-m", "pytest", "-q"]));
  }

  if (rawArgs[0] === "voice" && !voiceDepsPresent()) {
    console.error(
      "asis: voice extras are not installed; voice mode will use mock engines."
    );
    console.error(
      "asis: for real audio run: uv pip install -r requirements/voice.txt"
    );
  }

  if (rawArgs.includes("--check")) {
    process.exit(runForeground(VENV_PYTHON, ["-m", "asis", "--identify"]));
  }

  const { owned, servePid } = await ensureOllama();
  await checkModel();

  const child = spawn(VENV_PYTHON, ["-m", "asis", ...rawArgs], {
    stdio: "inherit",
  });
  const shutdownOwned = () => {
    if (owned) {
      unloadModel(MODEL);
      stopServeProcess(servePid);
    }
  };
  child.on("error", (error) => {
    shutdownOwned();
    fail(`could not launch asis: ${error.message}`);
  });
  child.on("exit", (code, signal) => {
    shutdownOwned();
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 1);
  });
}

await main();
