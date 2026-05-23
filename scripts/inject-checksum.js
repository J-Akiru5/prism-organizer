/**
 * Checksum injection utility.
 * Calculates the SHA-256 hash of the compiled Windows executable
 * and registers it in the NPM wrapper's CHECKSUM_REGISTRY.
 */

const fs = require('fs');
const crypto = require('crypto');
const path = require('path');

const rootDir = path.join(__dirname, '..');
const exePath = path.join(rootDir, 'dist', 'prism-organizer.exe');
const jsPath = path.join(rootDir, 'bin', 'prism-organizer.js');

if (!fs.existsSync(exePath)) {
  console.error(`Error: ${exePath} not found.`);
  process.exit(1);
}

const hash = crypto.createHash('sha256').update(fs.readFileSync(exePath)).digest('hex');
console.log(`Built exe hash: ${hash}`);

if (!fs.existsSync(jsPath)) {
  console.error(`Error: ${jsPath} not found.`);
  process.exit(1);
}

let content = fs.readFileSync(jsPath, 'utf8');
const packageJsonPath = path.join(rootDir, 'package.json');
const version = require(packageJsonPath).version;

const registryRegex = /const CHECKSUM_REGISTRY = \{([^}]+)\};/;
const match = content.match(registryRegex);
if (match) {
  const currentRegistry = match[1];
  const entryRegex = new RegExp(`"${version}":\\s*"[^"]+"`);
  let newRegistry;
  if (entryRegex.test(currentRegistry)) {
    newRegistry = currentRegistry.replace(entryRegex, `"${version}": "${hash}"`);
  } else {
    newRegistry = currentRegistry.trim();
    if (newRegistry.endsWith(',')) {
      newRegistry += `\n  "${version}": "${hash}"`;
    } else {
      newRegistry += `,\n  "${version}": "${hash}"`;
    }
  }
  content = content.replace(registryRegex, `const CHECKSUM_REGISTRY = {\n  ${newRegistry.trim()}\n};`);
  fs.writeFileSync(jsPath, content, 'utf8');
  console.log(`Successfully injected checksum for v${version}: ${hash}`);
} else {
  console.error(`Could not find CHECKSUM_REGISTRY in ${jsPath}`);
  process.exit(1);
}
