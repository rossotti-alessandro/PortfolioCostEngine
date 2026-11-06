/**
 * @module scripts/lib/backlog-frontmatter
 *
 * Minimal, dependency-free reader/writer for the YAML frontmatter of
 * `backlog/tasks/*.md`. Handles the subset the backlog uses: `key: scalar`,
 * `key: []`, and block lists (`key:` followed by `  - item`). Writes only
 * touch the scalar keys asked for, so the rest of the file is byte-stable.
 */

import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

/** Strip surrounding quotes from a YAML scalar. */
function unquote(v) {
  const t = v.trim();
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    return t.slice(1, -1);
  }
  return t;
}

/**
 * Parse the frontmatter block of a task file.
 * @param {string} text Full markdown file contents.
 * @returns {{ data: Record<string, string|string[]>, body: string }} Parsed keys + the markdown body.
 */
export function parseTask(text) {
  const m = text.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!m) return { data: {}, body: text };
  const data = {};
  let listKey = null;
  let foldKey = null;
  for (const line of m[1].split("\n")) {
    if (foldKey && /^\s+\S/.test(line)) {
      data[foldKey] = `${data[foldKey]} ${line.trim()}`.trim();
      continue;
    }
    foldKey = null;
    const item = line.match(/^\s+-\s+(.*)$/);
    if (item && listKey) {
      data[listKey].push(unquote(item[1]));
      continue;
    }
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (!kv) continue;
    const [, key, raw] = kv;
    if (/^[>|][-+]?$/.test(raw.trim())) {
      // Folded / literal block scalar: value continues on indented lines.
      data[key] = "";
      foldKey = key;
      listKey = null;
    } else if (raw === "") {
      data[key] = [];
      listKey = key;
    } else if (/^\[.*\]$/.test(raw.trim())) {
      data[key] = raw
        .trim()
        .slice(1, -1)
        .split(",")
        .map(unquote)
        .filter(Boolean);
      listKey = null;
    } else {
      data[key] = unquote(raw.replace(/\s+#.*$/, ""));
      listKey = null;
    }
  }
  return { data, body: text.slice(m[0].length) };
}

/** Ownership fields, in the order they appear after `assignee:`. */
export const OWNERSHIP_KEYS = ["owner", "model", "progress", "branch", "pr"];

/** Sort rank for a key: ownership keys first in canonical order. */
function rank(key) {
  const i = OWNERSHIP_KEYS.indexOf(key);
  return i < 0 ? OWNERSHIP_KEYS.length : i;
}

/**
 * Set scalar frontmatter keys in place, inserting missing keys after `assignee:` (or at the end).
 * @param {string} text Full markdown file contents.
 * @param {Record<string, string|number>} updates Keys to set; values are written as JSON-ish scalars.
 * @returns {string} The updated file contents.
 */
export function setFields(text, updates) {
  const m = text.match(/^---\n([\s\S]*?)\n---/);
  if (!m) throw new Error("task file has no frontmatter");
  const lines = m[1].split("\n");
  const ordered = Object.entries(updates).sort(
    ([a], [b]) => rank(a) - rank(b),
  );
  for (const [key, value] of ordered) {
    const rendered = typeof value === "number" ? String(value) : JSON.stringify(String(value));
    const idx = lines.findIndex((l) => l.startsWith(`${key}:`));
    if (idx >= 0) {
      // Drop any block-list items that belonged to the old value.
      let end = idx + 1;
      while (end < lines.length && /^\s+-\s/.test(lines[end])) end++;
      lines.splice(idx, end - idx, `${key}: ${rendered}`);
    } else {
      // Keep ownership keys grouped after `assignee:` in canonical order.
      const anchors = ["assignee", ...OWNERSHIP_KEYS];
      let at = -1;
      for (const k of anchors) {
        const i = lines.findIndex((l) => l.startsWith(`${k}:`));
        if (i > at) at = i;
      }
      if (at >= 0) {
        at++;
        while (at < lines.length && /^\s+-\s/.test(lines[at])) at++;
      } else at = lines.length;
      lines.splice(at, 0, `${key}: ${rendered}`);
    }
  }
  return text.replace(m[1], () => lines.join("\n"));
}

/**
 * Load every task under a directory.
 * @param {string} dir Absolute path to `backlog/tasks`.
 * @returns {Array<{ file: string, data: Record<string, any>, body: string }>} Parsed tasks.
 */
export function loadTasks(dir) {
  return readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .map((file) => ({ file, ...parseTask(readFileSync(join(dir, file), "utf8")) }));
}

/**
 * Find a task file by id (`SC-12`, `sc-12`, `12`, `12.3`).
 * @param {string} dir Absolute path to `backlog/tasks`.
 * @param {string} id Task id in any accepted casing.
 * @returns {string|null} Absolute path or null.
 */
export function findTaskFile(dir, id) {
  const norm = String(id).replace(/^sc-/i, "");
  const hit = readdirSync(dir).find((f) => f.toLowerCase().startsWith(`sc-${norm.toLowerCase()} `));
  return hit ? join(dir, hit) : null;
}

/**
 * Write updated fields to a task file on disk.
 * @param {string} path Absolute task file path.
 * @param {Record<string, string|number>} updates Keys to set.
 * @returns {void}
 */
export function updateTaskFile(path, updates) {
  writeFileSync(path, setFields(readFileSync(path, "utf8"), updates));
}

/** Normalise an id to `SC-<n>` upper-case form (`12`, `sc-12`, `SC-12` -> `SC-12`). */
export function normId(id) {
  const s = String(id || "").trim();
  if (!s) return "";
  return `SC-${s.replace(/^sc-/i, "")}`;
}

/** The numeric part of an id (`SC-12.3` -> `12.3`). */
export function idNum(id) {
  return normId(id).slice(3);
}

/** Allowed story statuses, in board order. */
export const STATUSES = ["To Do", "In Progress", "In Review", "Blocked", "Done"];
