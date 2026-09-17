// Harnais Node partagé : charge les vrais composants avec des dépendances simulées.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { runInThisContext } from "node:vm";
import ts from "typescript";

export type Element = { type: string; props: Record<string, any> };
export function elements(v: any): Element[] {
  if (Array.isArray(v)) return v.flatMap(elements);
  return v && typeof v === "object" ? [v, ...elements(v.props.children)] : [];
}
export function creerChargeur(baseDir: string) {
  return function charger(path: string, deps: Record<string, unknown>): any {
    const source = ts.transpileModule(readFileSync(join(baseDir, path), "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
    }).outputText;
    const exports = {};
    runInThisContext(`(function(require, exports) { ${source}\n})`)((name: string) => {
      assert.ok(name in deps, `Import inattendu : ${name}`);
      return deps[name];
    }, exports);
    return exports;
  };
}
// Cycle de hooks pour exercer les vrais composants, effets, focus et remontages.
export function hooks() {
  let index = 0;
  const slots: any[] = [];
  let effects: (() => void)[] = [];
  let focus: () => (() => void) | void;
  let cleanup: (() => void) | void;
  const changed = (a: any[], b: any[]) => !a || a.length !== b.length || b.some((v, i) => !Object.is(v, a[i]));
  return {
    react: {
      useState(initial: any) {
        const i = index++;
        if (!(i in slots)) slots[i] = typeof initial === "function" ? initial() : initial;
        return [slots[i], (v: any) => { slots[i] = typeof v === "function" ? v(slots[i]) : v; }];
      },
      useRef(current: any) { const i = index++; return slots[i] ??= { current }; },
      useCallback(callback: any, deps: any[]) {
        const i = index++;
        if (changed(slots[i]?.deps, deps)) slots[i] = { deps, callback };
        return slots[i].callback;
      },
      useEffect(callback: () => void, deps: any[]) {
        const i = index++;
        if (changed(slots[i], deps)) { slots[i] = deps; effects.push(callback); }
      },
    },
    useFocusEffect(callback: typeof focus) { focus = callback; },
    async focus() { cleanup = focus(); await Promise.resolve(); },
    blur() { cleanup?.(); },
    render(component: () => unknown) { index = 0; return elements(component()); },
    flush() { const pending = effects; effects = []; pending.forEach(f => f()); },
  };
}
