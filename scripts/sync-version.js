#!/usr/bin/env node

/**
 * Version synchronisation utility.
 * Synchronises version numbers from package.json to python / npm files.
 */

const fs = require("fs");
const path = require("path");

const rootDir = path.join(__dirname, "..");

function syncVersion() {
  const packageJsonPath = path.join(rootDir, "package.json");
  if (!fs.existsSync(packageJsonPath)) {
    console.error("Error: package.json not found.");
    process.exit(1);
  }

  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));
  const version = packageJson.version;
  console.log(`Syncing version v${version} across all files...`);

  // 1. Update prism_organizer/__init__.py
  const initPyPath = path.join(rootDir, "prism_organizer", "__init__.py");
  if (fs.existsSync(initPyPath)) {
    let initContent = fs.readFileSync(initPyPath, "utf8");
    const updatedInit = initContent.replace(
      /__version__\s*=\s*["'][^"']+["']/,
      `__version__ = "${version}"`
    );
    if (initContent !== updatedInit) {
      fs.writeFileSync(initPyPath, updatedInit, "utf8");
      console.log(`✔ Updated: prism_organizer/__init__.py`);
    } else {
      console.log(`- Unchanged: prism_organizer/__init__.py`);
    }
  }

  // 2. Update setup.py
  const setupPyPath = path.join(rootDir, "setup.py");
  if (fs.existsSync(setupPyPath)) {
    let setupContent = fs.readFileSync(setupPyPath, "utf8");
    const updatedSetup = setupContent.replace(
      /version\s*=\s*["'][^"']+["']/,
      `version="${version}"`
    );
    if (setupContent !== updatedSetup) {
      fs.writeFileSync(setupPyPath, updatedSetup, "utf8");
      console.log(`✔ Updated: setup.py`);
    } else {
      console.log(`- Unchanged: setup.py`);
    }
  }

  // 3. Update bin/prism-organizer.js
  const binJsPath = path.join(rootDir, "bin", "prism-organizer.js");
  if (fs.existsSync(binJsPath)) {
    let binContent = fs.readFileSync(binJsPath, "utf8");
    let updatedBin = binContent;

    // Replace WRAPPER_VERSION
    updatedBin = updatedBin.replace(
      /const WRAPPER_VERSION\s*=\s*["'][^"']+["'];/,
      `const WRAPPER_VERSION = "${version}";`
    );

    // Replace DOWNLOAD_URL release tag / filename if matching download format
    updatedBin = updatedBin.replace(
      /releases\/download\/v[^/]+\/prism-organizer\.exe/,
      `releases/download/v${version}/prism-organizer.exe`
    );

    // Replace PIP_URL version
    updatedBin = updatedBin.replace(
      /prism-organizer==[^"';\s]+/,
      `prism-organizer==${version}`
    );

    if (binContent !== updatedBin) {
      fs.writeFileSync(binJsPath, updatedBin, "utf8");
      console.log(`✔ Updated: bin/prism-organizer.js`);
    } else {
      console.log(`- Unchanged: bin/prism-organizer.js`);
    }
  }

  console.log("Version sync completed successfully!");
}

syncVersion();
