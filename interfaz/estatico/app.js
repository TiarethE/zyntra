/* Zyntra: interfaz web. Sin librerías externas: funciona sin internet. */
"use strict";

const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];
const vista = $("#vista");

const estado = {
  catalogo: null,
  envios: [],
  feed: [],
  noLeidos: 0,
  vistaActual: null,
  guiaCajon: null,
  guiaRastreo: null,
  wsViva: false,
  temporizador: null,
  filtros: { texto: "", tipo: "todos", estado: "todos" },
  orden: { col: "creado", dir: -1 },
  form: null,
  latencias: [],
  punteroLat: null,
};

// =========================================================
// Utilidades
// =========================================================
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clase = (e) => "e-" + e.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/\s+/g, "-");
const insignia = (e) => `<span class="insignia ${clase(e)}">${esc(e)}</span>`;
const lempiras = (m) => "L " + Number(m).toLocaleString("es-HN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const lempirasCorto = (m) => "L " + Math.round(Number(m)).toLocaleString("es-HN");
const entero = (n) => Math.round(n).toLocaleString("es-HN");
const sinMovimiento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const vehiculo = (tipo, extra = "") => `<svg class="vehiculo ${tipo} ${extra}" viewBox="0 0 32 20" aria-hidden="true"><use href="#v-${tipo}"/></svg>`;
const patron = (n) => `<span class="patron" title="Patrón de diseño">${esc(n)}</span>`;
const fecha = (iso) => new Date(iso).toLocaleString("es-HN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const activo = (e) => !["Entregado", "Cancelado"].includes(e.estado);
const destinoCorto = (e) => e.tipo === "internacional" ? e.pais_destino : String(e.destino).split(",").pop().trim();
const reiniciarAnim = (nodo, c) => { nodo.classList.remove(c); void nodo.offsetWidth; nodo.classList.add(c); };

function hace(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 45) return "hace un momento";
  if (s < 3600) return `hace ${Math.round(s / 60)} min`;
  if (s < 86400) return `hace ${Math.round(s / 3600)} h`;
  const d = Math.round(s / 86400);
  return d === 1 ? "ayer" : `hace ${d} días`;
}

function vacio(texto, accion = "") {
  return `<div class="vacio"><svg class="ilustracion" viewBox="0 0 120 90" aria-hidden="true"><use href="#caja-vacia"/></svg><p>${texto}</p>${accion}</div>`;
}

const ICONOS = {
  panel: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  caja: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  mas: '<path d="M12 5v14M5 12h14"/>',
  pin: '<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
  pulso: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  buscar: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  campana: '<path d="M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 21h4"/>',
  sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  luna: '<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  derecha: '<path d="m9 6 6 6-6 6"/>',
  izquierda: '<path d="m15 6-6 6 6 6"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  flecha: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  imprimir: '<path d="M7 9V3h10v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/>',
  refrescar: '<path d="M20 11a8 8 0 0 0-14.5-4.5L4 8"/><path d="M4 3v5h5"/><path d="M4 13a8 8 0 0 0 14.5 4.5L20 16"/><path d="M20 21v-5h-5"/>',
  camion: '<path d="M3 6h11v10H3zM14 9h4l3 3.5V16h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17.5" cy="17.5" r="1.8"/>',
  moneda: '<circle cx="12" cy="12" r="9"/><path d="M15 9.5c-.6-1-1.7-1.5-3-1.5-1.7 0-3 .9-3 2s1 1.7 3 2 3 .9 3 2-1.3 2-3 2c-1.3 0-2.4-.5-3-1.5M12 6v2M12 16v2"/>',
  alerta: '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  correo: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  reloj: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  ojo: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  play: '<path d="M7 4.5v15l12-7.5z"/>',
  orden: '<path d="M8 4v16M4 8l4-4 4 4M16 20V4M12 16l4 4 4-4"/>',
};
const ic = (n, extra = "") => `<svg class="i ${extra}" viewBox="0 0 24 24" aria-hidden="true">${ICONOS[n]}</svg>`;

/** Cuenta desde el valor que se mostraba hasta el nuevo, para que el cambio se note. */
function contar(nodo, valor, formato = entero) {
  if (!nodo) return;
  const antes = Number(nodo.dataset.valor ?? 0);
  nodo.dataset.valor = valor;
  if (antes === valor || sinMovimiento()) { nodo.textContent = formato(valor); return; }
  const inicio = performance.now(), dur = 700;
  const paso = (ahora) => {
    const x = Math.min(1, (ahora - inicio) / dur);
    nodo.textContent = formato(antes + (valor - antes) * (1 - Math.pow(1 - x, 3)));
    if (x < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
  const kpi = nodo.closest(".kpi");
  if (kpi && nodo.dataset.listo) reiniciarAnim(kpi, "cambio");
  nodo.dataset.listo = "1";
}

/** Cinco estrellas, como las de la bandera, cuando un envío se entrega. */
function festejar() {
  if (sinMovimiento()) return;
  const caja = $("#festejo");
  for (let i = 0; i < 5; i++) {
    const ang = (-90 + i * 72) * Math.PI / 180;
    const e = document.createElement("span");
    e.style.setProperty("--dx", `${Math.cos(ang) * 120}px`);
    e.style.setProperty("--dy", `${Math.sin(ang) * 120}px`);
    e.style.animationDelay = `${i * 40}ms`;
    e.innerHTML = `<svg viewBox="0 0 20 20"><use href="#estrella"/></svg>`;
    caja.append(e);
    setTimeout(() => e.remove(), 1400);
  }
}

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
  const icono = tipo === "error" ? "alerta" : tipo === "exito" ? "check" : "info";
  el.innerHTML = `<span class="ico-aviso">${ic(icono)}</span><div><strong>${esc(titulo)}</strong><span>${esc(texto)}</span></div>`;
  $("#avisos").append(el);
  setTimeout(() => {
    if (sinMovimiento()) { el.remove(); return; }
    el.classList.add("saliendo");
    setTimeout(() => el.remove(), 220);
  }, 4500);
}

// Tooltip compartido por todas las gráficas.
const tt = $("#tooltip");
function mostrarTT(html, x, y) {
  tt.innerHTML = html;
  tt.hidden = false;
  const r = tt.getBoundingClientRect();
  let izq = x + 14, arriba = y + 14;
  if (izq + r.width > innerWidth - 8) izq = x - r.width - 14;
  if (arriba + r.height > innerHeight - 8) arriba = y - r.height - 14;
  tt.style.left = `${Math.max(8, izq)}px`;
  tt.style.top = `${Math.max(8, arriba)}px`;
}
const ocultarTT = () => { tt.hidden = true; };

// =========================================================
// Textos del dominio
// =========================================================
const TIPOS = ["nacional", "express", "internacional"];
const NOMBRE_TIPO = { nacional: "Nacional", express: "Express", internacional: "Internacional" };
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
const FRASE = {
  "Registrado": "se registró", "En tránsito": "salió a tránsito", "Retenido en aduana": "quedó en aduana",
  "En reparto": "salió a reparto", "Entregado": "fue entregado", "Cancelado": "fue cancelado",
};
const COLOR_ESTADO = {
  "Registrado": "var(--neutro)", "En tránsito": "var(--info)", "Retenido en aduana": "var(--alerta)",
  "En reparto": "var(--violeta)", "Entregado": "var(--ok)", "Cancelado": "var(--error)",
};
const DESCRIPCION_TIPO = {
  nacional: "A cualquier ciudad de Honduras, en 2 a 3 días.",
  express: "Dentro de Honduras al día siguiente. Hasta 30 kg.",
  internacional: "Al extranjero. Pasa por aduana y exige valor declarado.",
};

// =========================================================
// Estructura: menú, tema, barra superior
// =========================================================
const MENU = [
  ["Operación", [["panel", "Panel", "panel"], ["envios", "Envíos", "caja"], ["nuevo", "Nuevo envío", "mas"]]],
  ["Clientes", [["rastrear", "Rastrear envío", "pin"]]],
  ["Plataforma", [["sistema", "Sistema", "pulso"]]],
];

function armarMenu() {
  $("#menu").innerHTML = MENU.map(([grupo, items]) => `<div class="grupo">${grupo}</div>` + items.map(([id, texto, icono]) =>
    `<a href="#/${id}" data-vista="${id}">${ic(icono)}<span>${texto}</span>${id === "envios" ? '<span class="insignia-menu" id="menu-activos" hidden></span>' : ""}</a>`).join("")).join("");
  $("#abrir-menu").innerHTML = ic("menu");
  $(".ico-buscar").outerHTML = ic("buscar");
  $("#abrir-avisos").innerHTML = ic("campana");
  if (!/Mac|iPhone|iPad/.test(navigator.platform)) return;
  $("#abrir-paleta kbd").textContent = "⌘ K";
}

function pintarTema() {
  const oscuro = document.documentElement.dataset.theme === "dark";
  $("#tema").innerHTML = ic(oscuro ? "sol" : "luna");
  $("#tema").setAttribute("aria-label", oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
}
function cambiarTema() {
  const nuevo = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = nuevo;
  try { localStorage.setItem("zyntra-tema", nuevo); } catch {}
  pintarTema();
}

function cambiarPatrones(valor) {
  $("#modo-patrones").checked = valor;
  document.body.classList.toggle("con-patrones", valor);
  try { localStorage.setItem("zyntra-patrones", valor ? "1" : ""); } catch {}
}

function pintarInsigniaMenu() {
  const n = estado.envios.filter(activo).length;
  const ins = $("#menu-activos");
  if (!ins) return;
  ins.hidden = !n;
  ins.textContent = n;
  ins.title = `${n} envíos en camino`;
}

// =========================================================
// Enrutador
// =========================================================
const vistas = { panel: verPanel, envios: verEnvios, nuevo: verNuevo, rastrear: verRastrear, sistema: verSistema };

function ruta() {
  const partes = location.hash.replace(/^#\/?/, "").split("/");
  let nombre = partes[0] || "panel";
  if (nombre === "envio") nombre = "envios";  // enlaces de la versión anterior
  if (!vistas[nombre]) nombre = "panel";
  const param = partes[1] ? decodeURIComponent(partes[1]).toUpperCase() : null;
  $("#app").classList.remove("menu-abierto");
  $$("#menu a").forEach((a) => {
    const es = a.dataset.vista === nombre;
    a.classList.toggle("activa", es);
    if (es) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });

  if (nombre === estado.vistaActual && nombre === "envios") { sincronizarCajon(param); return; }
  if (nombre === estado.vistaActual && nombre === "rastrear") { $("#buscar-guia").value = param || ""; pintarRastreo(param); return; }

  clearInterval(estado.temporizador);
  estado.vistaActual = nombre;
  estado.guiaRastreo = null;
  ocultarTT();
  reiniciarAnim(vista, "entrando");
  vistas[nombre](param);
  if (nombre !== "envios") sincronizarCajon(null);
  vista.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", ruta);

async function cargarEnvios() {
  estado.envios = await api("/api/envios");
  pintarInsigniaMenu();
  if (estado.vistaActual === "panel") pintarPanel();
  if (estado.vistaActual === "envios") pintarTabla();
}

// =========================================================
// Panel
// =========================================================
function dias(n = 7) {
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
  return Array.from({ length: n }, (_, i) => {
    const inicio = new Date(hoy); inicio.setDate(hoy.getDate() - (n - 1 - i));
    const fin = new Date(inicio); fin.setDate(inicio.getDate() + 1);
    return { inicio, fin, etq: inicio.toLocaleDateString("es-HN", { weekday: "short", day: "numeric" }).replace(".", "") };
  });
}
const enDia = (iso, d) => { const t = new Date(iso); return t >= d.inicio && t < d.fin; };

function saludo() {
  const h = new Date().getHours();
  return h < 12 ? "Buenos días" : h < 19 ? "Buenas tardes" : "Buenas noches";
}

function verPanel() {
  const hoy = new Date().toLocaleDateString("es-HN", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const kpi = (id, etq, icono) => `
    <div class="tarjeta kpi"><div class="etq"><span class="ico-kpi">${ic(icono)}</span>${etq}</div>
      <div class="fila-valor"><div class="valor num" id="k-${id}">0</div><svg class="chispa" id="c-${id}" viewBox="0 0 96 34" aria-hidden="true"></svg></div>
      <div class="sub" id="s-${id}">&nbsp;</div></div>`;
  vista.innerHTML = `
    <div class="encabezado saludo">
      <div><div class="fecha">${esc(hoy)}</div><h1>${saludo()}, Tegucigalpa</h1><p>Así va la red de Zyntra en este momento.</p></div>
      <div class="acciones"><a class="boton secundario" href="#/rastrear">${ic("pin")}Rastrear</a><a class="boton" href="#/nuevo">${ic("mas")}Nuevo envío</a></div>
    </div>
    <div class="rejilla kpis mb">
      ${kpi("hoy", "Envíos de hoy", "caja")}${kpi("camino", "En camino", "camion")}${kpi("entregados", "Entregados (7 días)", "check")}${kpi("ingresos", "Ingresos (7 días)", "moneda")}
    </div>
    <div class="rejilla col-2-1 mb">
      <section class="tarjeta">
        <div class="cab"><div><h2>Red en vivo</h2><p id="texto-red">Cargando envíos…</p></div>
          <div class="leyenda">${TIPOS.map((t) => `<span>${vehiculo(t)}${NOMBRE_TIPO[t]}</span>`).join("")}</div></div>
        <div class="cuerpo"><div class="caja-mapa" id="mapa-red"><div class="esqueleto" style="aspect-ratio:680/400"></div></div></div>
      </section>
      <section class="tarjeta">
        <div class="cab"><div><h2>Envíos por estado</h2><p>Todos los envíos registrados</p></div>${patron("State")}</div>
        <div class="cuerpo"><div class="barras-estado" id="barras-estado"></div>
          <div class="explica">Cada estado es una clase (<code>EnTransito</code>, <code>EnReparto</code>…) que decide a qué estados se puede pasar.</div></div>
      </section>
    </div>
    <div class="rejilla col-2-1 mb">
      <section class="tarjeta">
        <div class="cab"><div><h2>Envíos por día</h2><p>Registrados en los últimos 7 días, por tipo de servicio</p></div>
          <div class="leyenda">${TIPOS.map((t) => `<span><i class="punto-tipo ${t}"></i>${NOMBRE_TIPO[t]}</span>`).join("")}</div></div>
        <div class="cuerpo" id="grafica-dias"></div>
      </section>
      <section class="tarjeta">
        <div class="cab"><div><h2>Ingresos por servicio</h2><p>Últimos 7 días, sin cancelados</p></div>${patron("Factory Method")}</div>
        <div class="cuerpo" id="reparto"></div>
      </section>
    </div>
    <div class="rejilla col-2-1">
      <section class="tarjeta">
        <div class="cab"><div><h2>Envíos recientes</h2><p>Los últimos registrados en la red</p></div><a class="boton secundario chico" href="#/envios">Ver todos${ic("derecha")}</a></div>
        <div class="envoltura-tabla" style="margin-top:12px"><table class="tabla"><thead><tr><th>Guía</th><th class="ocultar-movil">Ruta</th><th>Estado</th><th class="der ocultar-movil">Total</th></tr></thead>
          <tbody id="recientes"></tbody></table></div>
      </section>
      <section class="tarjeta">
        <div class="cab"><div><h2>Actividad en vivo</h2><p>Cada cambio de estado, al instante</p></div>${patron("Observer")}</div>
        <div class="cuerpo"><ul class="feed" id="feed"></ul>
          <div class="explica">Cada cambio se publica en el <b>bus de eventos</b>. El suscriptor <code>TransmisorEnVivo</code> lo reenvía a esta pantalla por WebSocket, sin recargar.</div></div>
      </section>
    </div>`;
  $("#mapa-red").addEventListener("click", (ev) => {
    const v = ev.target.closest(".m-vehiculo");
    if (v?.dataset.guia) location.hash = "#/envios/" + v.dataset.guia;
  });
  pintarFeed();
  if (estado.envios.length) pintarPanel();
}

function chispa(svg, valores) {
  if (!svg) return;
  const max = Math.max(1, ...valores), n = valores.length;
  const x = (i) => 3 + i * (90 / (n - 1)), y = (v) => 30 - (v / max) * 26;
  const linea = valores.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join("");
  svg.innerHTML = `<path class="area-chispa" d="${linea}L${x(n - 1)} 32L3 32Z"/><path d="${linea}"/><circle cx="${x(n - 1)}" cy="${y(valores[n - 1]).toFixed(1)}" r="3"/>`;
}

function pintarPanel() {
  if (!$("#k-hoy")) return;
  const e = estado.envios, d7 = dias();
  const valido = e.filter((x) => x.estado !== "Cancelado");
  const porDia = (filtro, valor = () => 1) => d7.map((d) => e.filter((x) => filtro(x, d)).reduce((s, x) => s + valor(x), 0));

  const creadosDia = porDia((x, d) => enDia(x.creado, d));
  const caminoDia = d7.map((d) => e.filter((x) => new Date(x.creado) < d.fin &&
    (activo(x) || new Date(x.ultimo_movimiento) >= d.fin)).length);
  const entregadosDia = porDia((x, d) => x.estado === "Entregado" && enDia(x.ultimo_movimiento, d));
  const ingresosDia = porDia((x, d) => x.estado !== "Cancelado" && enDia(x.creado, d), (x) => Number(x.total));
  const suma = (a) => a.reduce((s, v) => s + v, 0);
  const activos = e.filter(activo);

  contar($("#k-hoy"), creadosDia[6]);
  contar($("#k-camino"), activos.length);
  contar($("#k-entregados"), suma(entregadosDia));
  contar($("#k-ingresos"), suma(ingresosDia), lempirasCorto);
  const ayer = creadosDia[5];
  $("#s-hoy").textContent = ayer ? `Ayer: ${ayer}` : "Ninguno ayer";
  const aduana = e.filter((x) => x.estado === "Retenido en aduana").length;
  $("#s-camino").textContent = aduana ? `${aduana} retenido${aduana > 1 ? "s" : ""} en aduana` : "Ninguno retenido en aduana";
  $("#s-entregados").textContent = `${valido.length ? Math.round(e.filter((x) => x.estado === "Entregado").length / valido.length * 100) : 0} % de los envíos vigentes`;
  $("#s-ingresos").textContent = `Promedio ${lempirasCorto(suma(ingresosDia) / 7)} por día`;
  chispa($("#c-hoy"), creadosDia);
  chispa($("#c-camino"), caminoDia);
  chispa($("#c-entregados"), entregadosDia);
  chispa($("#c-ingresos"), ingresosDia);

  // Mapa: solo se vuelve a dibujar si cambió algún envío en camino (así no se reinicia el movimiento).
  const firma = activos.map((x) => x.guia + x.estado).join("|");
  const mapa = $("#mapa-red");
  if (firma !== mapa.dataset.firma) {
    mapa.dataset.firma = firma;
    Mapa.red(mapa, e);
    const cuenta = TIPOS.map((t) => [t, activos.filter((x) => x.tipo === t).length]).filter(([, n]) => n);
    mapa.insertAdjacentHTML("beforeend", `<div class="sobre-mapa">${cuenta.map(([t, n]) => `<span><i class="punto-tipo ${t}"></i>${n} ${NOMBRE_TIPO[t].toLowerCase()}</span>`).join("")}</div>`);
  }
  $("#texto-red").textContent = activos.length ? `${activos.length} envíos en camino ahora. Toque un vehículo para abrirlo.` : "No hay envíos en camino ahora.";

  // Barras por estado
  const estados = estado.catalogo.estados;
  const maximo = Math.max(1, ...estados.map((s) => e.filter((x) => x.estado === s).length));
  $("#barras-estado").innerHTML = estados.map((s, i) => {
    const n = e.filter((x) => x.estado === s).length;
    return `<div class="barra-estado"><span>${esc(s)}</span><div class="pista"><div class="relleno" style="width:${(n / maximo * 100).toFixed(1)}%;background:${COLOR_ESTADO[s]};animation-delay:${i * 50}ms"></div></div><span class="cuenta num">${n}</span></div>`;
  }).join("");

  graficaDias(d7);
  repartoIngresos(e.filter((x) => x.estado !== "Cancelado" && new Date(x.creado) >= d7[0].inicio));

  const recientes = [...e].sort((a, b) => b.creado.localeCompare(a.creado)).slice(0, 6);
  $("#recientes").innerHTML = recientes.map((x) => filaEnvio(x, true)).join("");
  enlazarFilas($("#recientes"));
}

function graficaDias(d7) {
  const caja = $("#grafica-dias");
  const datos = d7.map((d) => ({ etq: d.etq, ...Object.fromEntries(TIPOS.map((t) => [t, estado.envios.filter((x) => x.tipo === t && enDia(x.creado, d)).length])) }));
  const firma = JSON.stringify(datos);
  if (caja.dataset.firma === firma) return;
  const primera = !caja.dataset.firma;
  caja.dataset.firma = firma;
  const W = Math.round(Math.max(320, Math.min(640, caja.clientWidth - 36 || 640))), H = W < 500 ? 220 : 240, L = 30, R = 6, T = 18, B = 28;
  const totales = datos.map((d) => TIPOS.reduce((s, t) => s + d[t], 0));
  const max = Math.max(2, Math.ceil(Math.max(...totales) / 2) * 2);
  const y = (v) => T + (H - T - B) * (1 - v / max);
  const banda = (W - L - R) / datos.length, ancho = Math.min(38, banda * 0.5);
  const guias = [0, max / 2, max].map((v) => `<line class="${v ? "linea-guia" : "base"}" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text class="eje" x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${v}</text>`).join("");
  const columnas = datos.map((d, i) => {
    const x = L + banda * i + (banda - ancho) / 2;
    let base = 0;
    const visibles = TIPOS.filter((t) => d[t]);
    const segs = visibles.map((t, j) => {
      const y1 = y(base + d[t]), y0 = y(base);
      base += d[t];
      const alto = Math.max(0, y0 - y1 - (j ? 2 : 0));  // 2 px de separación entre segmentos
      const r = j === visibles.length - 1 ? Math.min(4, alto) : 0;
      return `<path class="seg ${t}" d="M${x} ${y0 - (j ? 2 : 0)}V${y1 + r}q0 -${r} ${r} -${r}H${x + ancho - r}q${r} 0 ${r} ${r}V${y0 - (j ? 2 : 0)}Z"/>`;
    }).join("");
    const etqTotal = totales[i] ? `<text class="eje" x="${x + ancho / 2}" y="${y(totales[i]) - 6}" text-anchor="middle" style="fill:var(--texto-2);font-weight:650">${totales[i]}</text>` : "";
    return `<g class="columna" data-i="${i}" tabindex="0" role="img" aria-label="${esc(d.etq)}: ${totales[i]} envíos">
      <rect class="zona" x="${L + banda * i}" y="${T}" width="${banda}" height="${H - T - B}"/>
      <g class="${primera ? "crece" : ""}" style="animation-delay:${i * 50}ms">${segs}</g>${etqTotal}
      <text class="eje" x="${x + ancho / 2}" y="${H - 8}" text-anchor="middle">${esc(d.etq)}</text></g>`;
  }).join("");
  caja.innerHTML = `<svg class="grafica" viewBox="0 0 ${W} ${H}" role="group" aria-label="Envíos registrados por día">${guias}${columnas}</svg>`;
  const contenido = (i) => `<strong>${esc(datos[i].etq)}</strong>${TIPOS.map((t) => `<div class="fila-tt"><i class="punto-tipo ${t}"></i>${NOMBRE_TIPO[t]}<b>${datos[i][t]}</b></div>`).join("")}<div class="fila-tt">Total<b>${totales[i]}</b></div>`;
  $$(".columna", caja).forEach((g) => {
    const i = Number(g.dataset.i);
    g.addEventListener("mousemove", (ev) => mostrarTT(contenido(i), ev.clientX, ev.clientY));
    g.addEventListener("mouseleave", ocultarTT);
    g.addEventListener("focus", () => { const r = g.getBoundingClientRect(); mostrarTT(contenido(i), r.right, r.top + 20); });
    g.addEventListener("blur", ocultarTT);
  });
}

function repartoIngresos(lista) {
  const caja = $("#reparto");
  const total = lista.reduce((s, x) => s + Number(x.total), 0);
  const partes = TIPOS.map((t) => {
    const del = lista.filter((x) => x.tipo === t);
    return { t, monto: del.reduce((s, x) => s + Number(x.total), 0), n: del.length };
  });
  const firma = JSON.stringify(partes);
  if (caja.dataset.firma === firma) return;
  caja.dataset.firma = firma;
  if (!total) { caja.innerHTML = vacio("Aún no hay ingresos en los últimos 7 días."); return; }
  caja.innerHTML = `
    <div class="total" style="margin:0 0 6px"><span>Total</span><strong class="num" id="total-reparto">L 0</strong></div>
    <div class="reparto" role="img" aria-label="Reparto de ingresos por servicio">${partes.filter((p) => p.monto).map((p, i) =>
      `<span style="flex:${p.monto};background:var(--c-${p.t});animation-delay:${i * 80}ms" title="${NOMBRE_TIPO[p.t]}: ${lempiras(p.monto)}"></span>`).join("")}</div>
    <div class="reparto-lista">${partes.map((p) => `<div><i class="punto-tipo ${p.t}"></i>${NOMBRE_TIPO[p.t]} <span class="tenue">${p.n} envíos</span><b>${lempirasCorto(p.monto)}</b><span class="tenue">${Math.round(p.monto / total * 100)} %</span></div>`).join("")}</div>`;
  contar($("#total-reparto"), total, lempirasCorto);
}

function itemFeed(ev, nuevo) {
  const tipo = ev.tipo || estado.envios.find((x) => x.guia === ev.guia)?.tipo || "nacional";
  return `<li class="${nuevo ? "nuevo" : ""}"><span class="burbuja">${vehiculo(tipo)}</span>
    <div><button type="button" class="guia" data-guia="${esc(ev.guia)}">${esc(ev.guia)}</button> ${FRASE[ev.nuevo] || "cambió a"} ${insignia(ev.nuevo)}
      <div class="cuando" title="${esc(fecha(ev.hora))}">${hace(ev.hora)}${ev.descripcion ? " · " + esc(ev.descripcion) : ""}</div></div></li>`;
}

function movimientosRecientes() {
  if (estado.feed.length) return estado.feed;
  // Antes del primer evento en vivo, se muestran los últimos movimientos conocidos.
  return [...estado.envios].sort((a, b) => b.ultimo_movimiento.localeCompare(a.ultimo_movimiento)).slice(0, 8)
    .map((x) => ({ guia: x.guia, nuevo: x.estado, hora: x.ultimo_movimiento, tipo: x.tipo, descripcion: "" }));
}

function pintarFeed(nuevo = false) {
  const lista = movimientosRecientes();
  const html = lista.length ? lista.map((ev, i) => itemFeed(ev, nuevo && i === 0)).join("")
    : `<li style="display:block;border:0">${vacio("Aún no hay movimientos. Abra un envío y presione «Simular recorrido».")}</li>`;
  for (const ul of [$("#feed"), $("#panel-avisos .feed")]) {
    if (!ul) continue;
    ul.innerHTML = html;
    $$(".guia", ul).forEach((b) => b.onclick = () => { cerrarAvisos(); location.hash = "#/envios/" + b.dataset.guia; });
  }
}

// =========================================================
// Envíos: tabla con filtros y cajón de detalle
// =========================================================
function filaEnvio(x, compacta = false) {
  return `<tr data-guia="${esc(x.guia)}" tabindex="0">
    <td><div class="celda-guia"><span class="burbuja">${vehiculo(x.tipo)}</span><div><div class="guia">${esc(x.guia)}</div><div class="tipo-chip">${esc(x.tipo)} <span class="cuando-chip">· ${hace(x.creado)}</span></div></div></div></td>
    ${compacta ? "" : `<td class="ocultar-movil">${esc(x.cliente_nombre)}</td>`}
    <td class="ocultar-movil"><span class="ruta-celda">${esc(x.origen)}${ic("flecha")}${esc(destinoCorto(x))}</span></td>
    <td>${insignia(x.estado)}${x.simulando ? '<div class="tenue" style="margin-top:3px">En ruta…</div>' : ""}</td>
    <td class="der num ocultar-movil">${lempiras(x.total)}</td>
  </tr>`;
}

function enlazarFilas(tbody) {
  $$("tr[data-guia]", tbody).forEach((tr) => {
    tr.onclick = () => location.hash = "#/envios/" + tr.dataset.guia;
    tr.onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); tr.click(); } };
  });
}

function verEnvios(guia) {
  const f = estado.filtros;
  const columnas = [["creado", "Guía"], ["cliente_nombre", "Cliente", "ocultar-movil"], [null, "Ruta", "ocultar-movil"], ["estado", "Estado"], ["peso_kg", "Peso", "der ocultar-movil"], ["total", "Total", "der ocultar-movil"]];
  vista.innerHTML = `
    <div class="encabezado">
      <div><h1>Envíos</h1><p>Busque, filtre y abra cualquier envío para moverlo de estado.</p></div>
      <a class="boton" href="#/nuevo">${ic("mas")}Nuevo envío</a>
    </div>
    <section class="tarjeta">
      <div class="herramientas">
        <label class="buscar-tabla">${ic("buscar")}<span class="sr">Buscar envíos</span><input type="search" id="filtro-texto" placeholder="Guía, cliente o destino" value="${esc(f.texto)}" autocomplete="off"></label>
        <div class="segmentado" role="group" aria-label="Tipo de servicio">${["todos", ...TIPOS].map((t) =>
          `<button type="button" data-tipo="${t}" aria-pressed="${f.tipo === t}">${t === "todos" ? "Todos" : NOMBRE_TIPO[t]}</button>`).join("")}</div>
        <label><span class="sr">Estado</span><select id="filtro-estado"><option value="todos">Todos los estados</option>${estado.catalogo.estados.map((s) =>
          `<option ${f.estado === s ? "selected" : ""}>${esc(s)}</option>`).join("")}</select></label>
      </div>
      <div class="envoltura-tabla"><table class="tabla">
        <thead><tr>${columnas.map(([col, texto, c = ""]) => `<th class="${c}" data-col="${col || ""}">${col
          ? `<button type="button" data-ordenar="${col}">${texto}<span class="flecha-orden"></span></button>` : texto}</th>`).join("")}</tr></thead>
        <tbody id="lista"></tbody></table></div>
      <div class="pie-tabla"><span id="cuenta-tabla"></span><span>Toque una fila para ver el detalle</span></div>
    </section>`;
  $("#filtro-texto").addEventListener("input", (ev) => { f.texto = ev.target.value; pintarTabla(); });
  $("#filtro-estado").addEventListener("change", (ev) => { f.estado = ev.target.value; pintarTabla(); });
  $$("[data-tipo]").forEach((b) => b.onclick = () => {
    f.tipo = b.dataset.tipo;
    $$("[data-tipo]").forEach((o) => o.setAttribute("aria-pressed", o === b));
    pintarTabla();
  });
  $$("[data-ordenar]").forEach((b) => b.onclick = () => {
    const col = b.dataset.ordenar, o = estado.orden;
    o.dir = o.col === col ? -o.dir : (col === "cliente_nombre" || col === "estado" ? 1 : -1);
    o.col = col;
    pintarTabla();
  });
  pintarTabla();
  sincronizarCajon(guia);
}

function pintarTabla() {
  const tbody = $("#lista");
  if (!tbody) return;
  const f = estado.filtros, o = estado.orden;
  const t = f.texto.trim().toLowerCase();
  const visibles = estado.envios.filter((x) =>
    (f.tipo === "todos" || x.tipo === f.tipo) && (f.estado === "todos" || x.estado === f.estado) &&
    (!t || [x.guia, x.cliente_nombre, x.destino, x.pais_destino, x.origen].some((v) => String(v).toLowerCase().includes(t))));
  const valor = (x) => ["total", "peso_kg"].includes(o.col) ? Number(x[o.col]) : String(x[o.col]);
  visibles.sort((a, b) => { const va = valor(a), vb = valor(b); return (va > vb ? 1 : va < vb ? -1 : 0) * o.dir; });
  $$(".tabla th[data-col]").forEach((th) => {
    const es = th.dataset.col === o.col;
    if (es) th.setAttribute("aria-sort", o.dir > 0 ? "ascending" : "descending"); else th.removeAttribute("aria-sort");
    const flecha = $(".flecha-orden", th);
    if (flecha) flecha.textContent = es ? (o.dir > 0 ? "↑" : "↓") : "";
  });
  const hayFiltro = t || f.tipo !== "todos" || f.estado !== "todos";
  tbody.innerHTML = visibles.length ? visibles.map(filaEnvio).join("")
    : `<tr><td colspan="6" style="cursor:default">${vacio(hayFiltro ? "Ningún envío coincide con esos filtros." : "Todavía no hay envíos.",
      hayFiltro ? '<button type="button" class="secundario chico" id="limpiar-filtros">Quitar filtros</button>' : '<a class="boton chico" href="#/nuevo">Registrar el primero</a>')}</td></tr>`;
  $("#limpiar-filtros")?.addEventListener("click", () => { estado.filtros = { texto: "", tipo: "todos", estado: "todos" }; verEnvios(estado.guiaCajon); });
  $("#cuenta-tabla").textContent = `Mostrando ${visibles.length} de ${estado.envios.length} envíos`;
  enlazarFilas(tbody);
  $$("tr[data-guia]", tbody).forEach((tr) => tr.classList.toggle("seleccionada", tr.dataset.guia === estado.guiaCajon));
}

// ---------- Cajón ----------
let focoPrevio = null;

function sincronizarCajon(guia) {
  if (guia && guia !== estado.guiaCajon) abrirCajon(guia);
  else if (!guia && estado.guiaCajon) ocultarCajon();
}

async function abrirCajon(guia) {
  const cajon = $("#cajon"), cortina = $("#cortina");
  if (cajon.hidden) focoPrevio = document.activeElement;
  estado.guiaCajon = guia;
  cajon.classList.remove("saliendo");
  cajon.hidden = false; cortina.hidden = false;
  document.body.style.overflow = "hidden";
  cajon.innerHTML = `<div class="cajon-cab"><div class="titulo"><div class="esqueleto" style="height:14px;width:90px"></div><div class="esqueleto" style="height:24px;width:200px;margin-top:8px"></div></div>
    <button class="icono-btn" data-cerrar aria-label="Cerrar detalle">${ic("x")}</button></div>
    <div class="cajon-cuerpo"><div class="esqueleto" style="height:280px"></div><div class="esqueleto" style="height:120px"></div></div>`;
  $("[data-cerrar]", cajon).onclick = cerrarCajon;
  await pintarCajon(guia, false);
  $("[data-cerrar]", cajon)?.focus();
}

function cerrarCajon() {
  if (location.hash.startsWith("#/envios/")) location.hash = "#/envios";
  else ocultarCajon();
}

function ocultarCajon() {
  const cajon = $("#cajon"), cortina = $("#cortina");
  estado.guiaCajon = null;
  document.body.style.overflow = "";
  $$("#lista tr.seleccionada").forEach((tr) => tr.classList.remove("seleccionada"));
  const fin = () => { cajon.hidden = true; cortina.hidden = true; cajon.classList.remove("saliendo"); cajon.innerHTML = ""; };
  if (sinMovimiento() || cajon.hidden) fin();
  else { cajon.classList.add("saliendo"); setTimeout(fin, 200); }
  focoPrevio?.focus?.();
  focoPrevio = null;
}

async function pintarCajon(guia, animar) {
  const cajon = $("#cajon");
  let d;
  try { d = await api("/api/envios/" + encodeURIComponent(guia)); }
  catch (e) {
    if (estado.guiaCajon !== guia) return;
    $(".cajon-cuerpo", cajon).innerHTML = `<div class="tarjeta">${vacio(esc(e.message))}</div>`;
    return;
  }
  if (estado.guiaCajon !== guia) return;
  const scroll = $(".cajon-cuerpo", cajon)?.scrollTop || 0;
  const destino = d.tipo === "internacional" ? `${d.destino}, ${d.pais_destino}` : d.destino;
  cajon.innerHTML = `
    <div class="cajon-cab">
      <span class="burbuja-grande">${vehiculo(d.tipo, "xl")}</span>
      <div class="titulo"><div class="tipo-chip">Envío ${esc(d.tipo)}</div><div class="guia-grande guia" id="cajon-titulo">${esc(d.guia)}</div>
        <div class="tenue">${esc(d.sucursal_origen)} → ${esc(destino)}</div></div>
      ${insignia(d.estado)}
      <button class="icono-btn" data-cerrar aria-label="Cerrar detalle">${ic("x")}</button>
    </div>
    <div class="cajon-cuerpo">
      <section class="tarjeta"><div class="cuerpo"><div class="caja-mapa" id="mapa-ruta"></div><div style="margin-top:16px">${progreso(d)}</div></div></section>
      <section class="tarjeta">
        <div class="cab"><div><h2>Mover el envío</h2><p>Solo se ofrecen los cambios que el estado actual permite</p></div>${patron("State")}</div>
        <div class="cuerpo">${acciones(d)}
          <div class="explica">El estado actual es la clase <code>${esc(CLASE_ESTADO[d.estado])}</code>. «Retener en aduana» solo aparece en internacionales: esa regla vive en <code>EnTransito</code>.</div></div>
      </section>
      <div class="rejilla col-1-1">
        <section class="tarjeta"><div class="cab"><h2>Historial</h2><span class="tenue">${d.rastreo.length} ${d.rastreo.length === 1 ? "movimiento" : "movimientos"}</span></div><div class="cuerpo">${lineaTiempo(d, animar)}</div></section>
        <div class="rejilla">
          <section class="tarjeta"><div class="cab"><h2>Costo</h2>${patron("Decorator")}</div><div class="cuerpo">${desglose(d.costo)}
            <div class="explica">Seguro y manejo frágil son capas (<code>SeguroDecorator</code>, <code>ManejoFragilDecorator</code>) sobre el costo base.</div></div></section>
          <section class="tarjeta"><div class="cab"><h2>Cliente</h2></div><div class="cuerpo"><dl class="datos">
            <dt>Nombre</dt><dd>${esc(d.cliente.nombre)}</dd><dt>Correo</dt><dd>${esc(d.cliente.email)}</dd>
            <dt>Teléfono</dt><dd>${esc(d.cliente.telefono || "—")}</dd><dt>Seguro</dt><dd>${d.asegurado ? esc(d.poliza) : "Sin seguro"}</dd></dl></div></section>
        </div>
      </div>
      <section class="tarjeta"><div class="cab"><h2>Paquetes</h2><span class="tenue">Peso facturable ${esc(d.costo.peso_facturable_kg)} kg</span></div>
        <div class="envoltura-tabla" style="margin-top:10px"><table class="tabla"><thead><tr><th>Contenido</th><th class="ocultar-movil">Medidas</th><th class="der">Peso</th><th class="der">Valor</th></tr></thead><tbody>
        ${d.paquetes.map((p) => `<tr style="cursor:default"><td>${esc(p.contenido)}${p.fragil ? ' <span class="insignia e-retenido-en-aduana">Frágil</span>' : ""}</td>
          <td class="ocultar-movil tenue">${esc(p.medidas)}</td><td class="der num">${esc(p.peso_kg)} kg</td><td class="der num">${lempiras(p.valor_declarado)}</td></tr>`).join("")}
        </tbody></table></div></section>
      <section class="tarjeta"><div class="cab"><h2>Correos al cliente</h2>${patron("Observer")}</div><div class="cuerpo">${mensajes(d)}
        <div class="explica"><code>NotificadorCliente</code> está suscrito al bus: recibe cada cambio y redacta el correo. El envío no sabe que existe.</div></div></section>
    </div>`;
  $(".cajon-cuerpo", cajon).scrollTop = scroll;
  $("[data-cerrar]", cajon).onclick = cerrarCajon;
  Mapa.ruta($("#mapa-ruta"), d);
  enlazarAcciones(d, () => pintarCajon(d.guia, true));
  $$("#lista tr[data-guia]").forEach((tr) => tr.classList.toggle("seleccionada", tr.dataset.guia === d.guia));
}

function acciones(d) {
  if (!d.siguientes.length) return `<p class="tenue" style="font-size:.9rem">El envío está «${esc(d.estado)}». Es un estado final: ya no se puede mover.</p>`;
  return `<div class="acciones">${d.siguientes.map((e) =>
    `<button type="button" class="${e === "Cancelado" ? "peligro" : ""}" data-destino="${esc(e)}">${e === "Entregado" ? ic("check") : ""}${esc(VERBO[e] || e)}</button>`).join("")}
    <button type="button" class="secundario" id="simular" ${d.simulando ? "disabled" : ""}>${ic("play")}${d.simulando ? "Recorriendo la ruta…" : "Simular recorrido"}</button></div>`;
}

function enlazarAcciones(d, repintar) {
  $$("[data-destino]").forEach((b) => b.onclick = async () => {
    const destino = b.dataset.destino;
    if (destino === "Cancelado" && !b.dataset.confirmar) {
      b.dataset.confirmar = "1";
      b.textContent = "Confirmar cancelación";
      setTimeout(() => { if (b.isConnected) { delete b.dataset.confirmar; b.textContent = VERBO.Cancelado; } }, 4000);
      return;
    }
    $$("[data-destino], #simular").forEach((x) => x.disabled = true);
    try {
      await api(`/api/envios/${d.guia}/estado`, { method: "POST", body: { destino } });
      if (!estado.wsViva) { repintar(); cargarEnvios(); }  // sin WebSocket, se repinta aquí
    } catch (e) {
      aviso("Cambio rechazado", e.message, "error");
      $$("[data-destino], #simular").forEach((x) => x.disabled = false);
    }
  });
  const sim = $("#simular");
  if (sim) sim.onclick = async () => {
    sim.disabled = true;
    sim.innerHTML = `${ic("play")}Recorriendo la ruta…`;
    try { await api(`/api/envios/${d.guia}/simular`, { method: "POST" }); aviso("Simulación iniciada", "El envío avanzará solo cada 2.5 segundos."); }
    catch (e) { aviso("No se pudo simular", e.message, "error"); sim.disabled = false; }
  };
}

function progreso(d) {
  if (d.estado === "Cancelado") return `<div class="progreso"><div class="etapa actual alerta"><i></i>Envío cancelado</div></div>`;
  const etapas = ETAPAS[d.tipo];
  const recorridos = new Set(d.rastreo.map((r) => r.estado));
  const actual = etapas.indexOf(d.estado);
  return `<div class="progreso">${etapas.map((e, i) => {
    let c = "";
    if (e === d.estado) c = d.estado === "Entregado" ? "hecha" : "actual" + (e === "Retenido en aduana" ? " alerta" : "");
    else if (i < actual) c = "hecha";
    if (e === "Retenido en aduana" && !recorridos.has(e) && actual > i) c = "";  // no pasó por aduana
    return `<div class="etapa ${c}"><i></i>${esc(e)}</div>`;
  }).join("")}</div>`;
}

function lineaTiempo(d, animar) {
  return `<ul class="linea-tiempo">${[...d.rastreo].reverse().map((r, i) => `
    <li class="${animar && i === 0 ? "nuevo" : ""}"><div class="que">${insignia(r.estado)}</div>
      <div class="donde">${esc(r.descripcion)}${r.lugar || r.responsable ? " · " + esc([r.lugar, r.responsable && "Repartidor: " + r.responsable].filter(Boolean).join(" · ")) : ""}</div>
      <div class="cuando">${fecha(r.hora)}</div></li>`).join("")}</ul>`;
}

function mensajes(d) {
  return d.notificaciones.length
    ? `<ul class="mensajes">${[...d.notificaciones].reverse().map((m) => `<li><small><span>${ic("correo")} Para ${esc(d.cliente.email)}</span></small>${esc(m)}</li>`).join("")}</ul>`
    : `<p class="tenue">Todavía no se han enviado correos. Se envía uno con cada cambio de estado.</p>`;
}

function desglose(c, anteriores = null) {
  const clave = (t) => t.split(" (")[0];
  return `<table class="desglose">${c.desglose.map((x) => `<tr data-concepto="${esc(clave(x.concepto))}" class="${anteriores && anteriores.size && !anteriores.has(clave(x.concepto)) ? "capa-nueva" : ""}">
    <td>${esc(x.concepto)}</td><td class="monto">${lempiras(x.monto)}</td></tr>`).join("")}</table>
    <div class="total"><span>Total</span><strong class="num total-cot">${lempiras(c.total)}</strong></div>`;
}

// =========================================================
// Nuevo envío: asistente en 5 pasos
// =========================================================
const PASOS = [["Servicio", "Tipo de envío"], ["Ruta", "Origen y destino"], ["Paquetes", "Peso y medidas"], ["Cliente", "Quién envía"], ["Revisar", "Confirmar"]];
const paqueteVacio = () => ({ contenido: "", peso_kg: "", alto_cm: "", ancho_cm: "", largo_cm: "", valor_declarado: "", fragil: false });
const paqueteCompleto = (p) => ["peso_kg", "alto_cm", "ancho_cm", "largo_cm"].every((c) => Number(p[c]) > 0);
const formularioNuevo = () => ({
  paso: 0, maximo: 0, errores: {}, cot: null, errorCot: "", intentado: false,
  datos: { tipo: "nacional", sucursal_origen: String(estado.catalogo.sucursales[0].id), direccion_destino: "", pais_destino: "",
    asegurar: false, cliente: { nombre: "", email: "", telefono: "" }, paquetes: [paqueteVacio()] },
});

function verNuevo() {
  estado.form ??= formularioNuevo();
  vista.innerHTML = `
    <div class="encabezado"><div><div class="miga"><a href="#/envios">Envíos</a>${ic("derecha")}<span>Nuevo</span></div>
      <h1>Nuevo envío</h1><p>Cinco pasos cortos. El costo se calcula mientras escribe.</p></div></div>
    <div class="asistente">
      <ol class="pasos" id="pasos"></ol>
      <form class="tarjeta" id="form" novalidate><div class="paso-cuerpo" id="paso"></div>
        <div class="paso-pie"><button type="button" class="secundario" id="atras">${ic("izquierda")}Atrás</button><button type="submit" id="seguir"></button></div></form>
      <aside class="tarjeta resumen">
        <div class="cab"><div><h2>Cotización</h2><p>En lempiras (HNL)</p></div>${patron("Decorator")}</div>
        <div class="cuerpo"><div class="caja-mapa chica" id="mapa-cotizacion"></div><div id="lineas-resumen"></div><div id="cotizacion"></div>
          <p class="tenue" style="margin-top:10px">Las tarifas vienen de <code>tarifas.json</code>. Cambiar un precio es editar ese archivo.</p></div>
      </aside>
    </div>`;
  const form = $("#form");
  form.addEventListener("input", leerCampo);
  form.addEventListener("change", leerCampo);
  form.addEventListener("submit", (ev) => { ev.preventDefault(); seguir(); });
  $("#atras").onclick = () => irPaso(estado.form.paso - 1);
  pintarPaso();
  cotizar();
}

function irPaso(n) {
  const fm = estado.form;
  if (n < 0 || n > fm.maximo) return;
  fm.paso = n;
  fm.intentado = false;
  fm.errores = {};
  pintarPaso();
  $("#paso").querySelector("input, select")?.focus({ preventScroll: true });
}

function pintarPaso() {
  const fm = estado.form, f = fm.datos;
  $("#pasos").innerHTML = PASOS.map(([n, sub], i) => `<li class="${i < fm.paso || i < fm.maximo && i !== fm.paso ? "hecho" : ""} ${i === fm.paso ? "actual" : ""}">
    <button type="button" data-paso="${i}" ${i > fm.maximo ? "disabled" : ""} ${i === fm.paso ? 'aria-current="step"' : ""}><span class="n">${i < fm.paso ? ic("check") : i + 1}</span><span>${n}<small>${sub}</small></span></button></li>`).join("");
  $$("[data-paso]").forEach((b) => b.onclick = () => irPaso(Number(b.dataset.paso)));
  const err = (k) => fm.errores[k] ? `<span class="error-campo" id="err-${k}">${esc(fm.errores[k])}</span>` : "";
  const inv = (k) => fm.errores[k] ? `aria-invalid="true" aria-describedby="err-${k}"` : "";
  const tarifa = (id) => estado.catalogo.tipos.find((t) => t.id === id);
  const cuerpos = [
    () => `<h2>¿Qué servicio necesita? ${patron("Factory Method")}</h2><p class="intro">Cada servicio tiene sus propias reglas y tarifa.</p>
      <div class="tipos" role="radiogroup" aria-label="Tipo de envío">${TIPOS.map((t) => `
        <label class="tipo"><input type="radio" name="tipo" value="${t}" ${f.tipo === t ? "checked" : ""}><span class="marca-check">${ic("check")}</span>
          ${vehiculo(t)}<strong>${NOMBRE_TIPO[t]}</strong><small>${DESCRIPCION_TIPO[t]}</small>
          <span class="tarifa">${lempiras(tarifa(t).fija)} + ${lempiras(tarifa(t).por_kg)}/kg</span></label>`).join("")}</div>
      <div class="explica">Cada tipo tiene su <b>creador</b> (<code>EnvioNacionalCreator</code>, <code>EnvioExpressCreator</code>, <code>EnvioInternacionalCreator</code>) que valida sus reglas antes de crear el envío.</div>`,
    () => `<h2>¿De dónde a dónde?</h2><p class="intro">${f.tipo === "internacional" ? "El paquete sale de una sucursal y cruza la frontera." : "El paquete sale de una sucursal y viaja dentro de Honduras."}</p>
      <div class="fila">
        <label class="campo">Sucursal de origen<select name="sucursal_origen">${estado.catalogo.sucursales.map((s) =>
          `<option value="${s.id}" ${String(f.sucursal_origen) === String(s.id) ? "selected" : ""}>${esc(s.nombre)}</option>`).join("")}</select></label>
        ${f.tipo === "internacional" ? `<label class="campo">País de destino<input type="text" name="pais_destino" value="${esc(f.pais_destino)}" placeholder="Estados Unidos" list="paises" ${inv("pais_destino")}>${err("pais_destino")}</label>` : ""}
      </div>
      <datalist id="paises">${["Estados Unidos", "México", "Guatemala", "El Salvador", "Nicaragua", "Costa Rica", "España", "Canadá"].map((p) => `<option>${p}</option>`).join("")}</datalist>
      <label class="campo" style="margin-top:14px">Dirección de destino<input type="text" name="direccion_destino" value="${esc(f.direccion_destino)}" placeholder="${f.tipo === "internacional" ? "1200 Brickell Ave, Miami" : "Col. Kennedy, Tegucigalpa"}" ${inv("direccion_destino")}>
        <span class="ayuda">Incluya colonia o barrio y la ciudad: así se dibuja la ruta.</span>${err("direccion_destino")}</label>`,
    () => `<h2>¿Qué va a enviar?</h2><p class="intro">Se cobra el mayor entre el peso real y el volumétrico (alto × ancho × largo ÷ 5000).</p>
      <div id="paquetes">${f.paquetes.map((p, i) => `
        <div class="paquete" data-i="${i}">
          <div class="cab-paq"><span>Paquete ${i + 1}</span>${f.paquetes.length > 1 ? `<button type="button" class="quitar" data-quitar="${i}">${ic("x")}Quitar</button>` : ""}</div>
          <div class="fila">
            <label class="campo">Contenido<input type="text" data-c="contenido" value="${esc(p.contenido)}" placeholder="Café de Marcala" ${inv(`p${i}_contenido`)}>${err(`p${i}_contenido`)}</label>
            <label class="campo">Peso (kg)<input type="number" min="0" step="0.1" data-c="peso_kg" value="${esc(p.peso_kg)}" placeholder="2.5" ${inv(`p${i}_peso_kg`)}>${err(`p${i}_peso_kg`)}</label>
            <label class="campo">Valor (L)<input type="number" min="0" data-c="valor_declarado" value="${esc(p.valor_declarado)}" placeholder="0" ${inv(`p${i}_valor_declarado`)}>${err(`p${i}_valor_declarado`)}</label>
          </div>
          <div class="fila medidas" style="margin-top:12px">
            <label class="campo">Alto (cm)<input type="number" min="0" data-c="alto_cm" value="${esc(p.alto_cm)}" placeholder="20" ${inv(`p${i}_medidas`)}></label>
            <label class="campo">Ancho (cm)<input type="number" min="0" data-c="ancho_cm" value="${esc(p.ancho_cm)}" placeholder="30" ${inv(`p${i}_medidas`)}></label>
            <label class="campo">Largo (cm)<input type="number" min="0" data-c="largo_cm" value="${esc(p.largo_cm)}" placeholder="40" ${inv(`p${i}_medidas`)}></label>
          </div>
          ${fm.errores[`p${i}_medidas`] ? `<div class="campo" style="grid-column:1;margin-top:4px">${err(`p${i}_medidas`)}</div>` : ""}
          <div class="pie-paq"><label class="casilla"><input type="checkbox" data-c="fragil" ${p.fragil ? "checked" : ""}> Frágil: manejo con cuidado</label></div>
          <div class="vista-caja" aria-hidden="true">${cajaIso(p)}</div>
        </div>`).join("")}</div>
      <button type="button" class="secundario chico" id="agregar">${ic("mas")}Agregar paquete</button>
      <div style="margin-top:18px;padding-top:16px;border-top:1px solid var(--borde)"><label class="casilla"><input type="checkbox" name="asegurar" ${f.asegurar ? "checked" : ""}> Asegurar el envío por su valor declarado</label></div>
      ${fm.errorCot ? `<div class="error-form" style="margin-top:14px">${ic("alerta")}<span>${esc(fm.errorCot)}</span></div>` : ""}
      <div class="explica">El costo base es una pieza; el <b>seguro</b> y el <b>manejo frágil</b> son capas (<code>SeguroDecorator</code>, <code>ManejoFragilDecorator</code>) que se agregan solo si hacen falta. Mire cómo aparecen en la cotización.</div>`,
    () => `<h2>¿Quién envía?</h2><p class="intro">El cliente recibe un correo con cada cambio de estado.</p>
      <div class="fila">
        <label class="campo">Nombre completo<input type="text" name="c_nombre" value="${esc(f.cliente.nombre)}" placeholder="Ana López" autocomplete="name" ${inv("c_nombre")}>${err("c_nombre")}</label>
        <label class="campo">Correo<input type="email" name="c_email" value="${esc(f.cliente.email)}" placeholder="ana@correo.hn" autocomplete="email" ${inv("c_email")}>${err("c_email")}</label>
        <label class="campo">Teléfono <span class="ayuda">Opcional</span><input type="tel" name="c_telefono" value="${esc(f.cliente.telefono)}" placeholder="9999-0000" autocomplete="tel"></label>
      </div>`,
    () => {
      const s = estado.catalogo.sucursales.find((x) => String(x.id) === String(f.sucursal_origen));
      const bloque = (t, i, html) => `<div class="bloque"><h3>${t}<button type="button" class="fantasma-btn" data-ir="${i}">Editar</button></h3>${html}</div>`;
      return `<h2>Revise y registre</h2><p class="intro">Si algo no está bien, toque «Editar» en esa parte.</p>
        <div class="revisar">
          ${bloque("Servicio", 0, `<div class="tipo-chip">${vehiculo(f.tipo)}${NOMBRE_TIPO[f.tipo]}</div>${f.asegurar ? '<div class="tenue" style="margin-top:6px">Con seguro</div>' : ""}`)}
          ${bloque("Ruta", 1, `<div>${esc(s?.nombre)}</div><div class="tenue">→ ${esc(f.direccion_destino)}${f.tipo === "internacional" ? ", " + esc(f.pais_destino) : ""}</div>`)}
          ${bloque("Paquetes", 2, f.paquetes.map((p) => `<div>${esc(p.contenido)} <span class="tenue">· ${esc(p.peso_kg)} kg${p.fragil ? " · frágil" : ""}</span></div>`).join(""))}
          ${bloque("Cliente", 3, `<div>${esc(f.cliente.nombre)}</div><div class="tenue">${esc(f.cliente.email)}</div>`)}
        </div>
        <div id="error-registro" style="margin-top:14px"></div>`;
    },
  ];
  const paso = $("#paso");
  paso.innerHTML = cuerpos[fm.paso]();
  reiniciarAnim(paso, "paso-anim");
  $("#atras").style.visibility = fm.paso ? "visible" : "hidden";
  $("#seguir").innerHTML = fm.paso === 4 ? `${ic("check")}Registrar envío` : `Continuar${ic("derecha")}`;
  $("#agregar")?.addEventListener("click", () => { f.paquetes.push(paqueteVacio()); pintarPaso(); cotizar(); });
  $$("[data-quitar]").forEach((b) => b.onclick = () => { f.paquetes.splice(Number(b.dataset.quitar), 1); pintarPaso(); cotizar(); });
  $$("[data-ir]").forEach((b) => b.onclick = () => irPaso(Number(b.dataset.ir)));
  pintarResumen();
}

function leerCampo(ev) {
  const fm = estado.form, f = fm.datos, t = ev.target;
  if (t.dataset.c) {
    const caja = t.closest(".paquete"), p = f.paquetes[Number(caja.dataset.i)];
    p[t.dataset.c] = t.type === "checkbox" ? t.checked : t.value;
    const vistaCaja = $(".vista-caja", caja), nueva = cajaIso(p);
    if (vistaCaja.dataset.dibujo !== nueva) {
      vistaCaja.dataset.dibujo = nueva;
      vistaCaja.innerHTML = nueva;
      reiniciarAnim(vistaCaja, "pop");
    }
  } else if (t.name?.startsWith("c_")) {
    f.cliente[t.name.slice(2)] = t.value;
  } else if (t.name) {
    f[t.name] = t.type === "checkbox" ? t.checked : t.value;
  }
  if (fm.intentado) {  // después del primer intento, los errores se corrigen al escribir
    fm.errores = validar(fm.paso);
    $$(".error-campo", $("#paso")).forEach((e) => { if (!fm.errores[e.id.slice(4)]) e.remove(); });
    $$("[aria-invalid=true]", $("#paso")).forEach((i) => { const k = i.getAttribute("aria-describedby")?.slice(4); if (k && !fm.errores[k]) i.removeAttribute("aria-invalid"); });
  }
  pintarResumen();
  if (t.name?.startsWith("c_")) return;  // los datos del cliente no cambian el costo
  clearTimeout(leerCampo.espera);
  leerCampo.espera = setTimeout(cotizar, 250);
}

function validar(paso) {
  const f = estado.form.datos, e = {};
  if (paso === 1) {
    if (!f.direccion_destino.trim()) e.direccion_destino = "Escriba la dirección de destino.";
    if (f.tipo === "internacional" && !f.pais_destino.trim()) e.pais_destino = "Escriba el país de destino.";
  }
  if (paso === 2) {
    f.paquetes.forEach((p, i) => {
      if (!p.contenido.trim()) e[`p${i}_contenido`] = "Describa el contenido.";
      if (!(Number(p.peso_kg) > 0)) e[`p${i}_peso_kg`] = "Escriba un peso mayor que 0.";
      if (!["alto_cm", "ancho_cm", "largo_cm"].every((c) => Number(p[c]) > 0)) e[`p${i}_medidas`] = "Escriba alto, ancho y largo en centímetros.";
      if (f.tipo === "internacional" && !(Number(p.valor_declarado) > 0)) e[`p${i}_valor_declarado`] = "Los internacionales exigen valor declarado.";
    });
  }
  if (paso === 3) {
    if (!f.cliente.nombre.trim()) e.c_nombre = "Escriba el nombre del cliente.";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.cliente.email.trim())) e.c_email = "Escriba un correo válido, como ana@correo.hn.";
  }
  return e;
}

async function seguir() {
  const fm = estado.form;
  if (fm.paso === 4) { registrar(); return; }
  fm.errores = validar(fm.paso);
  if (fm.paso === 2 && !Object.keys(fm.errores).length) {
    await cotizar();
    if (fm.errorCot) { pintarPaso(); return; }
  }
  if (Object.keys(fm.errores).length) {
    fm.intentado = true;
    pintarPaso();
    $("#paso [aria-invalid=true]")?.focus();
    return;
  }
  fm.paso += 1;
  fm.maximo = Math.max(fm.maximo, fm.paso);
  fm.intentado = false;
  pintarPaso();
  $("#paso").querySelector("input, select, button")?.focus({ preventScroll: true });
  if (innerWidth < 1100) $("#form").scrollIntoView({ behavior: sinMovimiento() ? "auto" : "smooth", block: "start" });
}

function pintarResumen() {
  const f = estado.form?.datos;
  if (!f || !$("#lineas-resumen")) return;
  const s = estado.catalogo.sucursales.find((x) => String(x.id) === String(f.sucursal_origen));
  const destino = f.tipo === "internacional" ? f.pais_destino : f.direccion_destino.split(",").pop().trim();
  const peso = f.paquetes.reduce((t, p) => t + (Number(p.peso_kg) || 0), 0);
  $("#lineas-resumen").innerHTML = [
    ["Servicio", NOMBRE_TIPO[f.tipo]], ["Ruta", `${s?.ciudad || ""} → ${destino || "…"}`],
    ["Paquetes", `${f.paquetes.length} · ${peso ? peso.toLocaleString("es-HN") + " kg" : "sin peso"}`],
  ].map(([k, v]) => `<div class="linea-resumen"><span>${k}</span><b>${esc(v)}</b></div>`).join("");
  mapaCotizacion();
}

/** Dibujo de la caja en perspectiva, con sus proporciones reales. */
function cajaIso(p) {
  const n = (v, d) => Number(v) > 0 ? Number(v) : d;
  const completo = paqueteCompleto(p);
  const a = n(p.largo_cm, 40), b = n(p.ancho_cm, 30), c = n(p.alto_cm, 20);
  const s = 46 / Math.max(a, b, c);
  const O = [70, 116], X = [0.866, -0.5], Y = [-0.866, -0.5];
  const mas = (P, V, k) => [P[0] + V[0] * k, P[1] + V[1] * k];
  const sube = (P) => [P[0], P[1] - c * s];
  const Gx = mas(O, X, a * s), Gy = mas(O, Y, b * s), Gxy = mas(Gx, Y, b * s);
  const pts = (...ps) => ps.map((q) => q.map((v) => v.toFixed(1)).join(",")).join(" ");
  const cinta1 = sube(mas(O, Y, b * s / 2)), cinta2 = mas(cinta1, X, a * s);
  const peso = Number(p.peso_kg) > 0 ? `${p.peso_kg} kg` : "";
  return `<svg viewBox="0 0 140 130" class="${completo ? "" : "fantasma"}">
    <ellipse cx="70" cy="${(O[1] + 4).toFixed(1)}" rx="${(0.866 * (a + b) * s / 2 + 6).toFixed(1)}" ry="6" class="sombra-caja"/>
    <polygon points="${pts(O, Gy, sube(Gy), sube(O))}" class="cara izq"/>
    <polygon points="${pts(O, Gx, sube(Gx), sube(O))}" class="cara der"/>
    <polygon points="${pts(sube(O), sube(Gx), sube(Gxy), sube(Gy))}" class="cara arriba"/>
    <line x1="${cinta1[0].toFixed(1)}" y1="${cinta1[1].toFixed(1)}" x2="${cinta2[0].toFixed(1)}" y2="${cinta2[1].toFixed(1)}" class="cinta"/>
    ${p.fragil ? `<g class="sello-fragil" transform="translate(${((O[0] + Gx[0]) / 2).toFixed(1)} ${((O[1] + Gx[1]) / 2 - c * s / 2).toFixed(1)}) skewY(-30)"><rect x="-17" y="-6" width="34" height="12" rx="2"/><text y="3.5" text-anchor="middle">FRÁGIL</text></g>` : ""}
    <text x="70" y="128" text-anchor="middle" class="peso-caja">${completo ? esc(peso) : "Escriba las medidas"}</text>
  </svg>`;
}

function mapaCotizacion() {
  const f = estado.form.datos, caja = $("#mapa-cotizacion");
  if (!caja) return;
  const sucursal = estado.catalogo.sucursales.find((x) => String(x.id) === String(f.sucursal_origen));
  const envio = { guia: "cotizacion", tipo: f.tipo, estado: "En tránsito", origen: sucursal?.ciudad,
    destino: f.direccion_destino, pais_destino: f.pais_destino || "Estados Unidos" };
  const firma = [envio.tipo, envio.origen, envio.destino, envio.pais_destino].join("|");
  if (firma === caja.dataset.firma) return;
  caja.dataset.firma = firma;
  Mapa.red(caja, [envio]);
}

const cuerpoEnvio = () => {
  const f = estado.form.datos;
  return { ...f, paquetes: f.paquetes.map((p) => ({ ...p, contenido: p.contenido || "Sin describir" })) };
};

async function cotizar() {
  const fm = estado.form;
  const caja = $("#cotizacion");
  if (!fm || !caja) return;
  if (!fm.datos.paquetes.some(paqueteCompleto)) {
    fm.errorCot = "";
    caja.innerHTML = `<p class="tenue" style="margin-top:8px">Escriba el peso y las medidas del paquete para ver el costo.</p>
      <div class="total"><span>Total</span><strong class="num total-cot" data-valor="0">L 0.00</strong></div>`;
    return;
  }
  const antes = new Set($$("tr[data-concepto]", caja).map((tr) => tr.dataset.concepto));
  const totalAntes = Number($(".total-cot", caja)?.dataset.valor || 0);
  try {
    const c = await api("/api/cotizar", { method: "POST", body: cuerpoEnvio() });
    fm.cot = c;
    fm.errorCot = "";
    caja.innerHTML = desglose(c, antes) + `<p class="tenue" style="margin-top:4px">Peso facturable: ${esc(c.peso_facturable_kg)} kg</p>`;
    const total = $(".total-cot", caja);
    total.dataset.valor = totalAntes;
    contar(total, Number(c.total), lempiras);
  } catch (e) {
    fm.errorCot = e.message;
    caja.innerHTML = `<div class="error-form" style="margin-top:10px">${ic("alerta")}<span>${esc(e.message)}</span></div>`;
  }
}

async function registrar() {
  const boton = $("#seguir");
  boton.disabled = true;
  boton.innerHTML = "Registrando…";
  try {
    const envio = await api("/api/envios", { method: "POST", body: estado.form.datos });
    estado.form = null;
    cargarEnvios();
    verExito(envio);
  } catch (e) {
    $("#error-registro").innerHTML = `<div class="error-form">${ic("alerta")}<span>${esc(e.message)}</span></div>`;
    boton.disabled = false;
    boton.innerHTML = `${ic("check")}Registrar envío`;
  }
}

// ---------- Etiqueta con código de barras Code 39 ----------
const CODE39 = {
  "0": "000110100", "1": "100100001", "2": "001100001", "3": "101100000", "4": "000110001", "5": "100110000",
  "6": "001110000", "7": "000100101", "8": "100100100", "9": "001100100", "A": "100001001", "B": "001001001",
  "C": "101001000", "D": "000011001", "E": "100011000", "F": "001011000", "G": "000001101", "H": "100001100",
  "I": "001001100", "J": "000011100", "K": "100000011", "L": "001000011", "M": "101000010", "N": "000010011",
  "O": "100010010", "P": "001010010", "Q": "000000111", "R": "100000110", "S": "001000110", "T": "000010110",
  "U": "110000001", "V": "011000001", "W": "111000000", "X": "010010001", "Y": "110010000", "Z": "011010000",
  "-": "010000101", "*": "010010100",
};

function codigoBarras(texto) {
  const angosta = 1, ancha = 2.5;
  let x = 10;
  const barras = [];
  for (const ch of `*${texto}*`) {
    const patron = CODE39[ch];
    if (!patron) continue;
    [...patron].forEach((b, i) => {
      const w = b === "1" ? ancha : angosta;
      if (i % 2 === 0) barras.push(`<rect x="${x.toFixed(1)}" y="0" width="${w}" height="50"/>`);
      x += w;
    });
    x += angosta;  // espacio entre caracteres
  }
  return `<svg class="barras" viewBox="0 0 ${(x + 9).toFixed(1)} 50" preserveAspectRatio="none" role="img" aria-label="Código de barras de ${esc(texto)}"><g fill="#111">${barras.join("")}</g></svg>`;
}

function etiqueta(d) {
  const destino = d.tipo === "internacional" ? `${d.destino}, ${d.pais_destino}` : d.destino;
  return `<div class="etiqueta">
    <div class="et-cab"><strong>zyntra</strong><span class="et-tipo">${esc(d.tipo)}</span></div>
    <div class="et-partes">
      <div><small>Remite</small><b>${esc(d.sucursal_origen)}</b></div>
      <div><small>Destino</small><b>${esc(destino)}</b></div>
      <div><small>Cliente</small><b>${esc(d.cliente.nombre)}</b></div>
      <div><small>Peso facturable</small><b>${esc(d.costo.peso_facturable_kg)} kg · ${d.paquetes.length} paq.</b></div>
    </div>
    ${codigoBarras(d.guia)}
    <div class="et-guia">${esc(d.guia)}</div>
    <div class="et-pie"><span>${fecha(d.creado)}</span><span>${lempiras(d.costo.total)}</span></div>
  </div>`;
}

function verExito(d) {
  reiniciarAnim(vista, "entrando");
  vista.innerHTML = `
    <div class="exito">
      <div>
        <div class="sello">${ic("check")}</div>
        <h1>Envío registrado</h1>
        <p>La guía <b class="guia">${esc(d.guia)}</b> ya está en el sistema y ${esc(d.cliente.nombre)} recibió el primer correo. Imprima la etiqueta y péguela en el paquete.</p>
        <div class="acciones">
          <button type="button" id="imprimir">${ic("imprimir")}Imprimir etiqueta</button>
          <a class="boton secundario" href="#/envios/${esc(d.guia)}">${ic("ojo")}Ver envío</a>
          <button type="button" class="fantasma-btn" id="otro">${ic("mas")}Registrar otro</button>
        </div>
      </div>
      ${etiqueta(d)}
    </div>`;
  festejar();
  $("#imprimir").onclick = () => { $("#imprimible").innerHTML = etiqueta(d); window.print(); };
  $("#otro").onclick = () => verNuevo();
  $("#imprimir").focus();
}

// =========================================================
// Rastrear (vista del cliente)
// =========================================================
function verRastrear(guia) {
  const recientes = [...estado.envios].filter(activo).slice(0, 3).map((e) => e.guia);
  vista.innerHTML = `
    <section class="portada-rastreo">
      <div class="estrellas" aria-hidden="true">${'<svg viewBox="0 0 20 20"><use href="#estrella"/></svg>'.repeat(5)}</div>
      <h1>¿Dónde está mi paquete?</h1>
      <p>Escriba su número de guía. La página se actualiza sola cada vez que su envío avanza.</p>
      <form class="buscador" id="buscar"><label class="sr" for="buscar-guia">Número de guía</label>
        <input type="search" id="buscar-guia" name="guia" placeholder="Ejemplo: ZYN-00000001" value="${esc(guia || "")}" autocomplete="off">
        <button>${ic("buscar")}Rastrear</button></form>
      ${recientes.length ? `<div class="sugerencias">Pruebe con: ${recientes.map((g) => `<button type="button" data-g="${g}">${g}</button>`).join("")}</div>` : ""}
    </section>
    <div id="resultado"></div>`;
  $$(".sugerencias button").forEach((b) => b.onclick = () => location.hash = "#/rastrear/" + b.dataset.g);
  $("#buscar").onsubmit = (ev) => {
    ev.preventDefault();
    const g = ev.target.guia.value.trim().toUpperCase();
    if (g) location.hash = "#/rastrear/" + g;
  };
  pintarRastreo(guia);
}

async function pintarRastreo(guia, animar = false) {
  const caja = $("#resultado");
  estado.guiaRastreo = guia;
  if (!guia) {
    caja.innerHTML = `<section class="tarjeta">${vacio("Su número de guía aparece en la etiqueta del paquete y en el correo de confirmación.")}</section>`;
    return;
  }
  if (!animar) caja.innerHTML = `<div class="esqueleto" style="height:360px"></div>`;
  try {
    const d = await api("/api/envios/" + encodeURIComponent(guia));
    if (estado.guiaRastreo !== guia) return;
    const destino = d.tipo === "internacional" ? `${d.destino}, ${d.pais_destino}` : d.destino;
    const ultimo = d.rastreo[d.rastreo.length - 1];
    caja.innerHTML = `
      <section class="tarjeta mb">
        <div class="cabecera-envio">
          <div class="con-icono"><span class="burbuja-grande">${vehiculo(d.tipo, "xl")}</span>
            <div><div class="tipo-chip">Envío ${esc(d.tipo)}</div><div class="guia-grande guia">${esc(d.guia)}</div><div class="ruta">${esc(d.sucursal_origen)} → ${esc(destino)}</div></div></div>
          <div style="text-align:right">${insignia(d.estado)}<div class="tenue" style="margin-top:6px">${esc(ultimo.descripcion)} · ${hace(ultimo.hora)}</div></div>
        </div>
        <div class="cuerpo" style="padding-top:0"><div class="caja-mapa" id="mapa-ruta"></div><div style="margin-top:18px">${progreso(d)}</div></div>
      </section>
      <div class="rejilla col-1-1">
        <section class="tarjeta"><div class="cab"><h2>Historial</h2></div><div class="cuerpo">${lineaTiempo(d, animar)}</div></section>
        <section class="tarjeta"><div class="cab"><h2>Correos que recibió</h2>${patron("Observer")}</div><div class="cuerpo">${mensajes(d)}</div></section>
      </div>`;
    Mapa.ruta($("#mapa-ruta"), d);
  } catch (e) {
    caja.innerHTML = `<section class="tarjeta">${vacio(`No encontramos la guía <b>${esc(guia)}</b>. Revise que esté bien escrita, por ejemplo ZYN-00000001.`)}</section>`;
  }
}

// =========================================================
// Sistema: salud del bus de eventos
// =========================================================
const METRICAS = [
  ["entregados", "Avisos entregados", "check"], ["reintentos", "Reintentos", "refrescar"],
  ["en_cola_fallidos", "En cola de fallidos", "alerta"], ["rechazados_por_circuito", "Rechazados por circuito", "x"],
  ["latencia_promedio_ms", "Latencia promedio", "reloj"], ["latencia_p95_ms", "Latencia p95", "reloj"],
  ["latencia_max_ms", "Latencia máxima", "reloj"], ["pantallas", "Pantallas conectadas", "ojo"],
];

async function verSistema() {
  vista.innerHTML = `
    <div class="encabezado"><div><h1>Sistema</h1><p>Salud del bus de eventos que entrega los avisos en tiempo real.</p></div>${patron("Observer + Circuit breaker")}</div>
    <section class="tarjeta mb">
      <div class="estado-salud" id="salud"><div class="esqueleto" style="width:48px;height:48px"></div></div>
      <div class="simulador"><div><strong>Simular caída del servicio de SMS</strong>
        <p>Apáguelo y mueva un envío: verá los reintentos, la cola de fallidos y cómo se abre el circuito tras 5 fallos seguidos, sin que el correo ni esta pantalla dejen de funcionar.</p></div>
        <label class="interruptor"><input type="checkbox" id="tirar-sms"><span></span><b id="texto-sms">SMS en línea</b></label></div>
    </section>
    <div class="rejilla metricas mb">${METRICAS.map(([id, etq, icono]) => `
      <div class="tarjeta kpi"><div class="etq"><span class="ico-kpi">${ic(icono)}</span>${etq}</div><div class="valor num" id="m-${id}">—</div></div>`).join("")}</div>
    <div class="rejilla col-2-1 mb">
      <section class="tarjeta">
        <div class="cab"><div><h2>Latencia de entrega</h2><p>Milisegundos desde el cambio de estado hasta el aviso, en vivo</p></div>
          <div class="leyenda"><span><i class="punto-tipo" style="background:var(--marca)"></i>Promedio</span><span><i class="punto-tipo" style="background:var(--c-express)"></i>p95</span></div></div>
        <div class="cuerpo" id="grafica-latencia"></div>
      </section>
      <section class="tarjeta">
        <div class="cab"><div><h2>Suscriptores del bus</h2><p>Cada uno con su propio circuito</p></div></div>
        <div class="envoltura-tabla" style="margin-top:12px" id="suscriptores"></div>
        <div class="cuerpo"><div class="explica">Circuito <b>cerrado</b>: se le llama normal. <b>Abierto</b>: tras 5 fallos seguidos no se le llama por 15 s. <b>Semiabierto</b>: se prueba una llamada.</div></div>
      </section>
    </div>
    <section class="tarjeta">
      <div class="cab"><div><h2>Avisos fallidos</h2><p>Esperan aquí hasta que el servicio vuelva</p></div><button class="secundario chico" id="reprocesar" disabled>${ic("refrescar")}Reprocesar</button></div>
      <div id="fallidos" style="margin-top:12px"></div>
    </section>`;
  $("#tirar-sms").onchange = async (ev) => {
    try { pintarSistema(await api("/api/sistema/sms", { method: "POST", body: { caido: ev.target.checked } })); }
    catch (e) { aviso("No se pudo cambiar", e.message, "error"); }
    aviso(ev.target.checked ? "SMS apagado" : "SMS en línea", ev.target.checked ? "Mueva un envío para ver los reintentos." : "Los avisos nuevos vuelven a entregarse.", ev.target.checked ? "error" : "exito");
  };
  $("#reprocesar").onclick = async () => {
    const r = await api("/api/sistema/reprocesar", { method: "POST" });
    aviso("Cola reprocesada", `${r.reprocesados} aviso(s) entregado(s).`, "exito");
    pintarSistema(r);
  };
  const grafica = $("#grafica-latencia");
  grafica.addEventListener("mousemove", (ev) => { estado.punteroLat = ev; cursorLatencia(); });
  grafica.addEventListener("mouseleave", () => { estado.punteroLat = null; cursorLatencia(); });
  const sondear = async () => { try { pintarSistema(await api("/api/sistema")); } catch {} };
  await sondear();
  estado.temporizador = setInterval(sondear, 1500);
}

function pintarSistema(s) {
  if (!$("#salud")) return;
  const st = s.estadisticas, ok = s.salud.estado === "ok";
  $("#salud").innerHTML = `<div class="semaforo ${ok ? "ok" : "degradado"}">${ic(ok ? "check" : "alerta")}</div>
    <div><strong>${ok ? "Todo funciona" : "Servicio degradado"}</strong>
    <span>${ok ? "Todos los suscriptores responden. Los avisos se entregan al momento." : "Un servicio no responde. Su circuito está abierto y sus avisos esperan en la cola de fallidos; los demás siguen funcionando."}</span></div>`;
  $("#tirar-sms").checked = s.sms_caido;
  $("#texto-sms").textContent = s.sms_caido ? "SMS caído" : "SMS en línea";
  const valores = { ...st, pantallas: s.pantallas };
  for (const [id] of METRICAS) {
    const v = valores[id], nodo = $(`#m-${id}`);
    if (v === null || v === undefined) { nodo.textContent = "—"; continue; }
    contar(nodo, Number(v), id.startsWith("latencia") ? (n) => `${n.toFixed(1)} ms` : entero);
  }
  const subs = Object.entries(s.salud.suscriptores);
  $("#suscriptores").innerHTML = `<table class="tabla"><thead><tr><th>Servicio</th><th>Circuito</th></tr></thead><tbody>${subs.map(([n, x]) =>
    `<tr style="cursor:default"><td>${esc(n)}<div class="tenue">${x.fallos_seguidos} fallos seguidos · ${x.aperturas} aperturas</div></td><td><span class="pastilla ${esc(x.circuito)}">${esc(x.circuito)}</span></td></tr>`).join("")}</tbody></table>`;
  $("#reprocesar").disabled = !st.en_cola_fallidos;
  $("#fallidos").innerHTML = s.fallidos.length ? `<div class="envoltura-tabla"><table class="tabla"><thead><tr><th>Guía</th><th>Servicio</th><th class="ocultar-movil">Motivo</th><th class="der">Intentos</th></tr></thead><tbody>
    ${[...s.fallidos].reverse().map((f) => `<tr style="cursor:default"><td><span class="guia">${esc(f.guia)}</span><div class="tenue">${esc(f.estado)}</div></td><td>${esc(f.suscriptor)}</td><td class="ocultar-movil tenue">${esc(f.motivo)}</td><td class="der num">${f.intentos}</td></tr>`).join("")}
    </tbody></table></div>` : `<div class="cuerpo">${vacio("No hay avisos fallidos. Apague el SMS y mueva un envío para ver esta cola en acción.")}</div>`;

  if (st.latencia_promedio_ms !== null && st.latencia_promedio_ms !== undefined) {
    estado.latencias.push({ t: new Date(), prom: Number(st.latencia_promedio_ms), p95: Number(st.latencia_p95_ms ?? st.latencia_promedio_ms) });
    if (estado.latencias.length > 40) estado.latencias.shift();
  }
  graficaLatencia();
}

const GL = { W: 640, H: 220, L: 40, R: 10, T: 14, B: 26 };
function graficaLatencia() {
  const caja = $("#grafica-latencia");
  if (!caja) return;
  const datos = estado.latencias;
  if (datos.length < 2) {
    caja.innerHTML = vacio("Aún no hay mediciones. Mueva un envío o simule un recorrido y la línea aparecerá aquí.");
    return;
  }
  const { W, H, L, R, T, B } = GL;
  const max = Math.max(1, Math.ceil(Math.max(...datos.map((d) => d.p95)) * 1.25));
  const x = (i) => L + (W - L - R) * (i / 39);
  const y = (v) => T + (H - T - B) * (1 - v / max);
  const linea = (k) => datos.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(d[k]).toFixed(1)}`).join("");
  const guias = [0, max / 2, max].map((v) => `<line class="${v ? "linea-guia" : "base"}" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text class="eje" x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${+v.toFixed(1)}</text>`).join("");
  const ultimo = datos[datos.length - 1], n = datos.length - 1;
  caja.innerHTML = `<svg class="grafica" viewBox="0 0 ${W} ${H}" role="img" aria-label="Latencia promedio ${ultimo.prom.toFixed(1)} ms, p95 ${ultimo.p95.toFixed(1)} ms">
    ${guias}<text class="eje" x="${L}" y="${H - 6}">hace 1 min</text><text class="eje" x="${W - R}" y="${H - 6}" text-anchor="end">ahora</text>
    <path class="area" d="${linea("prom")}L${x(n)} ${y(0)}L${x(0)} ${y(0)}Z"/>
    <path class="serie p95" d="${linea("p95")}"/><path class="serie promedio" d="${linea("prom")}"/>
    <circle class="marcador" cx="${x(n)}" cy="${y(ultimo.p95)}" r="4" fill="var(--c-express)"/><circle class="marcador" cx="${x(n)}" cy="${y(ultimo.prom)}" r="4" fill="var(--marca)"/>
    <g id="cursor-lat"></g></svg>`;
  caja.dataset.max = max;
  cursorLatencia();
}

function cursorLatencia() {
  const g = $("#cursor-lat"), svg = g?.ownerSVGElement, datos = estado.latencias, ev = estado.punteroLat;
  if (!g) return;
  if (!ev) { g.innerHTML = ""; ocultarTT(); return; }
  const { W, H, L, R, T, B } = GL, max = Number($("#grafica-latencia").dataset.max);
  const r = svg.getBoundingClientRect();
  const px = (ev.clientX - r.left) * (W / r.width);
  const i = Math.max(0, Math.min(datos.length - 1, Math.round((px - L) / ((W - L - R) / 39))));
  const d = datos[i], cx = L + (W - L - R) * (i / 39), y = (v) => T + (H - T - B) * (1 - v / max);
  g.innerHTML = `<line class="cursor" x1="${cx}" x2="${cx}" y1="${T}" y2="${H - B}"/>
    <circle class="marcador" cx="${cx}" cy="${y(d.p95)}" r="5" fill="var(--c-express)"/><circle class="marcador" cx="${cx}" cy="${y(d.prom)}" r="5" fill="var(--marca)"/>`;
  mostrarTT(`<strong>${d.t.toLocaleTimeString("es-HN")}</strong><div class="fila-tt"><i class="punto-tipo" style="background:var(--marca)"></i>Promedio<b>${d.prom.toFixed(1)} ms</b></div><div class="fila-tt"><i class="punto-tipo" style="background:var(--c-express)"></i>p95<b>${d.p95.toFixed(1)} ms</b></div>`, ev.clientX, ev.clientY);
}

// =========================================================
// Buscador rápido (Ctrl K)
// =========================================================
const paleta = $("#paleta");
let opcionesPaleta = [], elegida = 0, focoAntesPaleta = null;

function accionesPaleta() {
  return [
    { texto: "Ir al panel", icono: "panel", hacer: () => location.hash = "#/panel" },
    { texto: "Ver todos los envíos", icono: "caja", hacer: () => location.hash = "#/envios" },
    { texto: "Registrar un envío nuevo", icono: "mas", hacer: () => location.hash = "#/nuevo" },
    { texto: "Rastrear un envío", icono: "pin", hacer: () => location.hash = "#/rastrear" },
    { texto: "Ver la salud del sistema", icono: "pulso", hacer: () => location.hash = "#/sistema" },
    { texto: document.documentElement.dataset.theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro", icono: document.documentElement.dataset.theme === "dark" ? "sol" : "luna", hacer: cambiarTema },
    { texto: $("#modo-patrones").checked ? "Ocultar los patrones de diseño" : "Mostrar los patrones de diseño", icono: "ojo", hacer: () => cambiarPatrones(!$("#modo-patrones").checked) },
  ];
}

function abrirPaleta() {
  focoAntesPaleta = document.activeElement;
  paleta.hidden = false;
  paleta.innerHTML = `<div class="caja">
    <div class="entrada">${ic("buscar")}<input type="text" id="texto-paleta" placeholder="Escriba una guía, un cliente o una acción" aria-label="Buscar" role="combobox" aria-expanded="true" aria-controls="lista-paleta" autocomplete="off"><kbd>Esc</kbd></div>
    <ul id="lista-paleta" role="listbox" aria-label="Resultados"></ul>
    <div class="pie-paleta"><span><kbd>↑</kbd> <kbd>↓</kbd> moverse</span><span><kbd>Enter</kbd> abrir</span><span><kbd>Esc</kbd> cerrar</span></div></div>`;
  const entrada = $("#texto-paleta");
  entrada.addEventListener("input", () => { elegida = 0; pintarPaleta(entrada.value); });
  entrada.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      ev.preventDefault();
      elegida = (elegida + (ev.key === "ArrowDown" ? 1 : -1) + opcionesPaleta.length) % Math.max(1, opcionesPaleta.length);
      marcarPaleta();
    } else if (ev.key === "Enter") { ev.preventDefault(); ejecutarPaleta(elegida); }
  });
  paleta.addEventListener("mousedown", (ev) => { if (ev.target === paleta) cerrarPaleta(); });
  elegida = 0;
  pintarPaleta("");
  entrada.focus();
}

function cerrarPaleta() {
  if (paleta.hidden) return;
  paleta.hidden = true;
  paleta.innerHTML = "";
  focoAntesPaleta?.focus?.();
}

function pintarPaleta(q) {
  const t = q.trim().toLowerCase();
  const acciones = accionesPaleta().filter((a) => !t || a.texto.toLowerCase().includes(t));
  const envios = estado.envios.filter((x) => t && [x.guia, x.cliente_nombre, x.destino, x.pais_destino].some((v) => String(v).toLowerCase().includes(t))).slice(0, 6)
    .map((x) => ({ texto: `${x.guia} · ${x.cliente_nombre}`, envio: x, hacer: () => location.hash = "#/envios/" + x.guia }));
  opcionesPaleta = [...envios, ...acciones];
  let i = 0;
  const op = (o) => `<li role="option" id="op-${i}" data-i="${i++}">${o.envio ? vehiculo(o.envio.tipo) : ic(o.icono)}<span>${esc(o.texto)}</span>${o.envio ? `<span class="tenue">${esc(o.envio.estado)}</span>` : ""}</li>`;
  $("#lista-paleta").innerHTML = (envios.length ? `<li class="titulo-grupo" role="presentation">Envíos</li>${envios.map(op).join("")}` : "")
    + (acciones.length ? `<li class="titulo-grupo" role="presentation">Acciones</li>${acciones.map(op).join("")}` : "")
    + (opcionesPaleta.length ? "" : `<li role="presentation">${vacio(`Nada coincide con «${esc(q)}».`)}</li>`);
  $$("#lista-paleta [role=option]").forEach((li) => {
    li.onmousemove = () => { if (elegida !== Number(li.dataset.i)) { elegida = Number(li.dataset.i); marcarPaleta(); } };
    li.onclick = () => ejecutarPaleta(Number(li.dataset.i));
  });
  marcarPaleta();
}

function marcarPaleta() {
  $$("#lista-paleta [role=option]").forEach((li) => li.setAttribute("aria-selected", Number(li.dataset.i) === elegida));
  const sel = $(`#op-${elegida}`);
  sel?.scrollIntoView({ block: "nearest" });
  $("#texto-paleta")?.setAttribute("aria-activedescendant", sel ? sel.id : "");
}

function ejecutarPaleta(i) {
  const o = opcionesPaleta[i];
  if (!o) return;
  focoAntesPaleta = null;
  cerrarPaleta();
  o.hacer();
}

// =========================================================
// Campana de movimientos
// =========================================================
function abrirAvisos() {
  const panel = $("#panel-avisos");
  panel.hidden = false;
  $("#abrir-avisos").setAttribute("aria-expanded", "true");
  panel.innerHTML = `<div class="cab-menu"><h2>Movimientos recientes</h2><span class="tenue">${estado.feed.length ? "En esta sesión" : "Últimos conocidos"}</span></div><ul class="feed"></ul>`;
  estado.noLeidos = 0;
  pintarNoLeidos();
  pintarFeed();
}
function cerrarAvisos() {
  $("#panel-avisos").hidden = true;
  $("#abrir-avisos").setAttribute("aria-expanded", "false");
}
function pintarNoLeidos() {
  const c = $("#no-leidos");
  c.hidden = !estado.noLeidos;
  c.textContent = estado.noLeidos > 9 ? "9+" : estado.noLeidos;
  $("#abrir-avisos").setAttribute("aria-label", estado.noLeidos ? `Movimientos recientes, ${estado.noLeidos} sin ver` : "Movimientos recientes");
}

// =========================================================
// Tiempo real (WebSocket)
// =========================================================
function conectar() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  const ind = $("#conexion");
  ws.onopen = () => { estado.wsViva = true; ind.className = "en-vivo viva"; ind.lastElementChild.textContent = "En vivo"; };
  ws.onclose = () => {
    estado.wsViva = false;
    ind.className = "en-vivo caida"; ind.lastElementChild.textContent = "Reconectando";
    setTimeout(conectar, 2000);
  };
  ws.onmessage = async (msg) => {
    const ev = JSON.parse(msg.data);
    ev.tipo = estado.envios.find((x) => x.guia === ev.guia)?.tipo;
    estado.feed.unshift(ev);
    estado.feed.length = Math.min(estado.feed.length, 30);
    if ($("#panel-avisos").hidden) { estado.noLeidos += 1; pintarNoLeidos(); }
    pintarFeed(true);
    const abierto = estado.guiaCajon === ev.guia || estado.guiaRastreo === ev.guia;
    if (estado.guiaCajon === ev.guia) pintarCajon(ev.guia, true);
    if (estado.guiaRastreo === ev.guia && estado.vistaActual === "rastrear") pintarRastreo(ev.guia, true);
    if (abierto) {
      aviso(`${ev.guia}: ${ev.nuevo}`, ev.descripcion, ev.nuevo === "Entregado" ? "exito" : "");
      if (ev.nuevo === "Entregado") setTimeout(festejar, 1200);  // cuando el vehículo llega
    }
    await cargarEnvios().catch(() => {});
    $(`#lista tr[data-guia="${ev.guia}"], #recientes tr[data-guia="${ev.guia}"]`)?.classList.add("destello");
  };
}

// =========================================================
// Teclado y arranque
// =========================================================
document.addEventListener("keydown", (ev) => {
  if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k") {
    ev.preventDefault();
    if (paleta.hidden) abrirPaleta(); else cerrarPaleta();
    return;
  }
  if (ev.key === "Escape") {
    if (!paleta.hidden) { cerrarPaleta(); return; }
    if (!$("#panel-avisos").hidden) { cerrarAvisos(); $("#abrir-avisos").focus(); return; }
    if (estado.guiaCajon) { cerrarCajon(); return; }
    $("#app").classList.remove("menu-abierto");
  }
  if (ev.key === "Tab" && !paleta.hidden) { ev.preventDefault(); $("#texto-paleta")?.focus(); return; }
  if (ev.key === "Tab" && estado.guiaCajon) {  // el foco no sale del cajón mientras está abierto
    const enfocables = $$("#cajon button:not(:disabled), #cajon a[href], #cajon [tabindex='0']");
    if (!enfocables.length) return;
    const primero = enfocables[0], ultimo = enfocables[enfocables.length - 1];
    if (!$("#cajon").contains(document.activeElement)) { ev.preventDefault(); primero.focus(); }
    else if (ev.shiftKey && document.activeElement === primero) { ev.preventDefault(); ultimo.focus(); }
    else if (!ev.shiftKey && document.activeElement === ultimo) { ev.preventDefault(); primero.focus(); }
  }
});

document.addEventListener("click", (ev) => {
  const campana = $(".campana");
  if (!$("#panel-avisos").hidden && !campana.contains(ev.target)) cerrarAvisos();
  if ($("#app").classList.contains("menu-abierto") && !ev.target.closest("#lateral, #abrir-menu")) $("#app").classList.remove("menu-abierto");
});

$("#cortina").onclick = cerrarCajon;
$("#tema").onclick = cambiarTema;
$("#abrir-paleta").onclick = abrirPaleta;
$("#abrir-avisos").onclick = () => { if ($("#panel-avisos").hidden) abrirAvisos(); else cerrarAvisos(); };
$("#abrir-menu").onclick = () => $("#app").classList.toggle("menu-abierto");
$("#modo-patrones").onchange = (ev) => cambiarPatrones(ev.target.checked);
window.addEventListener("afterprint", () => { $("#imprimible").innerHTML = ""; });

(async () => {
  armarMenu();
  if (!document.documentElement.dataset.theme && window.matchMedia("(prefers-color-scheme: dark)").matches) document.documentElement.dataset.theme = "dark";
  pintarTema();
  try { if (localStorage.getItem("zyntra-patrones")) cambiarPatrones(true); } catch {}
  estado.catalogo = await api("/api/catalogo");
  estado.envios = await api("/api/envios").catch(() => []);
  pintarInsigniaMenu();
  conectar();
  ruta();
  setInterval(() => cargarEnvios().catch(() => {}), 5000);
})();
