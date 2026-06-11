import {
  ALL_VAULT_PATH,
  cascadeTargets,
  scopeFromSelections,
  selectionsFromScope,
  syncMasterRow,
  type FolderAccess,
  type FolderNode,
} from "../folderScope";

export class FolderScopePicker {
  private selections = new Map<string, FolderAccess>();
  private onChangeHandler?: () => void;
  private bodyEl: HTMLDivElement | null = null;
  private checkboxByPath = new Map<string, { read: HTMLInputElement; write: HTMLInputElement }>();

  constructor(
    private container: HTMLElement,
    private nodes: FolderNode[],
    include: string[],
    writeInclude: string[] | undefined,
    writeAccess: boolean
  ) {
    this.selections = selectionsFromScope(nodes, include, writeInclude, writeAccess);
    this.render();
  }

  onChange(handler: () => void): void {
    this.onChangeHandler = handler;
  }

  getScopeFields(): { include: string[]; writeInclude: string[]; writeAccess: boolean } {
    return scopeFromSelections(this.nodes, this.selections);
  }

  getWriteFolderCount(): number {
    let n = 0;
    for (const [path, access] of this.selections) {
      if (path !== ALL_VAULT_PATH && access.write) n++;
    }
    return n;
  }

  private getAccess(path: string): FolderAccess {
    return this.selections.get(path) ?? { read: false, write: false };
  }

  private setCascade(path: string, field: "read" | "write", value: boolean): void {
    const targets = cascadeTargets(this.nodes, path);

    for (const target of targets) {
      const cur = this.getAccess(target);
      if (field === "read") {
        this.selections.set(target, {
          read: value,
          write: value ? cur.write : false,
        });
      } else {
        this.selections.set(target, {
          read: value ? true : cur.read,
          write: value,
        });
      }
    }

    syncMasterRow(this.nodes, this.selections);
    this.syncCheckboxes();
    this.onChangeHandler?.();
  }

  private syncCheckboxes(): void {
    for (const node of this.nodes) {
      const refs = this.checkboxByPath.get(node.path);
      if (!refs) continue;
      const access = this.getAccess(node.path);
      refs.read.checked = access.read;
      refs.write.checked = access.write;
      refs.write.disabled = !access.read;
    }
  }

  private render(): void {
    this.container.empty();
    this.checkboxByPath.clear();

    this.container.createEl("p", {
      cls: "ocm-muted",
      text: "Галочка на папке включает все подпапки. «Весь vault» — все сразу.",
    });

    const header = this.container.createDiv({ cls: "ocm-folder-picker-header" });
    header.createSpan({ text: "Папка" });
    header.createSpan({ text: "Читать", cls: "ocm-folder-picker-col" });
    header.createSpan({ text: "Писать", cls: "ocm-folder-picker-col" });

    this.bodyEl = this.container.createDiv({ cls: "ocm-folder-picker-body" });

    for (const node of this.nodes) {
      const access = this.getAccess(node.path);
      const row = this.bodyEl.createDiv({ cls: "ocm-folder-picker-row" });
      if (node.path === ALL_VAULT_PATH) {
        row.addClass("ocm-folder-picker-master");
      }
      row.style.paddingLeft = `${8 + node.depth * 18}px`;

      const label = row.createDiv({ cls: "ocm-folder-picker-label" });
      label.createSpan({ text: node.name });
      if (node.path && node.path !== ALL_VAULT_PATH) {
        label.createEl("span", { cls: "ocm-muted", text: ` ${node.path}` });
      }

      const readCb = row.createEl("input", { type: "checkbox" });
      readCb.className = "ocm-folder-picker-col";
      readCb.checked = access.read;

      const writeCb = row.createEl("input", { type: "checkbox" });
      writeCb.className = "ocm-folder-picker-col";
      writeCb.checked = access.write;
      writeCb.disabled = !access.read;

      readCb.onchange = () => {
        this.setCascade(node.path, "read", readCb.checked);
      };
      writeCb.onchange = () => {
        this.setCascade(node.path, "write", writeCb.checked);
      };

      this.checkboxByPath.set(node.path, { read: readCb, write: writeCb });
    }
  }
}
