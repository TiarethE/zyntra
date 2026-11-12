/* Mapa de Honduras con las rutas de Zyntra. SVG propio: no necesita internet. */
"use strict";

const Mapa = (() => {
  const NS = "http://www.w3.org/2000/svg";
  const ANCHO = 680, ALTO = 400;
  const pt = (lon, lat) => [(lon + 89.6) * 100, (16.75 - lat) * 100];
  const sinMovimiento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Contorno simplificado del país (lon, lat), de oeste a este por la costa norte.
  const CONTORNO = [
    [-89.35, 14.42], [-89.2, 14.85], [-88.95, 15.05], [-88.65, 15.35], [-88.2, 15.72],
    [-87.95, 15.85], [-87.6, 15.8], [-87.25, 15.75], [-86.8, 15.78], [-86.35, 15.8],
    [-86.0, 15.95], [-85.5, 15.97], [-84.9, 15.86], [-84.3, 15.83], [-83.75, 15.4],
    [-83.15, 15.0], [-83.6, 14.9], [-84.5, 14.6], [-85.15, 14.3], [-85.75, 13.95],
    [-86.1, 14.05], [-86.7, 13.75], [-86.8, 13.3], [-87.3, 12.98], [-87.6, 13.12],
    [-87.8, 13.4], [-88.4, 13.85], [-88.85, 14.1], [-89.15, 14.35],
  ];
  const ISLAS = [[-86.53, 16.35, 18, 4], [-86.9, 16.1, 7, 3], [-85.88, 16.46, 7, 3]];

  const CIUDADES = {
    "Tegucigalpa": { p: pt(-87.21, 14.07), claves: ["tegucigalpa", "comayagüela", "comayaguela", "kennedy"], sede: true },
    "San Pedro Sula": { p: pt(-88.03, 15.5), claves: ["san pedro"] },
    "La Ceiba": { p: pt(-86.79, 15.76), claves: ["ceiba"] },
    "Choluteca": { p: pt(-87.19, 13.3), claves: ["choluteca"] },
    "Comayagua": { p: pt(-87.64, 14.45), claves: ["comayagua "], menor: true },
    "Santa Rosa de Copán": { p: pt(-88.78, 14.77), claves: ["copán", "copan"], menor: true },
    "Juticalpa": { p: pt(-86.22, 14.66), claves: ["juticalpa", "olancho"], menor: true },
    "Danlí": { p: pt(-86.57, 14.03), claves: ["danlí", "danli"], menor: true },
    "Roatán": { p: pt(-86.53, 16.33), claves: ["roatán", "roatan"], menor: true },
  };
  // Hacia dónde sale del mapa un envío internacional.
  const SALIDAS = {
    norte: { p: [300, 14], texto: "Norteamérica y Europa", paises: ["estados unidos", "canadá", "canada", "españa", "espana", "méxico", "mexico"] },
    oeste: { p: [10, 190], texto: "Guatemala", paises: ["guatemala", "belice"] },
    suroeste: { p: [40, 360], texto: "El Salvador", paises: ["el salvador"] },
    sureste: { p: [640, 380], texto: "Nicaragua y Sudamérica", paises: [] },
  };

  function el(nombre, attrs = {}, hijos = []) {
    const n = document.createElementNS(NS, nombre);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    hijos.forEach((h) => n.append(h));
    return n;
  }

  function ciudadDe(texto, porDefecto) {
    const t = ` ${String(texto || "").toLowerCase()} `;
    for (const [nombre, c] of Object.entries(CIUDADES)) if (c.claves.some((k) => t.includes(k))) return nombre;
    return porDefecto;
  }

  function salidaDe(pais) {
    const t = String(pais || "").toLowerCase();
    for (const s of Object.values(SALIDAS)) if (s.paises.some((p) => t.includes(p))) return s;
    return SALIDAS.sureste;
  }

  /** Origen y destino de un envío en coordenadas del mapa. */
  function tramo(envio) {
    const origen = ciudadDe(envio.origen, "Tegucigalpa");
    if (envio.tipo === "internacional") {
      const s = salidaDe(envio.pais_destino);
      return { a: CIUDADES[origen].p, b: s.p, origen, destino: envio.pais_destino, salida: s };
    }
    let destino = ciudadDe(envio.destino, origen === "Tegucigalpa" ? "San Pedro Sula" : "Tegucigalpa");
    if (destino === origen) destino = origen === "Tegucigalpa" ? "San Pedro Sula" : "Tegucigalpa";
    return { a: CIUDADES[origen].p, b: CIUDADES[destino].p, origen, destino };
  }

  function curva([x1, y1], [x2, y2], k = 0.22) {
    const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, dx = x2 - x1, dy = y2 - y1;
    return `M${x1.toFixed(1)} ${y1.toFixed(1)} Q${(mx - dy * k).toFixed(1)} ${(my + dx * k).toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`;
  }

  function base(svg, conNombres = true) {
    svg.append(el("rect", { x: 0, y: 0, width: ANCHO, height: ALTO, class: "m-mar", rx: 14 }));
    // Líneas de latitud: dan sensación de carta náutica.
    for (let lat = 13; lat <= 16.5; lat += 0.5) {
      const y = pt(0, lat)[1];
      svg.append(el("line", { x1: 0, x2: ANCHO, y1: y, y2: y, class: "m-reticula" }));
    }
    const d = "M" + CONTORNO.map(([lo, la]) => pt(lo, la).map((n) => n.toFixed(1)).join(" ")).join("L") + "Z";
    svg.append(el("path", { d, class: "m-tierra" }));
    ISLAS.forEach(([lo, la, rx, ry]) => { const [x, y] = pt(lo, la); svg.append(el("ellipse", { cx: x, cy: y, rx, ry, class: "m-tierra", transform: `rotate(-12 ${x} ${y})` })); });
    for (const [nombre, c] of Object.entries(CIUDADES)) {
      const [x, y] = c.p;
      const g = el("g", { class: "m-ciudad" + (c.menor ? " menor" : "") + (c.sede ? " sede" : "") });
      g.append(el("circle", { cx: x, cy: y, r: c.menor ? 3 : 5 }));
      if (conNombres && !c.menor) {
        const t = el("text", { x: x + 9, y: y + 4 }); t.textContent = nombre; g.append(t);
      }
      svg.append(g);
    }
  }

  function vehiculo(tipo, tamano = 26) {
    const g = el("g", { class: `m-vehiculo ${tipo}` });
    const interior = el("g");
    interior.append(el("use", { href: `#v-${tipo}`, x: -tamano / 2, y: -tamano * 0.31, width: tamano, height: tamano * 0.625 }));
    g.append(interior);
    return { g, interior };
  }

  /** Mapa de toda la red: un vehículo recorre la ruta de cada envío activo. */
  function red(contenedor, envios) {
    const svg = el("svg", { viewBox: `0 0 ${ANCHO} ${ALTO}`, class: "mapa", role: "img", "aria-label": "Mapa de Honduras con los envíos en camino" });
    base(svg);
    const activos = envios.filter((e) => !["Entregado", "Cancelado"].includes(e.estado));
    const quieto = sinMovimiento();
    activos.forEach((e, i) => {
      const t = tramo(e);
      const id = `ruta-${e.guia}`;
      const ruta = el("path", { id, d: curva(t.a, t.b), class: `m-ruta ${e.tipo}`, pathLength: 100, style: `--retraso:${i * 120}ms` });
      svg.append(ruta);
      if (t.salida) {
        const [x, y] = t.salida.p;
        const tx = el("text", { x, y: y + (y < 50 ? 16 : -8), class: "m-salida", "text-anchor": x > ANCHO / 2 ? "end" : x < 60 ? "start" : "middle" });
        tx.textContent = t.salida.texto; svg.append(tx);
      }
      const { g, interior } = vehiculo(e.tipo);
      if (t.b[0] < t.a[0]) interior.setAttribute("transform", "scale(1,-1)");  // que no vaya de cabeza
      const titulo = el("title"); titulo.textContent = `${e.guia} · ${e.estado}`; g.append(titulo);
      g.dataset.guia = e.guia;
      if (quieto) {
        svg.append(g);
        requestAnimationFrame(() => colocar(g, interior, ruta, 0.5, t));
      } else {
        const dur = e.tipo === "express" ? 5 : e.tipo === "internacional" ? 9 : 7;
        const mov = el("animateMotion", { dur: `${dur}s`, repeatCount: "indefinite", rotate: "auto", begin: `${-(i * 1.7)}s` });
        mov.append(el("mpath", { href: `#${id}` }));
        g.append(mov);
        svg.append(g);
      }
    });
    contenedor.replaceChildren(svg);
    return svg;
  }

  function colocar(g, interior, ruta, fraccion, t) {
    const largo = ruta.getTotalLength();
    const p = ruta.getPointAtLength(largo * fraccion);
    const q = ruta.getPointAtLength(Math.min(largo, largo * fraccion + 1));
    const r = ruta.getPointAtLength(Math.max(0, largo * fraccion - 1));
    const ang = Math.atan2(q.y - r.y, q.x - r.x) * 180 / Math.PI;
    g.setAttribute("transform", `translate(${p.x.toFixed(1)} ${p.y.toFixed(1)}) rotate(${ang.toFixed(1)})`);
    interior.setAttribute("transform", Math.abs(ang) > 90 ? "scale(1,-1)" : "");
  }

  const AVANCE = {
    "Registrado": 0, "En tránsito": 0.45, "Retenido en aduana": 0.72,
    "En reparto": 0.86, "Entregado": 1, "Cancelado": 0,
  };
  const ultimo = new Map();  // guía → fracción mostrada la última vez

  /** Mapa de un solo envío. El vehículo avanza hasta donde va según su estado. */
  function ruta(contenedor, envio) {
    const svg = el("svg", { viewBox: envio.tipo === "internacional" ? `0 0 ${ANCHO} ${ALTO}` : `0 50 ${ANCHO} 345`, class: "mapa mapa-ruta", role: "img", "aria-label": `Ruta del envío ${envio.guia}` });
    base(svg, false);
    const t = tramo(envio);
    const d = curva(t.a, t.b);
    svg.append(el("path", { d, class: "m-ruta fondo" }));
    const hecho = el("path", { d, class: `m-ruta hecha ${envio.tipo}`, pathLength: 100 });
    svg.append(hecho);
    const etiqueta = (p, texto, clase) => {
      const [x, y] = p;
      const g = el("g", { class: "m-etiqueta " + clase });
      g.append(el("circle", { cx: x, cy: y, r: 7 }));
      const tx = el("text", { x: x > ANCHO - 160 ? x - 12 : x + 12, y: y < 40 ? y + 22 : y - 12, "text-anchor": x > ANCHO - 160 ? "end" : "start" });
      tx.textContent = texto; g.append(tx);
      svg.append(g);
    };
    etiqueta(t.a, t.origen, "origen");
    etiqueta(t.b, t.destino, "destino");
    const { g, interior } = vehiculo(envio.tipo, 38);
    svg.append(g);
    contenedor.replaceChildren(svg);

    const meta = AVANCE[envio.estado] ?? 0;
    const desde = ultimo.has(envio.guia) ? ultimo.get(envio.guia) : (sinMovimiento() ? meta : 0);
    ultimo.set(envio.guia, meta);
    const pintar = (f) => {
      colocar(g, interior, hecho, f, t);
      hecho.style.strokeDasharray = `${f * 100} 100`;
    };
    if (desde === meta || sinMovimiento()) { pintar(meta); return; }
    const inicio = performance.now(), dur = 1400;
    const paso = (ahora) => {
      const x = Math.min(1, (ahora - inicio) / dur);
      const suave = 1 - Math.pow(1 - x, 3);  // sale rápido y frena al llegar
      pintar(desde + (meta - desde) * suave);
      if (x < 1 && svg.isConnected) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  }

  return { red, ruta };
})();
