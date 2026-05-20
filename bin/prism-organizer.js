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
    const out = execSync(`${PYTHON_CMD} -m pip list`, {
      encoding: "utf-8",
    });
    return out.includes(PACKAGE_NAME);
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
 * Download the standalone binary from GitHub Releases.
 */
async function downloadBinary() {
  const https = require("https");
  const dest = path.join(os.homedir(), ".prism-organizer", "prism-organizer.exe");
  const destDir = path.dirname(dest);

  const { mkdirSync, createWriteStream } = require("fs");
  mkdirSync(destDir, { recursive: true });

  if (existsSync(dest)) {
    success(`Binary already exists: ${dest}`);
    return dest;
  }

  log("Downloading standalone binary...");
  const file = createWriteStream(dest);

  return new Promise((resolve, reject) => {
    https
      .get(GITHUB_RELEASES, { followAllRedirects: true }, (res) => {
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

        file.on("error", reject);
      })
      .on("error", (e) => {
        warn("Binary download failed. Falling back to Python.");
        resolve(null);
      });
  });
}

// ── Main ─────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);

  // Handle --install (postinstall hook)
  if (args.includes("--install")) {
    console.log("\n🔮 Prism Organizer — First-time Setup\n");

    if (!hasPython()) {
      warn("Python 3.8+ is not found on your PATH.");
      warn("Install Python from https://python.org and re-run.");
      process.exit(1);
    }

    if (!hasPipPackage()) {
      installPipPackage();
    } else {
      success("prism-organizer is already installed.");
    }

    console.log("\n  Run: prism-organizer --help\n");
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
