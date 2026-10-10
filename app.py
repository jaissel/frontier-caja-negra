"""Reemplazo de la caja negra (Reto 2, Frontier).

Pipeline de cada request a POST /msg (en este orden, igual que el original):
  ruta -> auth -> JSON -> campo m -> separadores -> segmentos vacíos -> PING
  -> formato del control -> valor del control -> comando -> aridad -> reglas del comando
"""
import json
import os
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from control import control

TOKEN = os.environ.get("TOKEN_EQUIPO", "").strip()
# Versión del comportamiento a imitar. El original pasó a v2 a las 15:30 (ticket FR-0153).
VERSION = int(os.environ.get("VERSION", "2"))

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# ---------- Tabla de errores (datos, no código: se corrige rápido si el original cambia) ----------
ERRORES = {
    "E001": (401, "no autorizado"),
    "E100": (400, "json inválido"),
    "E101": (413, "cuerpo demasiado grande"),
    "E102": (400, "falta m"),
    "E103": (400, "falta control"),
    "E104": (400, "segmento vacío"),
    "E201": (400, "control mal formado"),
    "E202": (400, "control inválido"),
    "E301": (400, "comando desconocido "),  # el espacio final es del original
    "E302": (400, "aridad inválida"),
    "E303": (400, "monto inválido"),
    "E304": (400, "origen y destino iguales"),
    "E401": (404, "cuenta inexistente"),
    "E402": (404, "operación inexistente"),
    "E404": (404, "ruta desconocida"),
    "E506": (422, "límite excedido"),
    "E507": (422, "saldo insuficiente"),
    "E510": (423, "cuenta bloqueada"),
    "E520": (409, "operación destructiva: detiene el servicio; reenvía con confirmación"),
    "E599": (503, "service halted"),
}

# Comandos y cuántos argumentos llevan (sin contar el comando ni el control)
# El orden importa: en un empate de la sugerencia gana el primero (ALT -> ALTA, no HALT)
ARIDAD = {"PING": 0, "ALTA": 1, "CONSULTA": 1, "DEPOSITO": 2, "TRANSFER": 3, "ANULA": 1, "HALT": 1}
LIMITE_TRANSFER = 100000 if VERSION == 1 else 50000   # v2: bajó a 50000
RECHAZOS_PARA_BLOQUEO = 3                               # v2: 3 rechazos E506/E507 seguidos bloquean
MONTO_OK = re.compile(r"[1-9][0-9]{0,9}")   # entero positivo, sin ceros a la izquierda, hasta 10 dígitos
CONTROL_OK = re.compile(r"[0-9]{1,2}")

MAX_CUERPO = 8192   # bytes; 8193 o más -> 413 E101

RUTAS = {("GET", "/health"), ("POST", "/__reset"), ("POST", "/msg")}


# ---------- Estado en memoria ----------
class Estado:
    def __init__(self):
        self.cuentas = {}       # "AC-0001" -> saldo
        self.operaciones = {}   # "OP-0001" -> dict(tipo, monto, origen, destino, anulada)
        self.n_cuentas = 0
        self.n_ops = 0
        self.detenido = False   # HALT;1 detiene el servicio hasta el próximo reset
        # v2: por cuenta de origen
        self.racha = {}         # rechazos de negocio seguidos (E506/E507)
        self.intentos = {}      # cuenta bloqueada -> intentos hechos mientras está bloqueada


estado = Estado()


def error(codigo, **extra):
    status, mensaje = ERRORES[codigo]
    return JSONResponse({"error": codigo, "mensaje": mensaje, **extra}, status_code=status)


def ok(cuerpo, status=200):
    return JSONResponse(cuerpo, status_code=status)


def distancia(a, b):
    """Distancia de Levenshtein."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def sugerencia(cmd):
    mejor = min(ARIDAD, key=lambda c: distancia(cmd, c))
    return mejor if distancia(cmd, mejor) <= 2 else None


def formato_saldo(centavos):
    """v1: entero tal cual. v2: string en pesos con 2 decimales ("0.05", "-30.00")."""
    if VERSION == 1:
        return centavos
    signo = "-" if centavos < 0 else ""
    c = abs(centavos)
    return f"{signo}{c // 100}.{c % 100:02d}"


def nueva_op(**datos):
    estado.n_ops += 1
    op_id = f"OP-{estado.n_ops:04d}"
    estado.operaciones[op_id] = {**datos, "anulada": False}
    return ok({"status": "recieved", "operacionId": op_id})  # "recieved" mal escrito, igual que el original


# ---------- Comandos ----------
def cmd_alta(nombre):
    estado.n_cuentas += 1
    cuenta = f"AC-{estado.n_cuentas:04d}"
    estado.cuentas[cuenta] = 0
    return ok({"cuentaId": cuenta}, 201)


def cmd_consulta(cuenta):
    if cuenta not in estado.cuentas:
        return error("E401")
    return ok({"cuenta_id": cuenta, "saldo": formato_saldo(estado.cuentas[cuenta])})


def cmd_deposito(cuenta, monto):
    if not MONTO_OK.fullmatch(monto):
        return error("E303")
    if cuenta not in estado.cuentas:
        return error("E401")
    monto = int(monto)
    estado.cuentas[cuenta] += monto
    # v2: cualquier depósito a la cuenta la desbloquea y reinicia su racha de rechazos
    estado.racha.pop(cuenta, None)
    estado.intentos.pop(cuenta, None)
    return nueva_op(tipo="DEPOSITO", monto=monto, destino=cuenta)


def cmd_transfer(origen, destino, monto):
    if not MONTO_OK.fullmatch(monto):
        return error("E303")
    if origen == destino:
        return error("E304")
    if origen not in estado.cuentas or destino not in estado.cuentas:
        return error("E401")
    monto = int(monto)
    if VERSION >= 2 and origen in estado.intentos:
        estado.intentos[origen] += 1
        return error("E510", intentos=estado.intentos[origen])
    if monto > LIMITE_TRANSFER:
        return rechazo(origen, "E506")
    if estado.cuentas[origen] < monto:
        return rechazo(origen, "E507")
    estado.racha.pop(origen, None)  # una transferencia exitosa corta la racha
    estado.cuentas[origen] -= monto
    estado.cuentas[destino] += monto
    return nueva_op(tipo="TRANSFER", monto=monto, origen=origen, destino=destino)


def rechazo(origen, codigo):
    """v2: el 3er rechazo de negocio seguido responde normal y deja la cuenta bloqueada."""
    if VERSION >= 2:
        estado.racha[origen] = estado.racha.get(origen, 0) + 1
        if estado.racha[origen] >= RECHAZOS_PARA_BLOQUEO:
            estado.intentos[origen] = 0
    return error(codigo)


def cmd_anula(op_id):
    op = estado.operaciones.get(op_id)
    if op is None:
        return error("E402")
    if op["anulada"]:
        return ok({"ok": False, "motivo": "ya anulada"})
    op["anulada"] = True
    estado.cuentas[op["destino"]] -= op["monto"]  # puede quedar negativo, como en el original
    if op["tipo"] == "TRANSFER":
        estado.cuentas[op["origen"]] += op["monto"]
    return ok({"ok": True, "anulada": op_id})


def cmd_halt(confirmacion):
    # Comando oculto: solo "1" confirma; cualquier otro valor pide confirmación
    if confirmacion != "1":
        return error("E520")
    estado.detenido = True
    return error("E599")


COMANDOS = {"HALT": cmd_halt, "ALTA": cmd_alta, "CONSULTA": cmd_consulta, "DEPOSITO": cmd_deposito,
            "TRANSFER": cmd_transfer, "ANULA": cmd_anula}


def procesar(m):
    if ";" not in m:
        return error("E103")
    seg = m.split(";")
    if any(s == "" for s in seg):
        return error("E104")

    # PING se atiende antes de mirar el control: no lo valida
    if seg[0].upper() == "PING":
        return ok({"pong": True}) if len(seg) == 2 else error("E302")

    ctl = seg[-1]
    if not CONTROL_OK.fullmatch(ctl):
        return error("E201")
    if int(ctl) != control(";".join(seg[:-1])):
        return error("E202")

    cmd = seg[0].upper()
    if cmd not in COMANDOS:
        sug = sugerencia(cmd)
        return error("E301", sugerencia=sug) if sug else error("E301")

    args = seg[1:-1]
    if len(args) != ARIDAD[cmd]:
        return error("E302")
    return COMANDOS[cmd](*args)


# ---------- HTTP ----------
def _sin_constantes(nombre):
    raise ValueError(nombre)


@app.api_route("/{ruta:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def todo(ruta: str, request: Request):
    global estado
    if (request.method, request.url.path) not in RUTAS:
        return error("E404")  # el original responde 404 aun sin token
    if not TOKEN or request.headers.get("authorization") != f"Bearer {TOKEN}":
        return error("E001")

    if request.url.path == "/health":
        return ok({"ok": True})
    if request.url.path == "/__reset":
        estado = Estado()
        return ok({"ok": True})

    if estado.detenido:
        return error("E599")  # detenido: todo /msg da 503, incluso con JSON roto

    crudo = await request.body()
    if len(crudo) > MAX_CUERPO:
        return error("E101")
    try:
        # Igual que el original: BOM inicial, NaN e Infinity son JSON inválido
        cuerpo = json.loads(crudo.decode("utf-8"), parse_constant=_sin_constantes)
    except (ValueError, UnicodeDecodeError):
        return error("E100")
    if not isinstance(cuerpo, dict) or not isinstance(cuerpo.get("m"), str):
        return error("E102")
    return procesar(cuerpo["m"])
