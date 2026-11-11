#!/usr/bin/env node
/**
 * @module scripts/backlog-lint
 *
 * Validates every story in `backlog/tasks/`. Run by `scripts/local-gate.sh` and CI.
 * Fails on: duplicate ids, file name / id mismatch, unknown status or priority, a parent or
 * dependency that does not exist, a story without one-liner or acceptance criteria, a Done story
 * without Branch & Commits rows, an In Progress story without owner or branch.
 *
 * Usage: node scripts/backlog-lint.mjs
 */

import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { STATUSES, idNum, loadTasks, normId } from "./lib/backlog-frontmatter.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PRIORITIES = new Set(["P0", "P1", "P2", "P3"]);
const tasks = loadTasks(join(root, "backlog/tasks"));
const ids = new Map();
const errors = [];
const err = (file, msg) => errors.push(`${file}: ${msg}`);

for (const t of tasks) {
  const id = normId(t.data.id);
  if (!/^SC-\d+(\.\d+)*$/.test(id)) err(t.file, `bad id "${t.data.id}"`);
  if (ids.has(id)) err(t.file, `duplicate id ${id} (also ${ids.get(id)})`);
  ids.set(id, t.file);
  if (!t.file.toLowerCase().startsWith(`sc-${idNum(id)} - `)) err(t.file, `file name must start with "sc-${idNum(id)} - "`);
}
for (const t of tasks) {
  const d = t.data;
  const labels = Array.isArray(d.labels) ? d.labels : [];
  const epic = labels.includes("epic");
  if (!STATUSES.includes(d.status)) err(t.file, `status "${d.status}" not in ${STATUSES.join(", ")}`);
  if (!PRIORITIES.has(d.priority)) err(t.file, `priority "${d.priority}" not in P0-P3`);
  if (!d.title) err(t.file, "missing title");
  if (d.parent_task_id && !ids.has(normId(d.parent_task_id))) err(t.file, `parent ${d.parent_task_id} does not exist`);
  for (const dep of Array.isArray(d.dependencies) ? d.dependencies : []) {
    if (!ids.has(normId(dep))) err(t.file, `dependency ${dep} does not exist`);
  }
  if (epic) continue;
  if (!d.parent_task_id) err(t.file, "a story needs parent_task_id (its epic)");
  if (!/^> \*\*One-liner\*\*: \S/m.test(t.body)) err(t.file, "missing '> **One-liner**: ...'");
  if ((t.body.match(/^- \[[ x]\] #\d+/gm) || []).length < 2) err(t.file, "needs at least 2 numbered acceptance criteria");
  if (d.status === "In Progress" && (!d.owner || !d.branch)) err(t.file, "In Progress needs owner and branch");
  if (d.status === "Done" && !/\| [^|\s-][^|]* \| [0-9a-f]{7,40} \|/.test(t.body)) {
    err(t.file, "Done needs a Branch & Commits row with a real commit hash");
  }
}

if (errors.length) {
  console.error(`✗ backlog-lint: ${errors.length} problem(s)\n  ${errors.join("\n  ")}`);
  process.exit(1);
}
console.log(`✓ backlog-lint: ${tasks.length} stories OK`);
