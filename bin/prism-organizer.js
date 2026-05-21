#!/usr/bin/env node

/**
 * Prism Organizer — Node.js wrapper
 *
 * Checks for Python + prism-organizer installation, handles the
 * `--install` postinstall hook, and proxies all CLI arguments.
 *
 * With --with-binary: downloads a PyInstaller-built .exe instead of
 * using Python.
 */

const { spawn, execSync } = require("child_process");
const { existsSync } = require("fs");
const path = require("path");
const os = require("os");

const PACKAGE_NAME = "prism_organizer";
const PYTHON_CMD = "python";
const PIP_URL =
  "git+https://github.com/J-Akiru5/prism-organizer.git";
const GITHUB_RELEASES =
  "https://github.com/J-Akiru5/prism-organizer/releases/latest/download/prism-organizer.exe";

// ── Helpers ──────────────────────────────────────────────────────────

function log(msg) {
  process.stderr.write(`  \x1b[36mℹ\x1b[0m ${msg}\n`);
}

function warn(msg) {
  process.stderr.write(`  \x1b[33m⚠\x1b[0m ${msg}\n`);
}

function error(msg) {
  process.stderr.write(`  \x1b[31m✗\x1b[0m ${msg}\n`);
}

function success(msg) {
  process.stderr.write(`  \x1b[32m✓\x1b[0m ${msg}\n`);
}

/**
 * Check if Python is available on PATH.
 */
function hasPython() {
  try {
    execSync(`${PYTHON_CMD} --version`, { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if the prism_organizer pip package is installed.
 */
function hasPipPackage() {
  try {
    const out = execSync(`${PYTHON_CMD} -m pip list --format=columns`, {
      encoding: "utf-8",
    });
    // Match the exact package name at the start of a line to avoid
    // false positives from packages whose names contain our name.
    return /^prism[_-]organizer\s/im.test(out);
  } catch {
    return false;
  }
}

/**
 * Install the pip package from GitHub.
 */
function installPipPackage() {
  log("Installing prism-organizer via pip...");
  try {
    execSync(`${PYTHON_CMD} -m pip install ${PIP_URL} --quiet`, {
      stdio: "inherit",
    });
    success("prism-organizer installed successfully.");
    return true;
  } catch (e) {
    error("Failed to install prism-organizer via pip.");
    console.error(e.message);
    return false;
  }
}

/**
 * Download a URL, following HTTP 301/302 redirects up to `maxRedirects`.
 */
function followRedirects(url, maxRedirects, callback) {
  const proto = url.startsWith("https") ? require("https") : require("http");
  proto.get(url, (res) => {
    if (
      (res.statusCode === 301 || res.statusCode === 302) &&
      res.headers.location
    ) {
      if (maxRedirects <= 0) {
        callback(new Error("Too many redirects"), null);
        return;
      }
      // Consume the response body before following redirect
      res.resume();
      followRedirects(res.headers.location, maxRedirects - 1, callback);
    } else if (res.statusCode === 200) {
      callback(null, res);
    } else {
      res.resume();
      callback(
        new Error(`Download failed with HTTP ${res.statusCode}`),
        null
      );
    }
  }).on("error", (e) => callback(e, null));
}

/**
 * Download the standalone binary from GitHub Releases.
 */
async function downloadBinary() {
  const dest = path.join(
    os.homedir(),
    ".prism-organizer",
    "prism-organizer.exe"
  );
  const destDir = path.dirname(dest);

  const { mkdirSync, createWriteStream, unlinkSync } = require("fs");
  mkdirSync(destDir, { recursive: true });

  if (existsSync(dest)) {
    success(`Binary already exists: ${dest}`);
    return dest;
  }

  log("Downloading standalone binary...");
  const file = createWriteStream(dest);

  return new Promise((resolve) => {
    followRedirects(GITHUB_RELEASES, 5, (err, res) => {
      if (err) {
        warn(`Binary download failed: ${err.message}. Falling back to Python.`);
        try { file.close(); unlinkSync(dest); } catch (_) {}
        resolve(null);
        return;
      }

      const total = parseInt(res.headers["content-length"], 10);
      let downloaded = 0;

      res.on("data", (chunk) => {
        downloaded += chunk.length;
        if (total) {
          const pct = ((downloaded / total) * 100).toFixed(1);
          process.stderr.write(`\r  Downloading... ${pct}%`);
        }
      });

      res.pipe(file);

      file.on("finish", () => {
        file.close();
        process.stderr.write("\r\x1b[K");
        success("Binary downloaded.");
        resolve(dest);
      });

      file.on("error", (e) => {
        warn(`Binary download failed: ${e.message}. Falling back to Python.`);
        try { unlinkSync(dest); } catch (_) {}
        resolve(null);
      });
    });
  });
}

// ── Main ─────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);

  // Handle --install (postinstall hook)
  // IMPORTANT: This must NEVER exit with a non-zero code, otherwise
  // `npm install -g prism-organizer` will fail and roll back.
  if (args.includes("--install")) {
    console.log("\n🔮 Prism Organizer — First-time Setup\n");

    if (!hasPython()) {
      warn("Python 3.8+ is not found on your PATH.");
      log("");
      log("  To use prism-organizer, install Python from:");
      log("  https://python.org/downloads/");
      log("");
      log("  After installing Python, run:");
      log("    pip install git+https://github.com/J-Akiru5/prism-organizer.git");
      log("");
      // Exit 0 so npm install succeeds even without Python
      process.exit(0);
    }

    if (!hasPipPackage()) {
      if (!installPipPackage()) {
        warn("Automatic pip installation failed.");
        log("You can install manually with:");
        log("  pip install git+https://github.com/J-Akiru5/prism-organizer.git");
      }
    } else {
      success("prism-organizer is already installed.");
    }

    console.log("\n  Run: prism-organizer --help\n");
    // Always exit 0 — postinstall is best-effort
    process.exit(0);
  }

  // Handle --with-binary
  const useBinary = args.includes("--with-binary");
  const actualArgs = args.filter((a) => a !== "--with-binary");

  let cmd, cmdArgs;

  if (useBinary) {
    const binaryPath = await downloadBinary();
    if (binaryPath) {
      cmd = binaryPath;
      cmdArgs = actualArgs;
    } else {
      // Fall back to Python
      if (!hasPython()) {
        error("Python is required. Install from https://python.org");
        process.exit(1);
      }
      if (!hasPipPackage()) {
        if (!installPipPackage()) process.exit(1);
      }
      cmd = PYTHON_CMD;
      cmdArgs = ["-m", PACKAGE_NAME, ...actualArgs];
    }
  } else {
    // Standard Python mode
    if (!hasPython()) {
      error("Python 3.8+ is required. Install from https://python.org");
      process.exit(1);
    }

    if (!hasPipPackage()) {
      warn("prism-organizer is not installed. Installing now...");
      if (!installPipPackage()) process.exit(1);
    }

    cmd = PYTHON_CMD;
    cmdArgs = ["-u", "-m", PACKAGE_NAME, ...actualArgs];
  }

  // Spawn the child process
  const child = spawn(cmd, cmdArgs, {
    stdio: "inherit",
    shell: true,
  });

  child.on("close", (code) => {
    process.exit(code);
  });

  child.on("error", (err) => {
    error(`Failed to start: ${err.message}`);
    process.exit(1);
  });
}

main();
