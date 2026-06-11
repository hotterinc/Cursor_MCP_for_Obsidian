import type { App } from "obsidian";

/** Master row — toggles all folders below. */
export const ALL_VAULT_PATH = "*";

export interface FolderNode {
  path: string;
  name: string;
  depth: number;
}

export interface FolderAccess {
  read: boolean;
  write: boolean;
}

const SKIP_PREFIXES = [".obsidian", ".trash", ".git"];

export function listVaultFolderNodes(app: App): FolderNode[] {
  const nodes: FolderNode[] = [
    { path: ALL_VAULT_PATH, name: "Весь vault", depth: 0 },
    { path: "", name: "Файлы в корне (без папки)", depth: 1 },
  ];

  const folders = app.vault.getAllFolders(true).sort((a, b) => a.path.localeCompare(b.path));
  for (const folder of folders) {
    const p = folder.path.replace(/\\/g, "/").replace(/^\/+/, "");
    if (!p || p === "/") continue;
    if (SKIP_PREFIXES.some((skip) => p === skip || p.startsWith(`${skip}/`))) continue;
    nodes.push({
      path: p,
      name: folder.name,
      depth: p.split("/").length + 1,
    });
  }
  return nodes;
}

export function cascadeTargets(nodes: FolderNode[], path: string): string[] {
  if (path === ALL_VAULT_PATH) {
    return nodes.map((n) => n.path);
  }
  if (!path) {
    return [""];
  }
  const prefix = `${path}/`;
  return nodes.filter((n) => n.path === path || n.path.startsWith(prefix)).map((n) => n.path);
}

function folderToIncludeGlob(path: string): string | null {
  if (path === ALL_VAULT_PATH) return "**/*.md";
  return path ? `${path}/**` : "*.md";
}

function globToFolderPath(pattern: string): string | null {
  const p = pattern.trim().replace(/\\/g, "/");
  if (p === "**/*.md" || p === "**/**") return ALL_VAULT_PATH;
  if (p === "*.md") return "";
  if (p.endsWith("/**")) return p.slice(0, -3);
  if (p.endsWith("/**/*.md")) return p.slice(0, -"/**/*.md".length);
  return null;
}

function isFullVaultGlob(patterns: string[]): boolean {
  return patterns.some((p) => p === "**/*.md" || p === "**/**");
}

export function selectionsFromScope(
  nodes: FolderNode[],
  include: string[],
  writeInclude: string[] | undefined,
  writeAccess: boolean
): Map<string, FolderAccess> {
  const map = new Map<string, FolderAccess>();
  for (const n of nodes) {
    map.set(n.path, { read: false, write: false });
  }

  if (isFullVaultGlob(include)) {
    for (const n of nodes) {
      map.set(n.path, { read: true, write: false });
    }
  } else {
    for (const pattern of include) {
      const folder = globToFolderPath(pattern);
      if (folder === null || !map.has(folder)) continue;
      for (const target of cascadeTargets(nodes, folder)) {
        const cur = map.get(target)!;
        map.set(target, { read: true, write: cur.write });
      }
    }
  }

  const writePatterns = writeInclude?.length ? writeInclude : writeAccess ? include : [];
  if (isFullVaultGlob(writePatterns)) {
    for (const n of nodes) {
      map.set(n.path, { read: true, write: true });
    }
  } else {
    for (const pattern of writePatterns) {
      const folder = globToFolderPath(pattern);
      if (folder === null || !map.has(folder)) continue;
      for (const target of cascadeTargets(nodes, folder)) {
        map.set(target, { read: true, write: true });
      }
    }
  }

  syncMasterRow(nodes, map);
  return map;
}

/** Keep «Весь vault» in sync with all other rows. */
export function syncMasterRow(nodes: FolderNode[], map: Map<string, FolderAccess>): void {
  const rest = nodes.filter((n) => n.path !== ALL_VAULT_PATH);
  map.set(ALL_VAULT_PATH, {
    read: rest.every((n) => map.get(n.path)?.read),
    write: rest.every((n) => map.get(n.path)?.write),
  });
}

export function scopeFromSelections(
  nodes: FolderNode[],
  selections: Map<string, FolderAccess>
): { include: string[]; writeInclude: string[]; writeAccess: boolean } {
  const rest = nodes.filter((n) => n.path !== ALL_VAULT_PATH);
  const allRead = rest.every((n) => selections.get(n.path)?.read);
  const allWrite = rest.every((n) => selections.get(n.path)?.write);

  if (allRead) {
    return {
      include: ["**/*.md"],
      writeInclude: allWrite ? ["**/*.md"] : compactWriteGlobs(nodes, selections),
      writeAccess: allWrite || compactWriteGlobs(nodes, selections).length > 0,
    };
  }

  const include: string[] = [];
  const writeInclude: string[] = [];

  for (const node of rest) {
    const access = selections.get(node.path);
    if (!access?.read) continue;
    if (!isCoveredByAncestor(node.path, rest, selections, "read")) {
      const glob = folderToIncludeGlob(node.path);
      if (glob) include.push(glob);
    }
    if (access.write && !isCoveredByAncestor(node.path, rest, selections, "write")) {
      const glob = folderToIncludeGlob(node.path);
      if (glob && glob !== "**/*.md") writeInclude.push(glob);
      else if (glob === "*.md") writeInclude.push("*.md");
    }
  }

  return {
    include,
    writeInclude,
    writeAccess: writeInclude.length > 0,
  };
}

function isCoveredByAncestor(
  path: string,
  nodes: FolderNode[],
  selections: Map<string, FolderAccess>,
  field: "read" | "write"
): boolean {
  if (!path) return false;
  const parts = path.split("/");
  for (let i = 1; i < parts.length; i++) {
    const ancestor = parts.slice(0, i).join("/");
    if (nodes.some((n) => n.path === ancestor) && selections.get(ancestor)?.[field]) {
      return true;
    }
  }
  return false;
}

function compactWriteGlobs(nodes: FolderNode[], selections: Map<string, FolderAccess>): string[] {
  const rest = nodes.filter((n) => n.path !== ALL_VAULT_PATH);
  const out: string[] = [];
  for (const node of rest) {
    const access = selections.get(node.path);
    if (!access?.write) continue;
    if (!isCoveredByAncestor(node.path, rest, selections, "write")) {
      const glob = folderToIncludeGlob(node.path);
      if (glob && glob !== "**/*.md") out.push(glob);
    }
  }
  return out;
}

export function countWriteFolders(selections: Map<string, FolderAccess>): number {
  let n = 0;
  for (const [path, access] of selections) {
    if (path !== ALL_VAULT_PATH && access.write) n++;
  }
  return n;
}
