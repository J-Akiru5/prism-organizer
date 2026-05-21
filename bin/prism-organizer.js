#!/usr/bin/env node

/**
 * Prism Organizer — Zero-friction Node.js wrapper.
 *
 * Strategy (in order):
 * 1. Use cached standalone .exe if available (no Python needed)
 * 2. Auto-download .exe from GitHub Releases on first run
 * 3. Fall back to Python + pip only if binary download fails
 *
 * All error messages include copy-paste fix commands.
 */

const { spawn, execSync } = require("child_process");
const { existsSync, mkdirSync, createWriteStream, unlinkSync } = require("fs");
const path = require("path");
const os = require("os");

const BINARY_NAME = "prism-organizer.exe";
const CACHE_DIR = path.join(os.homedir(), ".prism-organizer");
const BINARY_PATH = path.join(CACHE_DIR, BINARY_NAME);
const VERSION_PATH = path.join(CACHE_DIR, ".binary-version");
const WRAPPER_VERSION = "1.2.12";
const DOWNLOAD_URL =
  "https://github.com/J-Akiru5/prism-organizer/releases/latest/download/prism-organizer.exe";
const PIP_URL =
  "git+https://github.com/J-Akiru5/prism-organizer.git";
const PYTHON_CMD = "python";
const PACKAGE_MODULE = "prism_organizer";

// ── Output helpers ────────────────────────────────────────────────────

function cyan(msg)  { process.stderr.write(`  \x1b[36mℹ\x1b[0m ${msg}\n`); }
function green(msg) { process.stderr.write(`  \x1b[32m✓\x1b[0m ${msg}\n`); }
function yellow(msg){ process.stderr.write(`  \x1b[33m⚠\x1b[0m ${msg}\n`); }
function red(msg)   { process.stderr.write(`  \x1b[31m✗\x1b[0m ${msg}\n`); }

function splash() {
  process.stderr.write([
    "",
    "\x1b[35m  ╔══════════════════════════════════════════╗\x1b[0m",
    "\x1b[35m  ║\x1b[0m  \x1b[35;1m🔮  Prism Organizer\x1b[0m                      \x1b[35m║\x1b[0m",
    "\x1b[35m  ║\x1b[0m  \x1b[90mScan • Sort • Clean • Organize\x1b[0m        \x1b[35m║\x1b[0m",
    "\x1b[35m  ╚══════════════════════════════════════════╝\x1b[0m",
    "",
  ].join("\n"));
}

// ── Helpers ───────────────────────────────────────────────────────────

function hasPython() {
  try { execSync(`"${PYTHON_CMD}" --version`, { stdio: "ignore" }); return true; }
  catch { return false; }
}

function hasPipPackage() {
  try {
    const out = execSync(`"${PYTHON_CMD}" -m pip list --format=columns`, { encoding: "utf-8", timeout: 15000 });
    return /^prism[_-]organizer\s/im.test(out);
  } catch { return false; }
}

function installPipPackage() {
  cyan("Installing Prism Organizer via pip (one-time)...");
  try {
    execSync(`"${PYTHON_CMD}" -m pip install ${PIP_URL} --quiet`, { stdio: "inherit", timeout: 120000 });
    green("Prism Organizer installed.");
    return true;
  } catch (e) {
    red("pip install failed. Try manually:");
    process.stderr.write(`    pip install ${PIP_URL}\n`);
    return false;
  }
}

/**
 * Follow-redirects HTTP GET helper.
 */
function httpGet(url, maxRedirects, callback) {
  const proto = url.startsWith("https") ? require("https") : require("http");
  proto.get(url, (res) => {
    if ([301, 302, 307, 308].includes(res.statusCode) && res.headers.location) {
      if (maxRedirects <= 0) return callback(new Error("Too many redirects"));
      res.resume();
      return httpGet(res.headers.location, maxRedirects - 1, callback);
    }
    if (res.statusCode >= 400) {
      res.resume();
      return callback(new Error(`HTTP ${res.statusCode}`));
    }
    callback(null, res);
  }).on("error", callback);
}

/**
 * Download the standalone .exe from GitHub Releases (≈30 MB).
 * Returns the binary path on success, null on failure.
 *
 * On cache hit, the stored version is compared with WRAPPER_VERSION.
 * If they differ (e.g. after an npm update), the old binary is
 * deleted and a fresh one is downloaded.
 */
function downloadBinary() {
  const { readFileSync, writeFileSync } = require("fs");
  const tmpPath = BINARY_PATH + ".tmp";
  return new Promise((resolve) => {
    // Cache hit — check if version matches
    if (existsSync(BINARY_PATH)) {
      try {
        const storedVersion = readFileSync(VERSION_PATH, "utf-8").trim();
        if (storedVersion === WRAPPER_VERSION) {
          return resolve(BINARY_PATH);
        }
        // Version mismatch — delete old binary and re-download
        yellow(`Binary is for v${storedVersion}, updating to v${WRAPPER_VERSION}...`);
        try { unlinkSync(BINARY_PATH); } catch (_) {}
        try { unlinkSync(VERSION_PATH); } catch (_) {}
      } catch {
        // No version file — might be from before version tracking
      }
    }

    // Recover from interrupted download (leftover .tmp file)
    const tmpPath = BINARY_PATH + ".tmp";
    if (!existsSync(BINARY_PATH) && existsSync(tmpPath)) {
      try {
        require("fs").renameSync(tmpPath, BINARY_PATH);
        try { writeFileSync(VERSION_PATH, WRAPPER_VERSION, "utf-8"); } catch (_) {}
        cyan("Recovered partially downloaded binary.");
        return resolve(BINARY_PATH);
      } catch (_) {
        try { unlinkSync(tmpPath); } catch (_) {}
      }
    }

    mkdirSync(CACHE_DIR, { recursive: true });
    cyan("Downloading Prism Organizer (one-time, ~30MB)...");
    cyan("This removes the Python requirement entirely.");

    // Download to temp file first to avoid EBUSY on locked binary

    httpGet(DOWNLOAD_URL, 5, (err, res) => {
      if (err) {
        yellow(`Binary download unavailable (${err.message}).`);
        resolve(null);
        return;
      }

      // Clean up any existing tmp file
      try { unlinkSync(tmpPath); } catch (_) {}

      const total = parseInt(res.headers["content-length"], 10) || 0;
      let downloaded = 0;
      const file = createWriteStream(tmpPath);

      res.on("data", (chunk) => {
        downloaded += chunk.length;
        if (total) process.stderr.write(`\r  Downloading... ${((downloaded / total) * 100).toFixed(0)}%`);
      });

      res.pipe(file);

      file.on("finish", () => {
        file.close();
        // Atomically replace old binary with new one
        let finalPath = tmpPath;
        try { unlinkSync(BINARY_PATH); } catch (_) {}
        try {
          require("fs").renameSync(tmpPath, BINARY_PATH);
          finalPath = BINARY_PATH;
        } catch (_) {
          yellow("Binary will update on next restart. Using downloaded copy.");
        }
        // Write version marker
        try {
          writeFileSync(VERSION_PATH, WRAPPER_VERSION, "utf-8");
        } catch (_) {}
        process.stderr.write("\r\x1b[K");
        green("Download complete. Prism Organizer is ready!");
        resolve(finalPath);
      });

      file.on("error", (e) => {
        try { unlinkSync(BINARY_PATH); } catch (_) {}
        yellow(`Download failed: ${e.message}`);
        resolve(null);
      });
    });
  });
}

/**
 * Show a friendly error when neither binary nor Python is available.
 */
function showNoRuntimeError() {
  splash();
  red("Prism Organizer couldn't find a runtime on your system.");
  process.stderr.write("\n");
  cyan("Quick fix — install Python 3.8+ (3 minutes):");
  cyan("  1. Download: https://python.org/downloads/");
  cyan("  2. During install: CHECK 'Add Python to PATH'");
  cyan("  3. Then run: pip install " + PIP_URL);
  process.stderr.write("\n");
  cyan("Alternative — download the standalone .exe:");
  cyan("  " + DOWNLOAD_URL);
  cyan("  Save it anywhere on your PATH.");
  process.stderr.write("\n");
  yellow("To remove Prism Organizer: npm uninstall -g prism-organizer");
  yellow("                         rm -rf ~/.prism-organizer");
}

// ── Main ──────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);

  // --install (postinstall hook) — best-effort binary download, never fails
  if (args.includes("--install")) {
    process.stderr.write("\n🔮 Prism Organizer — Setup\n\n");
    await downloadBinary();  // best-effort
    if (hasPython()) {
      hasPipPackage() ? green("Python runtime ready.") : installPipPackage();
    }
    process.stderr.write("\n  Run: prism-organizer --help\n\n");
    process.exit(0);
  }

  // --uninstall helper
  if (args.includes("--uninstall")) {
    process.stderr.write("\n  To uninstall Prism Organizer:\n\n");
    process.stderr.write("    npm uninstall -g prism-organizer\n");
    process.stderr.write("    rm -rf ~/.prism-organizer\n\n");
    process.exit(0);
  }

  // ── Strategy: binary first, Python second ──────────────────────

  // 1. Try cached or downloadable binary
  const binary = await downloadBinary();

  if (binary) {
    const child = spawn(binary, args, { stdio: "inherit" });
    child.on("close", (code) => process.exit(code));
    child.on("error", () => {
      // Binary corrupt — delete and retry
      try { unlinkSync(BINARY_PATH); } catch (_) {}
      red("Binary failed. Run again to re-download.");
      process.exit(1);
    });
    return;
  }

  // 2. Fall back to Python
  if (!hasPython()) {
    showNoRuntimeError();
    process.exit(1);
  }

  if (!hasPipPackage() && !installPipPackage()) {
    process.exit(1);
  }

  const child = spawn(PYTHON_CMD, ["-u", "-m", PACKAGE_MODULE, ...args], {
    stdio: "inherit",
  });
  child.on("close", (code) => process.exit(code));
  child.on("error", (err) => {
    red(`Failed: ${err.message}`);
    process.exit(1);
  });
}

main();
