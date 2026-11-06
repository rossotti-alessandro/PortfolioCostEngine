#!/usr/bin/env node
/**
 * @module scripts/backlog-new-id
 *
 * Reserve backlog story ids so parallel sessions never pick the same "next" number from a stale main.
 *
 * An id is free when no story file with it exists on main, was added on any origin/* branch in the last
 * 30 days, or exists in the working tree, and no reservation branch `backlog-ids/sc-<id>` exists.
 * Reserving pushes that branch; creating a branch is atomic and server-arbitrated, so the second
 * session is rejected and moves on to the next id.
 *
 * Usage:
 *   node scripts/backlog-new-id.mjs --parent SC-7    # next free SC-7.<n> (preferred: stories live under epics)
 *   node scripts/backlog-new-id.mjs                  # new top-level id (a new epic)
 *   node scripts/backlog-new-id.mjs --count 3
 */
import { execFileSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const git = (...a) => execFileSync("git", a, { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
const ID_RE = /sc-(\d+(?:\.\d+)*) - /i;

/** @returns {Set<string>} Every id ("7.4") seen on any branch, locally, or reserved. */
function takenIds() {
  const ids = new Set();
  const add = (name) => {
    const m = name.match(ID_RE);
    if (m) ids.add(m[1]);
  };
  git("fetch", "origin", "--quiet", "--prune");
  const added = git("log", "--remotes=origin", "--since=30.days", "--diff-filter=A", "--name-only", "--format=", "--", "backlog/tasks");
  for (const f of added.split("\n")) add(f.split("/").pop() || "");
  for (const f of git("ls-tree", "--name-only", "origin/main", "backlog/tasks/").split("\n")) add(f.split("/").pop() || "");
  for (const f of readdirSync(join(root, "backlog/tasks"))) add(f);
  for (const r of git("ls-remote", "origin", "refs/heads/backlog-ids/*").split("\n")) {
    const m = r.match(/sc-(\d+(?:\.\d+)*)$/);
    if (m) ids.add(m[1]);
  }
  return ids;
}

/**
 * Push the reservation branch; false if another session already holds it.
 * @param {string} id Id without the SC- prefix.
 * @returns {boolean} Whether this session now owns the id.
 */
function reserve(id) {
  const base = git("rev-parse", "origin/main");
  const msg = `reserve SC-${id} by ${process.env.OWNER || "agent"} at ${new Date().toISOString()}`;
  const commit = git("commit-tree", `${base}^{tree}`, "-p", base, "-m", msg);
  try {
    git("push", "--quiet", "origin", `${commit}:refs/heads/backlog-ids/sc-${id}`);
    return true;
  } catch {
    return false;
  }
}

const arg = (k) => {
  const i = process.argv.indexOf(k);
  return i > 0 ? process.argv[i + 1] : undefined;
};
const parent = (arg("--parent") || "").replace(/^sc-/i, "");
const count = Number(arg("--count") || 1);
const taken = takenIds();
const depth = parent ? parent.split(".").length + 1 : 1;
const nums = [...taken]
  .filter((id) => id.split(".").length === depth && (!parent || id.startsWith(`${parent}.`)))
  .map((id) => Number(id.split(".").pop()));
let next = (nums.length ? Math.max(...nums) : 0) + 1;
const out = [];
for (let tries = 0; out.length < count; tries++) {
  if (tries > 50) throw new Error("[backlog-new-id] could not reserve an id after 50 tries (is push to origin working?)");
  const id = parent ? `${parent}.${next}` : String(next);
  if (!taken.has(id) && reserve(id)) out.push(`SC-${id}`);
  next += 1;
}
process.stdout.write(`${out.join("\n")}\n`);
