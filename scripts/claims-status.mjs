#!/usr/bin/env node
/**
 * @module scripts/claims-status
 *
 * Who is working on what, judged from REMOTE evidence only, so the answer is the same on a laptop and
 * in a fresh cloud container (which never has the other sessions' worktrees).
 *
 * A story is LIVE when any of these is younger than the TTL (default 48h):
 *   - its claim branch `claims/sc-<id>`,
 *   - the newest commit on a remote branch whose name contains `sc-<id>` or equals the story's `branch:`,
 *   - the story's frontmatter `owner` with an `updated_date` inside the TTL.
 * Everything else that is claimed or In Progress is STALE. Stale is a report, never an action:
 * releasing a claim stays a coordinator decision (AGENTS.md § Claiming).
 *
 * Usage:
 *   node scripts/claims-status.mjs            # table
 *   node scripts/claims-status.mjs --summary  # one line
 *   node scripts/claims-status.mjs --json
 */

import { execFileSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { idNum, loadTasks, normId } from "./lib/backlog-frontmatter.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const TTL_H = Number(process.env.CLAIM_TTL_HOURS || 48);
const now = Date.now() / 1000;
const git = (...a) => {
  try {
    return execFileSync("git", a, { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  } catch {
    return "";
  }
};
const ageH = (ts) => Math.round((now - ts) / 3600);

git("fetch", "origin", "--quiet", "--prune");
const refs = git("for-each-ref", "--format=%(refname:lstrip=3)\t%(committerdate:unix)\t%(subject)", "refs/remotes/origin")
  .split("\n")
  .filter(Boolean)
  .map((l) => {
    const [ref, ts, subject] = l.split("\t");
    return { ref, ts: Number(ts), subject };
  });
const claims = new Map(refs.filter((r) => r.ref.startsWith("claims/sc-")).map((r) => [normId(r.ref.slice(7)), r]));

const rows = [];
for (const t of loadTasks(join(root, "backlog/tasks"))) {
  const id = normId(t.data.id);
  const status = t.data.status || "To Do";
  const claim = claims.get(id);
  if (status !== "In Progress" && status !== "In Review" && !claim) continue;
  const re = new RegExp(`sc-${idNum(id).replace(/\./g, "\\.")}(?![\\d.])`, "i");
  const branch = refs
    .filter((r) => !r.ref.startsWith("claims/") && !r.ref.startsWith("backlog-ids/"))
    .filter((r) => re.test(r.ref) || (t.data.branch && r.ref === t.data.branch))
    .sort((a, b) => b.ts - a.ts)[0];
  const updated = Date.parse(`${String(t.data.updated_date || "").replace(" ", "T")}Z`) / 1000 || 0;
  const signals = [claim?.ts, branch?.ts, t.data.owner ? updated : 0].filter(Boolean);
  const last = signals.length ? Math.max(...signals) : 0;
  rows.push({
    id,
    status,
    owner: t.data.owner || "-",
    claim: claim ? `${ageH(claim.ts)}h` : "-",
    branch: branch ? `${branch.ref} (${ageH(branch.ts)}h)` : "-",
    verdict: last && ageH(last) < TTL_H ? "LIVE" : "STALE",
  });
}
rows.sort((a, b) => a.id.localeCompare(b.id, "en", { numeric: true }));

if (process.argv.includes("--json")) console.log(JSON.stringify(rows, null, 1));
else if (process.argv.includes("--summary")) {
  const live = rows.filter((r) => r.verdict === "LIVE").map((r) => r.id);
  console.log(`live (<${TTL_H}h remote activity): ${live.join(" ") || "none"} · stale: ${rows.length - live.length}`);
} else {
  console.log(`Claims and In Progress stories, remote evidence, TTL ${TTL_H}h\n`);
  console.log("verdict\tstory\tstatus\towner\tclaim age\tbranch (age)");
  for (const r of rows) console.log(`${r.verdict}\t${r.id}\t${r.status}\t${r.owner}\t${r.claim}\t${r.branch}`);
  if (!rows.length) console.log("(nothing claimed)");
}
