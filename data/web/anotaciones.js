/* Notas privadas en este navegador. No envía anotaciones a un servidor. */
(() => {
  "use strict";
  if (document.getElementById("ia-notas")) return;
  const KEY = "Donzhumber.AI.anotaciones.v1";
  const SCHEMA = "ia-anotaciones-v1";
  const DOCS = {
    principal: { title: "Artículo principal", page: "Principal/principal.html" },
    anexo: { title: "Anexo A", page: "Anexo_a/anexo_a.html" },
    dashboard: { title: "Dashboard", page: "Dashboard/dashboard.html" }
  };
  const path = location.pathname.toLowerCase();
  const doc = path.includes("/anexo_a/") ? "anexo" : path.includes("/dashboard/") ? "dashboard" : "principal";
  const base = new URL("../", location.href);
  const DRAFT_KEY = `${KEY}.borrador.${doc}`;
  let notes = [], draft = null, selected = null, deleted = null, storageFailed = false;
  const makeId = () => globalThis.crypto?.randomUUID?.() || `nota-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const now = () => new Date().toISOString();
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  };
  const button = (text, action, primary = false) => {
    const node = el("button", `notas-boton${primary ? " notas-primario" : ""}`, text);
    node.type = "button";
    node.addEventListener("click", action);
    return node;
  };
  function validNote(note) {
    if (!note || typeof note !== "object" || !Object.prototype.hasOwnProperty.call(DOCS, note.document)) throw new Error("Documento de anotación no reconocido.");
    for (const [name, limit] of [["id", 150], ["anchor", 300], ["section", 600], ["quote", 8000], ["comment", 20000]]) {
      if (typeof note[name] !== "string" || note[name].length > limit) throw new Error("El archivo contiene una anotación no válida o demasiado larga.");
    }
    if (!note.id || !note.comment.trim() || !Number.isFinite(Date.parse(note.createdAt)) || !Number.isFinite(Date.parse(note.updatedAt))) {
      throw new Error("Faltan el comentario, el identificador o las fechas de una anotación.");
    }
    return { id: note.id, document: note.document, anchor: note.anchor, section: note.section,
      quote: note.quote, comment: note.comment, createdAt: note.createdAt, updatedAt: note.updatedAt };
  }
  function load() {
    if (storageFailed) return notes;
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return [];
      const data = JSON.parse(raw);
      if (data.schema !== SCHEMA || !Array.isArray(data.notes) || data.notes.length > 3000) throw new Error("Formato de almacenamiento no reconocido.");
      return data.notes.map(validNote);
    } catch (error) {
      storageFailed = true;
      return notes;
    }
  }
  function payload() { return { schema: SCHEMA, project: "Donzhumber/AI", exportedAt: now(), notes }; }
  function persist() {
    try { localStorage.setItem(KEY, JSON.stringify(payload())); storageFailed = false; return true; }
    catch (error) { storageFailed = true; return false; }
  }
  function noteUrl(note) {
    const url = new URL(DOCS[note.document].page, base);
    if (note.anchor) url.hash = note.anchor;
    return url.href;
  }
  notes = load();
  const root = el("div"); root.id = "ia-notas";
  const launcher = el("button", "notas-lanzador", "Anotaciones");
  launcher.type = "button"; launcher.setAttribute("aria-controls", "ia-notas-panel"); launcher.setAttribute("aria-expanded", "false");
  const selectionButton = el("button", "notas-seleccion", "Anotar selección"); selectionButton.type = "button"; selectionButton.hidden = true;
  const panel = el("aside", "notas-panel"); panel.id = "ia-notas-panel"; panel.hidden = true;
  panel.setAttribute("role", "dialog"); panel.setAttribute("aria-labelledby", "ia-notas-titulo");
  const head = el("div", "notas-cabecera");
  const title = el("h2", "", "Mis anotaciones"); title.id = "ia-notas-titulo";
  const close = el("button", "notas-cerrar", "×"); close.type = "button"; close.setAttribute("aria-label", "Cerrar anotaciones");
  head.append(title, close);
  const body = el("div", "notas-cuerpo");
  const help = el("p", "notas-ayuda", "Se guardan solo en este navegador. Exporta tus notas para llevarlas a otro dispositivo. No se sincronizan automáticamente.");
  const status = el("p", "notas-estado"); status.setAttribute("role", "status"); status.setAttribute("aria-live", "polite");
  const undo = button("Deshacer eliminación", () => {
    if (!deleted) return;
    notes = load().filter(note => note.id !== deleted.id); notes.push(deleted); deleted = null;
    persist(); undo.hidden = true; render(); message("Anotación recuperada.");
  }); undo.hidden = true;
  const listView = el("div");
  const controls = el("div", "notas-fila");
  const newButton = button("Nueva nota", () => start());
  const filter = el("select", "notas-filtro"); filter.setAttribute("aria-label", "Mostrar anotaciones");
  for (const [value, text] of [["current", "Este documento"], ["all", "Todos los documentos"]]) {
    const option = el("option", "", text); option.value = value; filter.append(option);
  }
  const list = el("div", "notas-lista"); controls.append(newButton, filter); listView.append(controls, list);
  const editor = el("div"); editor.hidden = true;
  const context = el("p", "notas-contexto");
  const quote = el("blockquote");
  const label = el("label", "", "Comentario o cambio propuesto"); label.htmlFor = "ia-notas-comentario";
  const input = el("textarea"); input.id = "ia-notas-comentario"; input.maxLength = 20000; input.placeholder = "Escribe lo que quieres revisar o incorporar después…";
  const editActions = el("div", "notas-fila");
  editActions.append(button("Guardar nota", save, true), button("Cancelar", () => {
    draft = null; clearDraft(); editor.hidden = true; listView.hidden = false; message(""); render();
  }));
  editor.append(context, quote, label, input, editActions);
  const exports = el("div", "notas-exportar");
  exports.append(el("p", "notas-ayuda", "Exportar incluye las notas de los tres documentos. En casa, usa Importar notas con el archivo JSON."));
  const exportActions = el("div", "notas-fila");
  const importer = el("input"); importer.type = "file"; importer.accept = ".json,application/json"; importer.hidden = true;
  exportActions.append(button("Exportar JSON", () => exportNotes("json")), button("Descargar texto", () => exportNotes("md")), button("Importar notas", () => importer.click()));
  if (navigator.share && navigator.canShare) exportActions.append(button("Compartir", share));
  exports.append(exportActions, importer);
  body.append(help, status, undo, listView, editor, exports); panel.append(head, body); root.append(selectionButton, launcher, panel); document.body.append(root);

  function placeInViewport() {
    const viewport = window.visualViewport;
    if (!viewport) return;
    root.style.setProperty("--notas-vv-right", `${Math.max(0, innerWidth - viewport.width - viewport.offsetLeft)}px`);
    root.style.setProperty("--notas-vv-bottom", `${Math.max(0, innerHeight - viewport.height - viewport.offsetTop)}px`);
    root.style.setProperty("--notas-vv-width", `${viewport.width}px`);
    root.style.setProperty("--notas-vv-height", `${viewport.height}px`);
  }
  window.addEventListener("resize", placeInViewport, { passive: true });
  window.addEventListener("load", placeInViewport, { once: true });
  window.visualViewport?.addEventListener("resize", placeInViewport, { passive: true });
  window.visualViewport?.addEventListener("scroll", placeInViewport, { passive: true });
  placeInViewport();
  function message(text, error = false) {
    status.textContent = text; status.dataset.error = String(error);
    if (storageFailed && !error) {
      status.textContent += " No se pudo guardar en este navegador. Exporta el archivo antes de cerrar.";
      status.dataset.error = "true";
    }
  }
  function show() {
    notes = load(); panel.hidden = false; launcher.setAttribute("aria-expanded", "true"); selectionButton.hidden = true; render(); close.focus();
    if (storageFailed) message("Este navegador no pudo guardar las notas. Expórtalas antes de cerrar.", true);
  }
  function hide() { panel.hidden = true; launcher.setAttribute("aria-expanded", "false"); launcher.focus(); }
  launcher.addEventListener("click", () => panel.hidden ? show() : hide());
  close.addEventListener("click", hide);
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !panel.hidden) hide(); });
  filter.addEventListener("change", render);
  function sectionContext(node) {
    let section = node?.closest?.("section[id]");
    let heading = section?.querySelector("h1,h2,h3,h4,h5,h6");
    if (!section) {
      const visible = [...document.querySelectorAll("main h1,main h2,main h3,main h4")].filter(h => h.getClientRects().length && h.getBoundingClientRect().top < 180);
      heading = visible.at(-1);
      section = heading?.closest("section[id]");
    }
    return { anchor: section?.id || heading?.id || "", section: (heading?.textContent || "Nota general").trim().slice(0, 600) };
  }
  function captureSelection() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) { selectionButton.hidden = true; return; }
    const node = selection.anchorNode?.nodeType === Node.ELEMENT_NODE ? selection.anchorNode : selection.anchorNode?.parentElement;
    if (!node || root.contains(node)) return;
    const text = selection.toString().trim();
    if (!text) return;
    selected = { ...sectionContext(node), quote: text.slice(0, 8000) };
    selectionButton.hidden = !panel.hidden;
  }
  document.addEventListener("selectionchange", captureSelection);
  selectionButton.addEventListener("click", () => { show(); start(selected); });
  function clearDraft() { try { localStorage.removeItem(DRAFT_KEY); } catch (error) { /* Export remains available. */ } }
  function readDraft() {
    try { const value = JSON.parse(localStorage.getItem(DRAFT_KEY) || "null"); return value && DOCS[value.document] && typeof value.comment === "string" ? value : null; }
    catch (error) { return null; }
  }
  function start(selection = null, note = null) {
    if (draft && !editor.hidden && input.value.trim()) { message("Guarda o cancela el borrador abierto antes de crear otra nota."); input.focus(); return; }
    const recovered = !note && readDraft();
    const stamp = now();
    draft = note ? { ...note } : recovered || { id: makeId(), document: doc, ...sectionContext(), quote: "", comment: "", createdAt: stamp, updatedAt: stamp, ...(selection || {}) };
    context.textContent = `${DOCS[draft.document].title} · ${draft.section}`;
    quote.textContent = draft.quote; quote.hidden = !draft.quote;
    input.value = draft.comment; listView.hidden = true; editor.hidden = false;
    message(recovered ? "Se recuperó tu borrador. Puedes continuarlo y guardar la nota." : ""); input.focus();
  }
  input.addEventListener("input", () => {
    if (!draft) return;
    draft.comment = input.value;
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify(draft)); message("Borrador conservado en este navegador. Pulsa Guardar nota para añadirlo a la lista."); }
    catch (error) { storageFailed = true; message("No se pudo conservar el borrador. Guarda la nota y expórtala antes de cerrar.", true); }
  });
  function save() {
    if (!draft) return true;
    const comment = input.value.trim();
    if (!comment) { message("Escribe un comentario antes de guardar.", true); input.focus(); return false; }
    const note = validNote({ ...draft, comment, updatedAt: now() });
    notes = load().filter(item => item.id !== note.id); notes.push(note); persist(); clearDraft(); draft = null;
    editor.hidden = true; listView.hidden = false; render(); message("Nota guardada en este navegador."); return true;
  }
  function render() {
    launcher.textContent = notes.length ? `Anotaciones · ${notes.length}` : "Anotaciones";
    list.replaceChildren();
    newButton.textContent = readDraft()?.comment?.trim() ? "Continuar borrador" : "Nueva nota";
    const visible = notes.filter(note => filter.value === "all" || note.document === doc).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
    if (!visible.length) list.append(el("p", "notas-vacio", "Todavía no hay notas aquí. Crea una nota general o selecciona un texto y pulsa Anotar selección."));
    for (const note of visible) {
      const card = el("article", "notas-tarjeta"); card.dataset.noteId = note.id;
      const link = el("a", "", `${DOCS[note.document].title} · ${note.section}`); link.href = noteUrl(note);
      if (note.document === doc) link.addEventListener("click", hide);
      card.append(link);
      if (note.quote) card.append(el("blockquote", "", note.quote));
      card.append(el("p", "notas-comentario", note.comment), el("span", "notas-fecha", new Date(note.updatedAt).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })));
      const actions = el("div", "notas-acciones");
      const edit = button("Editar", () => start(null, note)); edit.className = "notas-texto-boton";
      const remove = button("Eliminar", () => {
        deleted = note; notes = load().filter(item => item.id !== note.id); persist(); undo.hidden = false; render(); message("Anotación eliminada. Puedes deshacerlo.");
      }); remove.className = "notas-texto-boton"; actions.append(edit, remove); card.append(actions); list.append(card);
    }
  }
  function exportData() {
    if (draft && input.value.trim() && !save()) return null;
    notes = load();
    if (!notes.length) { message("Guarda al menos una anotación para exportarla.", true); return null; }
    return JSON.stringify(payload(), null, 2);
  }
  function markdown() {
    const lines = ["# Anotaciones del proyecto IA", "", `Exportadas el ${new Date().toLocaleString("es-CO")}`, ""];
    for (const note of [...notes].sort((a, b) => a.document.localeCompare(b.document) || a.createdAt.localeCompare(b.createdAt))) {
      lines.push(`## ${DOCS[note.document].title} · ${note.section}`, "", `Referencia: ${noteUrl(note)}`, "");
      if (note.quote) lines.push(...note.quote.split("\n").map(line => `> ${line}`), "");
      lines.push("Comentario o cambio propuesto", "", note.comment, "", `Actualizada: ${note.updatedAt}`, "");
    }
    return lines.join("\n");
  }
  function download(content, extension) {
    const blob = new Blob([content], { type: extension === "json" ? "application/json;charset=utf-8" : "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob); const link = el("a"); link.href = url;
    link.download = `anotaciones_IA_${now().slice(0, 10)}.${extension}`; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }
  function exportNotes(format) {
    const data = exportData(); if (!data) return;
    download(format === "json" ? data : markdown(), format); message(format === "json" ? "Archivo preparado. Guárdalo en Archivos o iCloud para importarlo en casa." : "Texto preparado para revisar o incorporar las observaciones al documento.");
  }
  async function share() {
    const data = exportData(); if (!data) return;
    const file = new File([data], `anotaciones_IA_${now().slice(0, 10)}.json`, { type: "application/json" });
    if (!navigator.canShare({ files: [file] })) { exportNotes("json"); return; }
    try { await navigator.share({ files: [file], title: "Mis anotaciones del proyecto IA" }); message("Archivo compartido."); }
    catch (error) { if (error.name !== "AbortError") message("No fue posible compartir. Usa Exportar JSON.", true); }
  }
  importer.addEventListener("change", async () => {
    const file = importer.files?.[0]; if (!file) return;
    try {
      if (file.size > 8 * 1024 * 1024) throw new Error("El archivo de notas supera los 8 MB.");
      const data = JSON.parse(await file.text());
      if (data.schema !== SCHEMA || data.project !== "Donzhumber/AI" || !Array.isArray(data.notes) || data.notes.length > 3000) throw new Error("El archivo no es una exportación de anotaciones de este proyecto.");
      const incoming = data.notes.map(validNote); const merged = new Map(load().map(note => [note.id, note])); let changed = 0;
      for (const note of incoming) {
        const existing = merged.get(note.id);
        if (!existing || Date.parse(note.updatedAt) > Date.parse(existing.updatedAt)) { merged.set(note.id, note); changed++; }
      }
      if (merged.size > 3000) throw new Error("La colección supera las 3.000 anotaciones.");
      notes = [...merged.values()]; persist(); render(); message(`Se incorporaron ${changed} anotaciones nuevas o actualizadas. Se conservaron las versiones más recientes.`);
    } catch (error) { message(`No se importó el archivo. ${error.message}`, true); }
    finally { importer.value = ""; }
  });
  window.addEventListener("storage", event => { if (event.key === KEY) { notes = load(); render(); } });
  render();
  if (new URL(location.href).searchParams.get("notas") === "1") { show(); filter.value = "all"; render(); }
})();
