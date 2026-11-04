"""Genera el documento de diseño de Zyntra (HTML -> PDF) a partir del repositorio.

Las cifras (tarifas, desglose de costo, número de pruebas, historial) se leen
del código para que el documento no se desalinee.
Uso: python docs/documento/generar.py . docs/Zyntra_Documento_de_Diseno.pdf
Requiere Node.js con Playwright (Chromium) para convertir a PDF.
"""

import base64
import html
import inspect
import json
import subprocess
import sys
import textwrap
from decimal import Decimal
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
SALIDA = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(REPO))

from zyntra import costos, creadores, estados, eventos, gestor  # noqa: E402
from zyntra.dominio import Cliente, Paquete, Seguro, Sucursal  # noqa: E402
from zyntra.tarifas import TipoEnvio, cargar_tarifas  # noqa: E402

IMG = REPO / "docs" / "uml" / "img"


def img(nombre):
    datos = base64.b64encode((IMG / f"{nombre}.png").read_bytes()).decode()
    return f"data:image/png;base64,{datos}"


numero_figura = 0


def figura(nombre, pie, ancho="100%"):
    global numero_figura
    numero_figura += 1
    return (f'<figure><img src="{img(nombre)}" style="max-width:{ancho}">'
            f"<figcaption><b>Figura {numero_figura}.</b> {pie}</figcaption></figure>")


def codigo(obj, lineas=None):
    fuente = textwrap.dedent(inspect.getsource(obj))
    if lineas:
        fuente = "\n".join(fuente.splitlines()[lineas[0]:lineas[1]])
    return f"<pre><code>{html.escape(fuente.rstrip())}</code></pre>"


def ejecutar(*cmd):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True).stdout + \
        subprocess.run(cmd, cwd=REPO, capture_output=True, text=True).stderr


# ---- Datos tomados del código ----
tarifas = cargar_tarifas()
pruebas = subprocess.run([sys.executable, "-m", "unittest"], cwd=REPO,
                         capture_output=True, text=True).stderr
total_pruebas = next(l for l in pruebas.splitlines() if l.startswith("Ran")).split()[1]
assert pruebas.strip().endswith("OK"), pruebas
historial = subprocess.run(["git", "log", "--graph", "--format=%h %s", "main"], cwd=REPO,
                           capture_output=True, text=True).stdout

sucursal = Sucursal(id_punto=1, nombre="Zyntra Tegucigalpa Centro", direccion="Av. Cervantes",
                    ciudad="Tegucigalpa")
cliente = Cliente(id_usuario=1, nombre="Ana López", email="ana@correo.hn",
                  direccion="Col. Palmira", telefono="9999-0000")
ejemplo = creadores.crear_creadores(tarifas)[TipoEnvio.INTERNACIONAL].crear_envio(
    numero_guia="ZYN-00000042", cliente=cliente, sucursal_origen=sucursal,
    direccion_destino="1200 Brickell Ave, Miami", pais_destino="Estados Unidos",
    seguro=Seguro(numero_poliza="POL-7781"),
    paquetes=[Paquete(peso_kg=Decimal("3.5"), alto_cm=Decimal(20), ancho_cm=Decimal(30),
                      largo_cm=Decimal(40), contenido="Café de Marcala",
                      valor_declarado=Decimal(1500)),
              Paquete(peso_kg=Decimal(1), alto_cm=Decimal(15), ancho_cm=Decimal(15),
                      largo_cm=Decimal(15), contenido="Artesanía de barro",
                      valor_declarado=Decimal(800), fragil=True)])
desglose = ejemplo.armar_calculadora().desglose()
filas_desglose = "".join(f"<tr><td>{html.escape(c)}</td><td class='num'>L {m:,.2f}</td></tr>"
                         for c, m in desglose)
total = ejemplo.calcular_costo()

filas_tarifas = "".join(
    f"<tr><td>{t.value.capitalize()}</td><td class='num'>L {tarifas[t].fija:,.2f}</td>"
    f"<td class='num'>L {tarifas[t].por_kg:,.2f}</td>"
    f"<td class='num'>{tarifas[t].tasa_seguro * 100:.0f} %</td>"
    f"<td class='num'>L {tarifas[t].recargo_fragil:,.2f}</td></tr>" for t in TipoEnvio)

CSS = """
@page { size: Letter; margin: 22mm 20mm 20mm 20mm;
  @bottom-left { content: "Zyntra · Documento de diseño · Primer parcial"; font: 8.5pt 'Inter', sans-serif; color: #7A8394; }
  @bottom-right { content: counter(page); font: 8.5pt 'Inter', sans-serif; color: #7A8394; } }
@page portada { margin: 0; @bottom-left { content: none } @bottom-right { content: none } }
:root { --tinta:#1F2633; --suave:#5B6474; --linea:#DDE1E8; --acento:#0F4C81; --acento2:#E8792B;
  --fm:#2B5C9E; --dec:#1E7A46; --st:#B85A12; --ob:#6B3FA0; --fondo:#F5F7FA; }
* { box-sizing: border-box; }
body { font-family: 'Inter', 'DejaVu Sans', sans-serif; color: var(--tinta); font-size: 10.2pt;
  line-height: 1.5; margin: 0; }
h1 { font-size: 19pt; margin: 0 0 10px; color: var(--acento); letter-spacing: -0.3px;
  break-before: page; padding-bottom: 6px; border-bottom: 2px solid var(--acento); }
h1 .num { color: var(--acento2); margin-right: 8px; }
h2 { font-size: 12.5pt; margin: 18px 0 6px; color: var(--tinta); break-after: avoid; }
h3 { font-size: 10.8pt; margin: 12px 0 4px; break-after: avoid; }
p { margin: 0 0 8px; }
.lead { font-size: 11pt; color: var(--suave); }
table { width: 100%; border-collapse: collapse; margin: 8px 0 12px; font-size: 9.3pt; break-inside: avoid; }
th { text-align: left; background: var(--fondo); color: var(--suave); font-weight: 600;
  border-bottom: 1.5px solid var(--linea); padding: 6px 8px; }
td { border-bottom: 1px solid var(--linea); padding: 6px 8px; vertical-align: top; }
td.num, th.num { text-align: right; white-space: nowrap; }
tr.total td { font-weight: 700; border-top: 1.5px solid var(--tinta); }
figure { margin: 10px 0 14px; text-align: center; break-inside: avoid; }
figure img { max-height: 175mm; object-fit: contain; border: 1px solid var(--linea); border-radius: 6px; padding: 6px; background: #fff; }
figcaption { font-size: 8.8pt; color: var(--suave); margin-top: 4px; }
pre { background: #1F2633; color: #E6E9EF; border-radius: 6px; padding: 10px 12px; font-size: 8.1pt;
  line-height: 1.4; overflow: hidden; white-space: pre-wrap; break-inside: avoid; margin: 6px 0 12px; }
code { font-family: 'JetBrains Mono', 'DejaVu Sans Mono', monospace; }
p code, td code, li code { background: var(--fondo); padding: 0 3px; border-radius: 3px; font-size: 8.8pt; }
ul { margin: 0 0 8px; padding-left: 18px; } li { margin-bottom: 3px; }
.chip { display: inline-block; font-size: 8pt; font-weight: 600; padding: 1px 7px; border-radius: 10px; color: #fff; }
.fm { background: var(--fm) } .dec { background: var(--dec) } .st { background: var(--st) } .ob { background: var(--ob) }
.tarjetas { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0 14px; }
.tarjeta { border: 1px solid var(--linea); border-left: 4px solid var(--c); border-radius: 6px;
  padding: 8px 10px; break-inside: avoid; }
.tarjeta b { color: var(--c); } .tarjeta p { margin: 2px 0 0; font-size: 9.2pt; }
.nota { background: #FFF8E1; border-left: 3px solid #D8B85A; padding: 8px 12px; border-radius: 4px;
  font-size: 9.4pt; margin: 8px 0 12px; break-inside: avoid; }
.portada { page: portada; height: 279mm; position: relative; color: #fff;
  background: linear-gradient(155deg, #0F4C81 0%, #0B3459 60%, #081F36 100%); padding: 38mm 24mm; }
.portada .marca { font-size: 46pt; font-weight: 800; letter-spacing: 6px; margin: 0; }
.portada .sub { font-size: 14pt; opacity: .85; margin: 4px 0 26mm; }
.portada .doc { font-size: 22pt; font-weight: 700; margin: 0; }
.portada .parcial { font-size: 12.5pt; color: #FFB27A; margin: 6px 0 0; font-weight: 600; }
.portada .barra { width: 60px; height: 4px; background: var(--acento2); margin: 16mm 0 10mm; }
.portada table { width: auto; font-size: 10.5pt; color: #fff; }
.portada td { border: 0; padding: 4px 18px 4px 0; } .portada td:first-child { opacity: .7; }
.portada .pie { position: absolute; bottom: 22mm; left: 24mm; right: 24mm; font-size: 9pt; opacity: .7;
  border-top: 1px solid rgba(255,255,255,.3); padding-top: 8px; }
.indice { break-before: page; } .indice h1 { break-before: avoid; }
.indice ol { padding-left: 0; list-style: none; font-size: 10.5pt; }
.indice li { display: flex; border-bottom: 1px dotted var(--linea); padding: 5px 0; }
.indice li span:first-child { color: var(--acento2); width: 28px; font-weight: 700; }
.git { background: var(--fondo); color: var(--tinta); font-size: 7.4pt; }
td:first-child { white-space: nowrap; }
"""

DT = [
    ("DT-1", "La decisión «nacional / internacional / express» se repite tres veces en <code>calcular_costo</code>.",
     "Agregar un tipo obliga a editar cada <code>if/elif</code>.", "Factory Method"),
    ("DT-2", "El tipo y el estado son textos sueltos.",
     "<code>Envio(..., \"Nacional\", ...)</code> cuesta L 0 sin avisar (prueba <code>test_tipo_mal_escrito_no_falla</code>).",
     "Factory Method, State (enums)"),
    ("DT-3", "Las transiciones se deciden con <code>if</code> anidados.",
     "Cada estado nuevo vuelve más difícil entender las reglas.", "State"),
    ("DT-4", "Una sola clase guarda datos, calcula costos y controla estados.",
     "Un cambio en las tarifas puede romper el manejo de estados.", "Decorator, State"),
    ("DT-5", "Las tarifas están escritas dentro del código.",
     "Cambiar un precio implica buscarlo en medio de la lógica.", "Tarifa + tarifas.json"),
    ("DT-6", "No se validan los datos de entrada.",
     "Acepta peso −3 kg y guía vacía (prueba <code>test_acepta_peso_negativo</code>).",
     "Factory Method, Paquete"),
    ("DT-7", "Nadie se entera cuando un envío cambia.",
     "No se puede ofrecer rastreo en tiempo real.", "Observer"),
]
filas_dt = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in DT)

CRITERIOS = [
    ("Los tres tipos se crean mediante su creador y rechazan datos inválidos.",
     "test_creadores.py · TestFactoryMethod, TestValidaciones"),
    ("Los costos coinciden con la tabla para todas las combinaciones de tipo, seguro y fragilidad.",
     "test_costos.py · test_todas_las_combinaciones"),
    ("La v1.0 da los mismos costos y transiciones que la v0.1.",
     "test_costos.py · TestMismoResultadoQueV01; test_estados.py · TestMismasTransicionesQueV01"),
    ("Solo se permiten las transiciones del diagrama de estados.",
     "test_estados.py · test_solo_se_permiten_las_transiciones_del_diagrama"),
    ("«Retenido en aduana» solo aplica a envíos internacionales.",
     "test_estados.py · test_aduana_solo_para_internacionales"),
    ("Cada cambio de estado genera un registro de rastreo, aunque se descarten avisos.",
     "test_eventos.py · test_cola_llena_descarta_avisos_pero_no_rastreo"),
    ("Si un notificador falla o tarda, el envío cambia de estado en menos de 10 ms.",
     "test_eventos.py · test_suscriptor_lento_se_corta_por_tiempo_limite, test_un_suscriptor_que_falla_no_afecta_a_los_demas"),
    ("Los diagramas UML coinciden con el código.", "test_diagramas.py · TestDiagramasAlineados"),
]
filas_criterios = "".join(f"<tr><td>CA-{i:02d}</td><td>{a}</td><td><code>{b}</code></td></tr>"
                          for i, (a, b) in enumerate(CRITERIOS, 1))

cuerpo = f"""
<section class="portada">
  <p class="marca">ZYNTRA</p>
  <p class="sub">Sistema de gestión de envíos · Tegucigalpa, Honduras</p>
  <p class="doc">Documento de diseño</p>
  <p class="parcial">Primer parcial: Arquitectura y patrones</p>
  <div class="barra"></div>
  <table>
    <tr><td>Autora</td><td>Tiareth Estrada · 529611</td></tr>
    <tr><td>Materia</td><td>Ingeniería de Software II</td></tr>
    <tr><td>Carrera</td><td>Ingeniería en Tecnologías de la Información y Negocios Digitales</td></tr>
    <tr><td>Institución</td><td>Universidad Anáhuac Mayab</td></tr>
    <tr><td>Fecha</td><td>4 de noviembre de 2026</td></tr>
    <tr><td>Repositorio</td><td>github.com/TiarethE/zyntra · etiqueta v1.0</td></tr>
  </table>
  <div class="pie">Proyecto integrador: Evolución de software · Temas 1.1 a 1.3</div>
</section>

<section class="indice">
  <h1>Contenido</h1>
  <ol>
    <li><span>1</span><span>Introducción</span></li>
    <li><span>2</span><span>Arquitectura de Zyntra</span></li>
    <li><span>3</span><span>Punto de partida y deuda técnica</span></li>
    <li><span>4</span><span>Justificación de los patrones</span></li>
    <li><span>5</span><span>Diseño para el rastreo en tiempo real</span></li>
    <li><span>6</span><span>Comparativa UML: antes y después</span></li>
    <li><span>7</span><span>Implementación y repositorio</span></li>
    <li><span>8</span><span>Conclusiones y limitaciones</span></li>
    <li><span>A</span><span>Referencias</span></li>
  </ol>
</section>

<h1><span class="num">1</span>Introducción</h1>
<p class="lead">Zyntra es el sistema con el que una paquetería con sede en Tegucigalpa, Honduras, registra sus envíos, calcula cuánto cuestan, sigue su recorrido y avisa al cliente cada vez que algo cambia.</p>
<p>La empresa recibe paquetes en sus sucursales, los acomoda en bodegas y ofrece tres servicios: <b>nacional</b>, <b>express</b> (entrega rápida dentro de Honduras) e <b>internacional</b>, que puede quedar retenido en aduana. Los clientes necesitan rastrear su paquete casi en tiempo real. Todos los montos se manejan en lempiras (HNL).</p>
<p>La primera versión del sistema (v0.1) metía todo en una sola clase. Este documento explica cómo se pagó esa deuda técnica con tres patrones de diseño, uno de cada familia, más el patrón Observer para el rastreo:</p>
<div class="tarjetas">
  <div class="tarjeta" style="--c:var(--fm)"><b>Factory Method · creacional</b><p>Un creador por tipo de envío que valida los datos antes de crearlo.</p></div>
  <div class="tarjeta" style="--c:var(--dec)"><b>Decorator · estructural</b><p>El costo base más capas opcionales de seguro y manejo frágil.</p></div>
  <div class="tarjeta" style="--c:var(--st)"><b>State · comportamiento</b><p>Una clase por estado del envío, que conoce sus transiciones.</p></div>
  <div class="tarjeta" style="--c:var(--ob)"><b>Observer · comportamiento</b><p>Un bus de eventos que avisa los cambios sin detener la operación.</p></div>
</div>
<p>Todo lo descrito aquí está implementado en el repositorio con la etiqueta <b>v1.0</b>. Los diagramas se escribieron a partir del código, y una prueba automática comprueba que cada clase, atributo y método dibujado existe en él. Las {total_pruebas} pruebas del proyecto pasan.</p>

<h1><span class="num">2</span>Arquitectura de Zyntra</h1>
<p class="lead">El sistema se organiza en cinco capas. Cada capa solo depende de las que están debajo de ella.</p>
{figura("arquitectura", "Arquitectura por capas.", "62%")}
<table>
  <tr><th>Capa</th><th>Qué contiene</th><th>Responsabilidad</th></tr>
  <tr><td>Presentación</td><td><code>demo.py</code></td><td>Demostración de consola; en una versión futura, la interfaz web.</td></tr>
  <tr><td>Aplicación</td><td><code>GestorEnvios</code></td><td>Punto de entrada: registra envíos, cambia estados y publica eventos.</td></tr>
  <tr><td>Lógica de negocio</td><td>Creadores, envíos, costos, estados, tarifas</td><td>Las reglas del negocio, organizadas con los patrones.</td></tr>
  <tr><td>Dominio</td><td>Usuarios, paquetes, seguro, rastreo, puntos logísticos</td><td>Los datos del negocio y sus validaciones básicas.</td></tr>
  <tr><td>Infraestructura</td><td>Bus de eventos, notificadores, <code>tarifas.json</code></td><td>Comunicación asíncrona y configuración.</td></tr>
</table>
<h2>2.1 Modelo del dominio</h2>
<p>Todo gira alrededor del envío: un cliente lo solicita en una sucursal, contiene uno o más paquetes, puede estar asegurado y va dejando registros de rastreo.</p>
{figura("dominio", "Modelo del dominio (v1.0).", "78%")}
<ul>
  <li><b>Usuario, Cliente y Empleado.</b> Todo cliente y empleado es un usuario con correo y contraseña (guardada con hash PBKDF2). El empleado tiene un rol: empleado de sucursal, repartidor o administrador.</li>
  <li><b>Envío.</b> Es abstracto y tiene tres tipos. Su peso y su valor declarado se calculan sumando sus paquetes; no se guardan dos veces.</li>
  <li><b>Paquete.</b> Guarda peso, medidas, contenido, valor declarado y si es frágil. Se valida al crearse y calcula su peso facturable: el mayor entre el real y el volumétrico (largo × ancho × alto / 5000).</li>
  <li><b>Seguro (0..1).</b> Es opcional y cubre el valor declarado del envío.</li>
  <li><b>RegistroRastreo.</b> Cada movimiento con fecha, estado, descripción, responsable y, si aplica, el punto logístico o las coordenadas.</li>
  <li><b>Puntos logísticos.</b> Sucursales (atienden al público) y bodegas (almacenan y operan vehículos) comparten nombre, dirección y ciudad.</li>
  <li><b>Servicio externo.</b> Un tramo subcontratado a otra transportista, con su guía y el costo del contrato.</li>
</ul>

<h1><span class="num">3</span>Punto de partida y deuda técnica</h1>
<p class="lead">La v0.1 metía todo en una sola clase, <code>Envio</code>: guardaba los datos, calculaba el costo y controlaba los cambios de estado.</p>
{figura("antes", "Diseño de partida (v0.1) con la deuda técnica señalada.", "92%")}
<p>El código original se conserva en <code>legado/envio_legado.py</code> y en la etiqueta <b>v0.1</b>. Sus pruebas de caracterización fijan cómo se comporta, errores incluidos, para comprobar que la refactorización conserva lo que sí funcionaba.</p>
{codigo(__import__("legado.envio_legado", fromlist=["Envio"]).Envio.calcular_costo, (0, 16))}
<h2>3.1 Problemas detectados</h2>
<table>
  <tr><th>Clave</th><th>Problema</th><th>Consecuencia</th><th>Se resuelve con</th></tr>
  {filas_dt}
</table>
<p>Dos principios guían la solución: <b>una clase, una responsabilidad</b> (cada clase cambia por una sola razón) y <b>abierto a extensión, cerrado a modificación</b> (agregar algo nuevo no obliga a editar lo que ya existe).</p>

<h1><span class="num">4</span>Justificación de los patrones</h1>
<p class="lead">Un patrón de diseño es una solución probada a un problema que se repite. Se eligió uno de cada familia del catálogo GoF, y cada uno responde a problemas concretos de la sección anterior.</p>
<table>
  <tr><th>Patrón</th><th>Familia</th><th>Resuelve</th><th>Archivo</th><th>Analogía</th></tr>
  <tr><td><span class="chip fm">Factory Method</span></td><td>Creacional</td><td>DT-1, DT-2, DT-6</td><td><code>creadores.py</code></td><td>La empresa decide en el momento si usa camión o barco según el terreno.</td></tr>
  <tr><td><span class="chip dec">Decorator</span></td><td>Estructural</td><td>DT-4</td><td><code>costos.py</code></td><td>Capas de ropa: un suéter sobre la camisa añade calor sin cambiar a la persona.</td></tr>
  <tr><td><span class="chip st">State</span></td><td>Comportamiento</td><td>DT-2, DT-3</td><td><code>estados.py</code></td><td>Semáforo: el objeto es el mismo, pero actúa distinto según su estado.</td></tr>
  <tr><td><span class="chip ob">Observer</span></td><td>Comportamiento</td><td>DT-7</td><td><code>eventos.py</code></td><td>Suscripción a una revista: cuando sale la edición, llega sin pedirla.</td></tr>
</table>
<p>DT-5 no necesita un patrón: se resuelve sacando las tarifas a <code>datos/tarifas.json</code>, que se carga en objetos <code>Tarifa</code>.</p>

<h2><span class="chip fm">4.1</span> Factory Method</h2>
<p><b>Qué hace.</b> <code>EnvioCreator</code> define el paso de creación (<code>crear_envio</code>) y deja que cada subclase decida qué envío fabricar (<code>_fabricar</code>). Antes de crear, valida la guía (formato <code>ZYN-00000000</code>), el destino, que haya al menos un paquete y que un envío asegurado tenga valor declarado. Cada creador agrega sus reglas: el express admite hasta 30 kg y el internacional exige país de destino distinto de Honduras y valor declarado en cada paquete, porque lo pide la aduana.</p>
<p><b>Por qué aquí.</b> El resto del sistema pide «un envío de tipo X» y no necesita saber qué clase se crea. El tipo deja de ser un texto: es la clase misma y el enum <code>TipoEnvio</code>. Para no mover el <code>if/elif</code> al momento de elegir el creador, se usa un registro: agregar un tipo es agregar un creador y una entrada.</p>
{"<pre><code>" + html.escape(textwrap.dedent('''
CLASES_CREADOR: dict[TipoEnvio, type[EnvioCreator]] = {
    TipoEnvio.NACIONAL: EnvioNacionalCreator,
    TipoEnvio.INTERNACIONAL: EnvioInternacionalCreator,
    TipoEnvio.EXPRESS: EnvioExpressCreator,
}''').strip()) + "</code></pre>"}
<p><b>Por qué no otras opciones.</b> Una función con condiciones solo cambiaría el problema de lugar. Abstract Factory sirve para familias completas de objetos relacionados, y aquí hay una sola familia. Builder conviene para objetos con muchos pasos de armado; crear un envío es un solo paso con validación.</p>
{figura("factory_method", "Factory Method aplicado a los envíos.")}

<h2><span class="chip dec">4.2</span> Decorator</h2>
<p><b>Qué hace.</b> <code>CostoBase</code> calcula la tarifa fija más el precio por kilo del peso facturable. <code>SeguroDecorator</code> y <code>ManejoFragilDecorator</code> envuelven esa calculadora y le suman su cargo solo cuando el envío lo necesita. Cada capa también aporta su línea al desglose que ve el cliente.</p>
{codigo(costos.armar_calculadora)}
<p><b>Por qué aquí.</b> Cada envío se arma según lo que necesita: express asegurado, nacional con paquetes frágiles, internacional con ambos. Un extra nuevo, como «entrega en sábado», es una subclase nueva de <code>DecoradorCosto</code> que no toca el cálculo existente.</p>
<p><b>Por qué no herencia.</b> Con 3 tipos y 2 extras habría que cubrir 3 × 4 = 12 combinaciones con subclases; con un tercer extra serían 3 × 8 = 24. Con Decorator cada extra es una sola clase.</p>
{figura("decorator", "Decorator aplicado al cálculo del costo.", "92%")}

<h2><span class="chip st">4.3</span> State</h2>
<p><b>Qué hace.</b> Cada estado es una clase que declara a qué estados puede pasar. El envío solo le pregunta a su estado actual si el cambio es válido; si no lo es, se lanza <code>TransicionInvalida</code> y nada cambia. Los nombres de estado son el enum <code>NombreEstado</code>, así que un error de escritura falla al instante.</p>
{codigo(estados.EnTransito)}
<p><b>Por qué aquí.</b> Como el semáforo, el envío es el mismo pero reacciona distinto según su estado. «Retenido en aduana» tiene una regla propia: solo aplica si el envío la admite, y solo <code>EnvioInternacional</code> declara <code>admite_aduana = True</code>. Esa regla vive en el estado al que pertenece.</p>
<p><b>Por qué no una tabla de transiciones.</b> Bastaría si los estados solo tuvieran nombre, pero algunos tienen reglas propias (la de aduana). Con State cada regla queda en su clase y agregar un estado es una clase nueva más una transición.</p>
{figura("state", "State aplicado al ciclo de vida del envío.")}
{figura("maquina_estados", "Estados posibles de un envío y sus transiciones.")}

<h2><span class="chip ob">4.4</span> Observer</h2>
<p><b>Qué hace.</b> <code>BusEventos</code> es el sujeto: recibe un evento <code>CambioEstado</code> por cada cambio y lo entrega a sus suscriptores, como el notificador de clientes y el panel de rastreo. El envío no conoce a quienes lo observan.</p>
<p><b>Por qué aquí.</b> Resuelve DT-7: avisar sin acoplar. Agregar un canal nuevo (SMS, WhatsApp) es suscribir un observador nuevo, sin tocar envíos ni estados. Su diseño en tiempo real se explica en la sección 5.</p>
{figura("observer", "Observer: bus de eventos y sus suscriptores.", "88%")}

<h1><span class="num">5</span>Diseño para el rastreo en tiempo real</h1>
<p class="lead">Es tiempo real blando: si una notificación llega un par de segundos tarde no pasa nada grave, pero el sistema nunca debe quedarse detenido esperándola.</p>
<table>
  <tr><th>Regla</th><th>Cómo se cumple en el código</th></tr>
  <tr><td>Publicar no bloquea</td><td><code>publicar()</code> usa <code>put_nowait</code> y regresa de inmediato.</td></tr>
  <tr><td>Tiempo límite por suscriptor</td><td><code>wait_for</code> con {eventos.TIEMPO_LIMITE_S:g} s; si se excede, se registra un aviso y se continúa.</td></tr>
  <tr><td>Cola con límite</td><td>{eventos.CAPACIDAD_COLA} eventos; si se llena, el evento se descarta y se cuenta en <code>descartados</code>.</td></tr>
  <tr><td>Un fallo no afecta a los demás</td><td>Los suscriptores se atienden a la vez con <code>gather</code> y cada error se atrapa por separado.</td></tr>
  <tr><td>El rastreo nunca se pierde</td><td>El registro se guarda de forma síncrona dentro de <code>cambiar_estado</code>, antes de publicar. Por el bus solo viajan los avisos.</td></tr>
  <tr><td>Fácil de probar</td><td>El bus se crea fuera y se entrega a <code>GestorEnvios</code>; no es global.</td></tr>
</table>
{figura("secuencia", "Cambio de estado con notificación en segundo plano.")}
<div class="nota">Este diseño es la base del «Módulo de respuesta» del Segundo Parcial (manejo de eventos concurrentes). Ahí se le agregarán reintentos y persistencia.</div>

<h1><span class="num">6</span>Comparativa UML: antes y después</h1>
{figura("despues", "Diseño después de aplicar los patrones (comparar con la Figura 3).")}
<table>
  <tr><th>Aspecto</th><th>Antes (v0.1)</th><th>Después (v1.0)</th></tr>
  <tr><td>Clases</td><td>Una sola: <code>Envio</code>.</td><td>{len([c for c in __import__('tests.test_diagramas', fromlist=['x']).clases_del_codigo().values() if any(o.__module__.startswith('zyntra') for o in c)])} clases, cada una con una responsabilidad.</td></tr>
  <tr><td>Tipo de envío</td><td>Texto libre; un error da costo 0.</td><td>Una clase por tipo y el enum <code>TipoEnvio</code>.</td></tr>
  <tr><td>Creación</td><td>Sin validar: acepta peso negativo.</td><td>Un creador por tipo que valida antes de crear.</td></tr>
  <tr><td>Costo</td><td><code>if/elif</code> repetido; tarifas en el código; trunca centavos.</td><td>Costo base más capas; tarifas en JSON; <code>Decimal</code> con centavos.</td></tr>
  <tr><td>Peso</td><td>Un solo número.</td><td>Suma de paquetes, con peso volumétrico.</td></tr>
  <tr><td>Estados</td><td><code>if</code> anidados sobre textos.</td><td>Una clase por estado; transición inválida lanza error.</td></tr>
  <tr><td>Rastreo</td><td>No existía.</td><td>Registro por cada cambio y aviso asíncrono por el bus.</td></tr>
  <tr><td>Agregar algo nuevo</td><td>Editar la clase central.</td><td>Agregar una clase nueva.</td></tr>
  <tr><td>Pruebas</td><td>Ninguna.</td><td>{total_pruebas} pruebas automáticas.</td></tr>
</table>
<p><b>Costo de la solución.</b> Hay más clases y el diseño pide un poco más de lectura al inicio. A cambio, cada pieza es pequeña, se prueba por separado y crece sin romper lo existente.</p>

<h1><span class="num">7</span>Implementación y repositorio</h1>
<p class="lead">El código está en Python 3.11+, sin librerías externas, en <b>github.com/TiarethE/zyntra</b>.</p>
<pre class="git"><code>python -m zyntra.demo     # demostración de punta a punta
python -m unittest -v     # {total_pruebas} pruebas automáticas</code></pre>
<h2>7.1 Tarifas</h2>
<table>
  <tr><th>Tipo</th><th class="num">Tarifa fija</th><th class="num">Por kg</th><th class="num">Seguro</th><th class="num">Frágil (por paquete)</th></tr>
  {filas_tarifas}
</table>
<p>Costo = tarifa fija + (por kg × peso facturable) + seguro (porcentaje del valor declarado, si está asegurado) + recargo por cada paquete frágil.</p>
<h3>Ejemplo: envío internacional a Miami</h3>
<p>Dos paquetes: café (3.5 kg, caja de 20 × 30 × 40 cm, valor L 1,500) y artesanía frágil (1 kg, valor L 800), asegurado. La caja de café pesa 4.8 kg volumétricos, así que se cobra ese peso. Este es el desglose que produce el código:</p>
<table style="width:70%">
  <tr><th>Concepto</th><th class="num">Monto</th></tr>
  {filas_desglose}
  <tr class="total"><td>Total</td><td class="num">L {total:,.2f}</td></tr>
</table>
<h2>7.2 Control de versiones</h2>
<p>Cada patrón se desarrolló en su propia rama y se unió a <code>main</code> con sus pruebas pasando. La etiqueta <b>v0.1</b> marca el código de partida y <b>v1.0</b> la versión refactorizada. Los cambios se documentan en <code>CHANGELOG.md</code>.</p>
<pre class="git"><code>{html.escape(historial.strip())}</code></pre>
<h2>7.3 Criterios de aceptación</h2>
<p>Cada criterio tiene al menos una prueba automática que lo verifica.</p>
<table>
  <tr><th>Clave</th><th>Criterio</th><th>Prueba</th></tr>
  {filas_criterios}
</table>

<h1><span class="num">8</span>Conclusiones y limitaciones</h1>
<p>Separar la creación, el costo, los estados y los avisos permitió que cada cambio futuro se resuelva agregando una clase y no editando una central. Los cuatro patrones responden a problemas reales del diseño de partida y se complementan: Factory Method entrega envíos válidos, Decorator calcula su costo, State controla su ciclo de vida y Observer avisa cada cambio. Las pruebas de caracterización demuestran que la v1.0 conserva los costos y transiciones de la v0.1, y corrige sus errores.</p>
<h2>Limitaciones</h2>
<ul>
  <li>Los datos viven en memoria: no hay base de datos todavía.</li>
  <li>El bus de eventos no tiene reintentos ni persistencia; un aviso descartado no se recupera (el rastreo sí se conserva).</li>
  <li>Los notificadores simulan el envío de correos; no hay integración con un servicio real.</li>
  <li>El servicio express es solo nacional, y la asignación de vehículos a rutas queda fuera del alcance de esta etapa.</li>
  <li>No hay interfaz gráfica; la demostración es de consola.</li>
</ul>

<h1><span class="num">A</span>Referencias</h1>
<ul>
  <li>Fowler, M. (2018). <i>Refactoring: Improving the design of existing code</i> (2.ª ed.). Addison-Wesley.</li>
  <li>Gamma, E., Helm, R., Johnson, R. y Vlissides, J. (1994). <i>Design patterns: Elements of reusable object-oriented software</i>. Addison-Wesley.</li>
  <li>Martin, R. C. (2003). <i>Agile software development: Principles, patterns, and practices</i>. Prentice Hall.</li>
  <li>Python Software Foundation. (2025). <i>asyncio: Asynchronous I/O</i>. https://docs.python.org/3/library/asyncio.html</li>
  <li>Universidad Anáhuac Mayab. (2026). <i>Tema 1.2: Catálogo de patrones de diseño (GoF)</i> [Material del curso]. Ingeniería de Software II.</li>
</ul>
"""

documento = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Zyntra – Documento de diseño (Primer parcial)</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>{cuerpo}</body></html>"""

html_salida = SALIDA.with_suffix(".html")
html_salida.write_text(documento, encoding="utf-8")

js = f"""const p=require('playwright');(async()=>{{const b=await p.chromium.launch();const pg=await b.newPage();
await pg.goto({json.dumps(html_salida.as_uri())},{{waitUntil:'networkidle'}});
await pg.pdf({{path:{json.dumps(str(SALIDA))},printBackground:true,preferCSSPageSize:true}});await b.close();}})();"""
subprocess.run(["node", "-e", js], check=True)
print(SALIDA)
