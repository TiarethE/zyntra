/* Zyntra: interfaz web. Sin librerías externas: funciona sin internet. */
"use strict";

const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];
const vista = $("#vista");

const estado = {
  catalogo: null,
  envios: [],
  feed: [],
  filtro: "Todos",
  formulario: null,
  guiaAbierta: null,
  temporizador: null,
};

// ---------- Utilidades ----------
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clase = (estadoEnvio) => "e-" + estadoEnvio.normalize("NFD").replace(/[̀-ͯ]/g, "")
  .toLowerCase().replace(/\s+/g, "-");
const insignia = (e) => `<span class="insignia ${clase(e)}">${esc(e)}</span>`;
const lempiras = (m) => "L " + Number(m).toLocaleString("es-HN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const patron = (n) => `<span class="patron" title="Patrón de diseño">${esc(n)}</span>`;
const fecha = (iso) => new Date(iso).toLocaleString("es-HN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const hora = (iso) => new Date(iso).toLocaleTimeString("es-HN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const ETAPAS = {
  nacional: ["Registrado", "En tránsito", "En reparto", "Entregado"],
  express: ["Registrado", "En tránsito", "En reparto", "Entregado"],
  internacional: ["Registrado", "En tránsito", "Retenido en aduana", "En reparto", "Entregado"],
};
const CLASE_ESTADO = {
  "Registrado": "Registrado", "En tránsito": "EnTransito", "Retenido en aduana": "RetenidoEnAduana",
  "En reparto": "EnReparto", "Entregado": "Entregado", "Cancelado": "Cancelado",
};
const VERBO = {
  "En tránsito": "Enviar a tránsito", "Retenido en aduana": "Retener en aduana",
  "En reparto": "Sacar a reparto", "Entregado": "Marcar entregado", "Cancelado": "Cancelar envío",
};

async function api(ruta, opciones = {}) {
  const resp = await fetch(ruta, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
    body: opciones.body ? JSON.stringify(opciones.body) : undefined,
  });
  const datos = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(datos.error || datos.detail?.[0]?.msg || `Error ${resp.status}`);
  return datos;
}

function aviso(titulo, texto = "", tipo = "") {
  const el = document.createElement("div");
  el.className = "aviso " + tipo;
  el.innerHTML = `<strong>${esc(titulo)}</strong>${esc(texto)}`;
  $("#avisos").append(el);
  setTimeout(() => el.remove(), 4500);
}

// ---------- Enrutador ----------
const vistas = { panel: verPanel, nuevo: verNuevo, rastrear: verRastrear, envio: verEnvio, sistema: verSistema };

function ruta() {
  const [, nombre = "panel", param] = location.hash.split("/");
  clearInterval(estado.temporizador);
  estado.guiaAbierta = null;
  $$("nav a").forEach((a) => a.classList.toggle("activa",
    a.dataset.vista === nombre || (nombre === "envio" && a.dataset.vista === "panel")));
  (vistas[nombre] || verPanel)(param ? decodeURIComponent(param) : undefined);
  vista.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", ruta);

// ---------- Panel ----------
async function verPanel() {
  vista.innerHTML = `
    <div class="encabezado">
      <div><h1>Panel de envíos</h1><p>Lo que está pasando ahora en la red de Zyntra.</p></div>
      <a class="boton" href="#/nuevo">＋ Nuevo envío</a>
    </div>
    <div class="rejilla kpis" id="kpis"></div>
    <div class="rejilla dos-columnas">
      <section class="tarjeta">
        <div class="cab"><h2>Envíos</h2><div class="filtros" id="filtros"></div></div>
        <div class="cuerpo" style="padding-top:8px"><table class="tabla">
          <thead><tr><th>Guía</th><th>Cliente</th><th class="ocultar-movil">Ruta</th><th>Estado</th><th class="ocultar-movil" style="text-align:right">Total</th></tr></thead>
          <tbody id="lista"></tbody></table></div>
      </section>
      <section class="tarjeta">
        <div class="cab"><h2>En vivo <span class="punto-vivo"></span></h2>${patron("Observer")}</div>
        <div class="cuerpo"><ul class="feed" id="feed"></ul>
        <div class="explica">Cada cambio de estado se publica en el <b>bus de eventos</b>. El suscriptor <code>TransmisorEnVivo</code> lo reenvía a esta pantalla por WebSocket, sin recargar.</div></div>
      </section>
    </div>`;
  pintarFeed();
  await cargarEnvios();
  estado.temporizador = setInterval(cargarEnvios, 5000);
}

async function cargarEnvios() {
  estado.envios = await api("/api/envios");
  if (!$("#lista")) return;
  const e = estado.envios;
  const activos = e.filter((x) => !["Entregado", "Cancelado"].includes(x.estado));
  const ingresos = e.filter((x) => x.estado !== "Cancelado").reduce((s, x) => s + Number(x.total), 0);
  $("#kpis").innerHTML = [
    ["Envíos activos", activos.length, `${e.length} en total`],
    ["En aduana", e.filter((x) => x.estado === "Retenido en aduana").length, "solo internacionales"],
    ["Entregados", e.filter((x) => x.estado === "Entregado").length, "con rastreo completo"],
    ["Ingresos", lempiras(ingresos), "lempiras (HNL)"],
  ].map(([etq, valor, sub]) => `<div class="tarjeta kpi"><div class="etq">${etq}</div>
    <div class="valor num">${esc(valor)}</div><div class="sub">${sub}</div></div>`).join("");

  const opciones = ["Todos", "Registrado", "En tránsito", "Retenido en aduana", "En reparto", "Entregado"];
  $("#filtros").innerHTML = opciones.map((o) =>
    `<button class="filtro ${o === estado.filtro ? "activo" : ""}" data-f="${o}">${o}</button>`).join("");
  $$("#filtros .filtro").forEach((b) => b.onclick = () => { estado.filtro = b.dataset.f; cargarEnvios(); });

  const visibles = e.filter((x) => estado.filtro === "Todos" || x.estado === estado.filtro);
  $("#lista").innerHTML = visibles.length ? visibles.map((x) => `
    <tr data-guia="${esc(x.guia)}">
      <td><div class="guia">${esc(x.guia)}</div><div class="tipo-chip ${x.tipo}">${esc(x.tipo)}</div></td>
      <td>${esc(x.cliente_nombre)}<div class="tenue">${fecha(x.ultimo_movimiento)}</div></td>
      <td class="ocultar-movil">${esc(x.origen)} → ${esc(x.tipo === "internacional" ? x.pais_destino : x.destino)}</td>
      <td>${insignia(x.estado)}${x.simulando ? ' <span class="tenue">· en ruta…</span>' : ""}</td>
      <td class="monto ocultar-movil" style="text-align:right">${lempiras(x.total)}</td>
    </tr>`).join("") : `<tr><td colspan="5" class="vacio">No hay envíos en este estado.</td></tr>`;
  $$("#lista tr[data-guia]").forEach((tr) => tr.onclick = () => location.hash = "#/envio/" + tr.dataset.guia);
}

function pintarFeed() {
  const feed = $("#feed");
  if (!feed) return;
  feed.innerHTML = estado.feed.length ? estado.feed.map((ev) => `
    <li><span class="guia" data-guia="${esc(ev.guia)}">${esc(ev.guia)}</span> pasó a ${insignia(ev.nuevo)}
      <div>${esc(ev.descripcion)}</div><div class="cuando">${hora(ev.hora)}</div></li>`).join("")
    : `<li class="vacio" style="animation:none">Aún no hay movimientos en esta sesión.<br>Abra un envío y presione «Simular recorrido».</li>`;
  $$("#feed .guia").forEach((g) => g.onclick = () => location.hash = "#/envio/" + g.dataset.guia);
}

// ---------- Nuevo envío ----------
const paqueteVacio = () => ({ contenido: "", peso_kg: "", alto_cm: "", ancho_cm: "", largo_cm: "", valor_declarado: "", fragil: false });

function verNuevo() {
  const cat = estado.catalogo;
  estado.formulario ??= { tipo: "nacional", sucursal_origen: 1, direccion_destino: "", pais_destino: "",
    asegurar: false, cliente: { nombre: "", email: "", telefono: "" }, paquetes: [paqueteVacio()] };
  const f = estado.formulario;
  const tarifa = (id) => cat.tipos.find((t) => t.id === id);
  const textoTipo = {
    nacional: "Entrega en cualquier ciudad de Honduras.",
    express: "Entrega rápida dentro de Honduras. Hasta 30 kg.",
    internacional: "Al extranjero. Pasa por aduana y exige valor declarado.",
  };
  vista.innerHTML = `
    <div class="encabezado"><div><h1>Nuevo envío</h1><p>El costo se calcula mientras llena el formulario.</p></div></div>
    <div class="rejilla dos-columnas">
      <form class="tarjeta" id="form" novalidate>
        <div class="seccion-form"><h2><span class="paso">1</span>Tipo de envío ${patron("Factory Method")}</h2>
          <div class="tipos">${cat.tipos.map((t) => `
            <label class="tipo"><input type="radio" name="tipo" value="${t.id}" ${f.tipo === t.id ? "checked" : ""}>
              <strong style="text-transform:capitalize">${t.id}</strong><small>${textoTipo[t.id]}</small>
              <span class="tarifa">${lempiras(t.fija)} + ${lempiras(t.por_kg)}/kg</span></label>`).join("")}</div>
          <div class="explica">Cada tipo tiene su propio <b>creador</b> (<code>EnvioNacionalCreator</code>, <code>EnvioExpressCreator</code>, <code>EnvioInternacionalCreator</code>) que valida sus reglas antes de crear el envío.</div>
        </div>
        <div class="seccion-form"><h2><span class="paso">2</span>Origen y destino</h2>
          <div class="fila">
            <label class="campo">Sucursal de origen<select name="sucursal_origen">${cat.sucursales.map((s) =>
              `<option value="${s.id}" ${String(f.sucursal_origen) === String(s.id) ? "selected" : ""}>${esc(s.nombre)}</option>`).join("")}</select></label>
            <label class="campo" id="campo-pais" ${f.tipo === "internacional" ? "" : "hidden"}>País de destino
              <input type="text" name="pais_destino" value="${esc(f.pais_destino)}" placeholder="Estados Unidos" list="paises"></label>
          </div>
          <datalist id="paises"><option>Estados Unidos</option><option>México</option><option>Guatemala</option><option>El Salvador</option><option>Nicaragua</option><option>Costa Rica</option><option>España</option><option>Canadá</option></datalist>
          <label class="campo" style="margin-top:12px">Dirección de destino
            <input type="text" name="direccion_destino" value="${esc(f.direccion_destino)}" placeholder="Col. Kennedy, Tegucigalpa"></label>
        </div>
        <div class="seccion-form"><h2><span class="paso">3</span>Paquetes</h2>
          <div id="paquetes"></div>
          <button type="button" class="secundario chico" id="agregar">＋ Agregar paquete</button>
          <p class="nota">Se cobra el mayor entre el peso real y el volumétrico (alto × ancho × largo ÷ 5000).</p>
        </div>
        <div class="seccion-form"><h2><span class="paso">4</span>Extras ${patron("Decorator")}</h2>
          <label class="casilla"><input type="checkbox" name="asegurar" ${f.asegurar ? "checked" : ""}> Asegurar el envío por su valor declarado</label>
          <div class="explica">El costo base es una pieza; el <b>seguro</b> y el <b>manejo frágil</b> son capas (<code>SeguroDecorator</code>, <code>ManejoFragilDecorator</code>) que se agregan solo si hacen falta.</div>
        </div>
        <div class="seccion-form"><h2><span class="paso">5</span>Cliente</h2>
          <div class="fila">
            <label class="campo">Nombre completo<input type="text" name="c_nombre" value="${esc(f.cliente.nombre)}" placeholder="Ana López"></label>
            <label class="campo">Correo<input type="email" name="c_email" value="${esc(f.cliente.email)}" placeholder="ana@correo.hn"></label>
            <label class="campo">Teléfono<input type="text" name="c_telefono" value="${esc(f.cliente.telefono)}" placeholder="9999-0000"></label>
          </div>
        </div>
      </form>
      <aside class="tarjeta cotizacion">
        <div class="cab"><h2>Cotización</h2><span class="tenue" id="moneda">HNL</span></div>
        <div class="cuerpo">
          <div id="cotizacion"><div class="vacio">Agregue el peso y las medidas del paquete para ver el costo.</div></div>
          <div id="error-registro"></div>
          <button class="grande" id="registrar" type="button">Registrar envío</button>
          <p class="nota">Las tarifas vienen de <code>tarifas.json</code>. Cambiar un precio es editar ese archivo.</p>
        </div>
      </aside>
    </div>`;
  pintarPaquetes();
  const form = $("#form");
  form.addEventListener("input", leerFormulario);
  form.addEventListener("change", leerFormulario);
  $("#agregar").onclick = () => { f.paquetes.push(paqueteVacio()); pintarPaquetes(); cotizar(); };
  $("#registrar").onclick = registrar;
  cotizar();
}

function pintarPaquetes() {
  const f = estado.formulario;
  $("#paquetes").innerHTML = f.paquetes.map((p, i) => `
    <div class="paquete" data-i="${i}">
      <div class="cab-paq"><span>Paquete ${i + 1}</span>${f.paquetes.length > 1 ? `<button type="button" class="quitar" data-quitar="${i}" aria-label="Quitar paquete ${i + 1}">✕ Quitar</button>` : ""}</div>
      <div class="fila">
        <label class="campo">Contenido<input type="text" data-c="contenido" value="${esc(p.contenido)}" placeholder="Café de Marcala"></label>
        <label class="campo">Peso (kg)<input type="number" min="0" step="0.1" data-c="peso_kg" value="${esc(p.peso_kg)}" placeholder="2.5"></label>
        <label class="campo">Alto (cm)<input type="number" min="0" data-c="alto_cm" value="${esc(p.alto_cm)}" placeholder="20"></label>
        <label class="campo">Ancho (cm)<input type="number" min="0" data-c="ancho_cm" value="${esc(p.ancho_cm)}" placeholder="30"></label>
        <label class="campo">Largo (cm)<input type="number" min="0" data-c="largo_cm" value="${esc(p.largo_cm)}" placeholder="40"></label>
        <label class="campo">Valor (L)<input type="number" min="0" data-c="valor_declarado" value="${esc(p.valor_declarado)}" placeholder="0"></label>
      </div>
      <div class="pie-paq"><label class="casilla"><input type="checkbox" data-c="fragil" ${p.fragil ? "checked" : ""}> Frágil</label></div>
    </div>`).join("");
  $$("[data-quitar]").forEach((b) => b.onclick = () => {
    f.paquetes.splice(Number(b.dataset.quitar), 1); pintarPaquetes(); cotizar();
  });
}

let esperaCotizar;
function leerFormulario(ev) {
  const f = estado.formulario, form = $("#form");
  const v = (n) => form.elements[n]?.value ?? "";
  f.tipo = form.querySelector("input[name=tipo]:checked")?.value || "nacional";
  f.sucursal_origen = v("sucursal_origen");
  f.direccion_destino = v("direccion_destino");
  f.pais_destino = v("pais_destino");
  f.asegurar = form.elements.asegurar.checked;
  f.cliente = { nombre: v("c_nombre"), email: v("c_email"), telefono: v("c_telefono") };
  $$(".paquete").forEach((el) => {
    const p = f.paquetes[Number(el.dataset.i)];
    $$("[data-c]", el).forEach((inp) => p[inp.dataset.c] = inp.type === "checkbox" ? inp.checked : inp.value);
  });
  $("#campo-pais").hidden = f.tipo !== "internacional";
  if (ev && ev.target.name?.startsWith("c_")) return;  // los datos del cliente no cambian el costo
  clearTimeout(esperaCotizar);
  esperaCotizar = setTimeout(cotizar, 250);
}

const paqueteCompleto = (p) => ["peso_kg", "alto_cm", "ancho_cm", "largo_cm"].every((c) => Number(p[c]) > 0);
const cuerpoEnvio = () => {
  const f = estado.formulario;
  return { ...f, paquetes: f.paquetes.map((p) => ({ ...p, contenido: p.contenido || "Sin describir" })) };
};

async function cotizar() {
  const caja = $("#cotizacion");
  if (!caja) return;
  if (!estado.formulario.paquetes.some(paqueteCompleto)) {
    caja.innerHTML = `<div class="vacio">Agregue el peso y las medidas del paquete para ver el costo.</div>`;
    return;
  }
  try {
    const c = await api("/api/cotizar", { method: "POST", body: cuerpoEnvio() });
    caja.innerHTML = `
      <table class="desglose">${c.desglose.map((d) =>
        `<tr><td>${esc(d.concepto)}</td><td class="monto">${lempiras(d.monto)}</td></tr>`).join("")}</table>
      <div class="total"><span>Total</span><strong class="num">${lempiras(c.total)}</strong></div>
      <div class="nota" style="margin:-8px 0 12px">Peso facturable: ${esc(c.peso_facturable_kg)} kg</div>`;
  } catch (e) {
    caja.innerHTML = `<div class="error-form">${esc(e.message)}</div>`;
  }
}

async function registrar() {
  leerFormulario();
  const boton = $("#registrar");
  boton.disabled = true;
  $("#error-registro").innerHTML = "";
  try {
    const f = estado.formulario;
    const sinContenido = f.paquetes.findIndex((p) => !p.contenido.trim());
    if (sinContenido >= 0) throw new Error(`Paquete ${sinContenido + 1}: describa el contenido`);
    const envio = await api("/api/envios", { method: "POST", body: f });
    estado.formulario = null;
    aviso("Envío registrado", `Guía ${envio.guia} · ${lempiras(envio.costo.total)}`);
    location.hash = "#/envio/" + envio.guia;
  } catch (e) {
    $("#error-registro").innerHTML = `<div class="error-form">${esc(e.message)}</div>`;
  } finally {
    boton.disabled = false;
  }
}

// ---------- Rastrear (vista del cliente) ----------
function verRastrear(guia) {
  vista.innerHTML = `
    <div class="encabezado"><div><h1>Rastrear envío</h1><p>Escriba su número de guía. La página se actualiza sola cuando su paquete avanza.</p></div></div>
    <form class="buscador" id="buscar"><input type="search" name="guia" placeholder="ZYN-00000000" value="${esc(guia || "")}" aria-label="Número de guía" autocomplete="off"><button>Rastrear</button></form>
    <div class="sugerencias" id="sugerencias"></div>
    <div id="resultado" style="margin-top:22px"></div>`;
  const recientes = estado.envios.slice(0, 3).map((e) => e.guia);
  if (recientes.length) $("#sugerencias").innerHTML = "Pruebe con: " + recientes.map((g) => `<button type="button" data-g="${g}">${g}</button>`).join(" ");
  $$("#sugerencias button").forEach((b) => b.onclick = () => location.hash = "#/rastrear/" + b.dataset.g);
  $("#buscar").onsubmit = (ev) => {
    ev.preventDefault();
    const g = ev.target.guia.value.trim().toUpperCase();
    if (g) location.hash = "#/rastrear/" + g;
  };
  if (guia) pintarRastreo(guia);
}

async function pintarRastreo(guia, animar = false) {
  const caja = $("#resultado");
  try {
    const d = await api("/api/envios/" + encodeURIComponent(guia));
    estado.guiaAbierta = d.guia;
    caja.innerHTML = `
      <section class="tarjeta">${cabeceraEnvio(d)}${progreso(d)}</section>
      <div class="rejilla dos-columnas" style="margin-top:18px">
        <section class="tarjeta"><div class="cab"><h2>Historial</h2></div><div class="cuerpo">${lineaTiempo(d, animar)}</div></section>
        <section class="tarjeta"><div class="cab"><h2>Avisos que recibió</h2></div><div class="cuerpo">${mensajes(d)}</div></section>
      </div>`;
  } catch (e) {
    caja.innerHTML = `<div class="tarjeta"><div class="vacio">${esc(e.message)}</div></div>`;
  }
}

// ---------- Detalle del envío (vista del empleado) ----------
async function verEnvio(guia, animar = false) {
  let d;
  try { d = await api("/api/envios/" + encodeURIComponent(guia)); }
  catch (e) { vista.innerHTML = `<div class="tarjeta"><div class="vacio">${esc(e.message)}</div></div>`; return; }
  estado.guiaAbierta = d.guia;
  const destinos = d.siguientes;
  vista.innerHTML = `
    <div class="encabezado"><div><a href="#/panel">← Panel</a></div></div>
    <section class="tarjeta">${cabeceraEnvio(d)}${progreso(d)}</section>
    <div class="rejilla dos-columnas" style="margin-top:18px">
      <div class="rejilla">
        <section class="tarjeta">
          <div class="cab"><h2>Mover el envío</h2>${patron("State")}</div>
          <div class="cuerpo">
            ${destinos.length ? `<div class="acciones">${destinos.map((e) =>
              `<button class="${e === "Cancelado" ? "peligro" : ""}" data-destino="${esc(e)}">${esc(VERBO[e] || e)}</button>`).join("")}
              <button class="secundario" id="simular" ${d.simulando ? "disabled" : ""}>${d.simulando ? "Simulando recorrido…" : "▶ Simular recorrido"}</button></div>`
              : `<div class="vacio" style="padding:8px">El envío está «${esc(d.estado)}». Es un estado final: ya no se puede mover.</div>`}
            <div class="explica">Solo aparecen los cambios que el estado actual (<code>${esc(CLASE_ESTADO[d.estado])}</code>) permite. «Retener en aduana» solo existe para internacionales: la regla vive en la clase <code>EnTransito</code>.</div>
          </div>
        </section>
        <section class="tarjeta"><div class="cab"><h2>Historial de rastreo</h2></div><div class="cuerpo">${lineaTiempo(d, animar)}</div></section>
        <section class="tarjeta"><div class="cab"><h2>Paquetes</h2></div><div class="cuerpo" style="padding-top:8px">
          <table class="tabla"><thead><tr><th>Contenido</th><th class="ocultar-movil">Medidas</th><th>Peso</th><th>Facturable</th><th style="text-align:right">Valor</th></tr></thead><tbody>
          ${d.paquetes.map((p) => `<tr style="cursor:default"><td>${esc(p.contenido)}${p.fragil ? ' <span class="insignia e-retenido-en-aduana">Frágil</span>' : ""}</td>
            <td class="ocultar-movil tenue">${esc(p.medidas)}</td><td class="num">${esc(p.peso_kg)} kg</td><td class="num">${esc(p.peso_facturable_kg)} kg</td>
            <td class="monto" style="text-align:right">${lempiras(p.valor_declarado)}</td></tr>`).join("")}
          </tbody></table></div></section>
      </div>
      <div class="rejilla">
        <section class="tarjeta"><div class="cab"><h2>Costo</h2>${patron("Decorator")}</div><div class="cuerpo">
          <table class="desglose">${d.costo.desglose.map((x) => `<tr><td>${esc(x.concepto)}</td><td class="monto">${lempiras(x.monto)}</td></tr>`).join("")}</table>
          <div class="total" style="margin-bottom:0"><span>Total</span><strong class="num">${lempiras(d.costo.total)}</strong></div></div></section>
        <section class="tarjeta"><div class="cab"><h2>Cliente</h2></div><div class="cuerpo"><dl class="datos">
          <dt>Nombre</dt><dd>${esc(d.cliente.nombre)}</dd><dt>Correo</dt><dd>${esc(d.cliente.email)}</dd>
          <dt>Teléfono</dt><dd>${esc(d.cliente.telefono || "—")}</dd><dt>Seguro</dt><dd>${d.asegurado ? esc(d.poliza) : "No"}</dd></dl></div></section>
        <section class="tarjeta"><div class="cab"><h2>Correos al cliente</h2>${patron("Observer")}</div><div class="cuerpo">${mensajes(d)}
          <div class="explica"><code>NotificadorCliente</code> está suscrito al bus: recibe cada cambio y redacta el correo. El envío no sabe que existe.</div></div></section>
      </div>
    </div>`;
  $$("[data-destino]").forEach((b) => b.onclick = () => mover(d.guia, b.dataset.destino));
  const sim = $("#simular");
  if (sim) sim.onclick = async () => {
    sim.disabled = true; sim.textContent = "Simulando recorrido…";
    try { await api(`/api/envios/${d.guia}/simular`, { method: "POST" }); aviso("Simulación iniciada", "El envío avanzará solo cada 2.5 segundos."); }
    catch (e) { aviso("No se pudo simular", e.message, "error"); }
  };
}

async function mover(guia, destino) {
  if (destino === "Cancelado" && !confirm(`¿Cancelar el envío ${guia}? No se puede deshacer.`)) return;
  try { await api(`/api/envios/${guia}/estado`, { method: "POST", body: { destino } }); }
  catch (e) { aviso("Cambio rechazado", e.message, "error"); }
  // La pantalla se repinta cuando llega el evento por WebSocket.
}

function cabeceraEnvio(d) {
  const destino = d.tipo === "internacional" ? `${d.destino}, ${d.pais_destino}` : d.destino;
  return `<div class="cabecera-envio">
    <div><div class="tipo-chip ${d.tipo}">Envío ${esc(d.tipo)}</div><div class="guia-grande">${esc(d.guia)}</div>
      <div class="ruta">${esc(d.sucursal_origen)} → ${esc(destino)}</div></div>
    <div style="text-align:right">${insignia(d.estado)}<div class="tenue" style="margin-top:6px;font-size:.82rem">Último movimiento: ${fecha(d.ultimo_movimiento)}</div></div></div>`;
}

function progreso(d) {
  if (d.estado === "Cancelado") return `<div class="progreso"><div class="etapa actual alerta"><i></i>Envío cancelado</div></div>`;
  const etapas = ETAPAS[d.tipo];
  const recorridos = new Set(d.rastreo.map((r) => r.estado));
  const actual = etapas.indexOf(d.estado);
  return `<div class="progreso">${etapas.map((e, i) => {
    let c = "";
    if (e === d.estado) c = d.estado === "Entregado" ? "hecha" : "actual" + (e === "Retenido en aduana" ? " alerta" : "");
    else if (i < actual || (recorridos.has(e) && d.estado !== "Registrado")) c = "hecha";
    if (e === "Retenido en aduana" && !recorridos.has(e) && actual > i) c = "";  // no pasó por aduana
    return `<div class="etapa ${c}"><i></i>${esc(e)}</div>`;
  }).join("")}</div>`;
}

function lineaTiempo(d, animar) {
  return `<ul class="linea-tiempo">${[...d.rastreo].reverse().map((r, i) => `
    <li class="${animar && i === 0 ? "nuevo" : ""}"><div class="que">${esc(r.descripcion)} ${insignia(r.estado)}</div>
      ${r.lugar || r.responsable ? `<div class="donde">${esc([r.lugar, r.responsable && "Repartidor: " + r.responsable].filter(Boolean).join(" · "))}</div>` : ""}
      <div class="cuando">${fecha(r.hora)}</div></li>`).join("")}</ul>`;
}

function mensajes(d) {
  return d.notificaciones.length
    ? `<ul class="mensajes">${[...d.notificaciones].reverse().map((m) => `<li><small>Para ${esc(d.cliente.email)}</small>${esc(m)}</li>`).join("")}</ul>`
    : `<div class="vacio" style="padding:12px">Todavía no se han enviado avisos. Se envía uno con cada cambio de estado.</div>`;
}

// ---------- Sistema (módulo de respuesta en tiempo real) ----------
async function verSistema() {
  vista.innerHTML = `
    <div class="encabezado"><div><h1>Sistema</h1><p>Salud del bus de eventos que entrega los avisos en tiempo real.</p></div>${patron("Observer + Circuit breaker")}</div>
    <div id="sistema"></div>`;
  await pintarSistema();
  estado.temporizador = setInterval(pintarSistema, 1500);
}

async function pintarSistema() {
  const caja = $("#sistema");
  if (!caja) return;
  const s = await api("/api/sistema");
  const st = s.estadisticas, ok = s.salud.estado === "ok";
  const ms = (v) => v === null ? "—" : `${v} ms`;
  caja.innerHTML = `
    <section class="tarjeta claro" style="margin-bottom:18px">
      <div class="estado-salud"><div class="semaforo ${ok ? "ok" : "degradado"}">${ok ? "✓" : "!"}</div>
        <div><strong>${ok ? "Todo funciona" : "Servicio degradado"}</strong>
        <span>${ok ? "Todos los suscriptores responden. Los avisos se entregan al momento." : "Un servicio no responde. Su circuito está abierto y sus avisos esperan en la cola de fallidos; los demás siguen funcionando."}</span></div></div>
      <div class="simulador"><div><strong>Simular caída del servicio de SMS</strong>
        <p>Apáguelo y mueva un envío: verá los reintentos, la cola de fallidos y cómo se abre el circuito tras 5 fallos seguidos, sin que el correo ni esta pantalla dejen de funcionar.</p></div>
        <label class="interruptor"><input type="checkbox" id="tirar-sms" ${s.sms_caido ? "checked" : ""}><span></span>${s.sms_caido ? "SMS caído" : "SMS en línea"}</label></div>
    </section>
    <div class="rejilla metricas" style="margin-bottom:18px">
      ${[["Avisos entregados", st.entregados], ["Reintentos", st.reintentos], ["En cola de fallidos", st.en_cola_fallidos], ["Rechazados por circuito", st.rechazados_por_circuito],
         ["Latencia promedio", ms(st.latencia_promedio_ms)], ["Latencia p95", ms(st.latencia_p95_ms)], ["Latencia máxima", ms(st.latencia_max_ms)], ["Pantallas conectadas", s.pantallas]]
        .map(([e, v]) => `<div class="tarjeta kpi"><div class="etq">${e}</div><div class="valor num">${esc(v)}</div></div>`).join("")}
    </div>
    <div class="rejilla dos-columnas">
      <section class="tarjeta"><div class="cab"><h2>Avisos fallidos</h2>
        <button class="secundario chico" id="reprocesar" ${st.en_cola_fallidos ? "" : "disabled"}>↻ Reprocesar</button></div>
        <div class="cuerpo" style="padding-top:8px">${s.fallidos.length ? `<table class="tabla"><thead><tr><th>Guía</th><th>Servicio</th><th class="ocultar-movil">Motivo</th><th>Intentos</th></tr></thead><tbody>
          ${[...s.fallidos].reverse().map((f) => `<tr style="cursor:default"><td class="guia">${esc(f.guia)}<div class="tenue">${esc(f.estado)}</div></td><td>${esc(f.suscriptor)}</td><td class="ocultar-movil tenue">${esc(f.motivo)}</td><td class="num">${f.intentos}</td></tr>`).join("")}
          </tbody></table>` : `<div class="vacio">No hay avisos fallidos.</div>`}</div></section>
      <section class="tarjeta"><div class="cab"><h2>Suscriptores del bus</h2></div><div class="cuerpo" style="padding-top:8px">
        <table class="tabla"><thead><tr><th>Servicio</th><th>Circuito</th></tr></thead><tbody>
        ${Object.entries(s.salud.suscriptores).map(([n, x]) => `<tr style="cursor:default"><td>${esc(n)}<div class="tenue">${x.fallos_seguidos} fallos seguidos · ${x.aperturas} aperturas</div></td>
          <td><span class="circuito ${x.circuito}">${esc(x.circuito)}</span></td></tr>`).join("")}</tbody></table>
        <div class="explica">Circuito <b>cerrado</b>: se le llama normal. <b>Abierto</b>: tras 5 fallos seguidos no se le llama por 15 s. <b>Semiabierto</b>: se prueba una llamada.</div></div></section>
    </div>`;
  $("#tirar-sms").onchange = async (ev) => { await api("/api/sistema/sms", { method: "POST", body: { caido: ev.target.checked } }); pintarSistema(); };
  $("#reprocesar").onclick = async () => {
    const r = await api("/api/sistema/reprocesar", { method: "POST" });
    aviso("Cola de fallidos reprocesada", `${r.reprocesados} aviso(s) entregado(s).`);
    pintarSistema();
  };
}

// ---------- Tiempo real (WebSocket) ----------
function conectar() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  const ind = $("#conexion");
  ws.onopen = () => { ind.className = "conexion viva"; ind.lastElementChild.textContent = "En vivo"; };
  ws.onclose = () => {
    ind.className = "conexion caida"; ind.lastElementChild.textContent = "Reconectando…";
    setTimeout(conectar, 2000);
  };
  ws.onmessage = (msg) => {
    const ev = JSON.parse(msg.data);
    estado.feed.unshift(ev);
    estado.feed.length = Math.min(estado.feed.length, 30);
    pintarFeed();
    const [, nombre] = location.hash.split("/");
    if (estado.guiaAbierta === ev.guia) {
      if (nombre === "envio") verEnvio(ev.guia, true);
      if (nombre === "rastrear") pintarRastreo(ev.guia, true);
      aviso(`${ev.guia}: ${ev.nuevo}`, ev.descripcion);
    }
    if ($("#lista")) cargarEnvios().then(() => $(`#lista tr[data-guia="${ev.guia}"]`)?.classList.add("destello"));
  };
}

// ---------- Arranque ----------
$("#modo-patrones").onchange = (ev) => {
  document.body.classList.toggle("con-patrones", ev.target.checked);
  try { localStorage.setItem("zyntra-patrones", ev.target.checked ? "1" : ""); } catch {}
};
try {
  if (localStorage.getItem("zyntra-patrones")) { $("#modo-patrones").checked = true; document.body.classList.add("con-patrones"); }
} catch {}

(async () => {
  estado.catalogo = await api("/api/catalogo");
  estado.envios = await api("/api/envios").catch(() => []);
  conectar();
  ruta();
})();
