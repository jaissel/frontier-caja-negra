"""Manda mensajes a la caja negra y los anota en experimentos.jsonl.

Uso desde la terminal:
    python enviar.py reset s1
    python enviar.py msg s1 "PING;64" "PING responde sin estado"

Uso desde otro script:
    from enviar import reset, msg
    reset()
    msg("s1", "PING;64", "hipótesis")
"""
import json
import os
import sys
import time

import httpx2 as httpx  # viene instalado con la librería openai
from dotenv import load_dotenv

load_dotenv()
URL = os.environ["URL_ORIGINAL"].rstrip("/")
TOKEN = os.environ["TOKEN_PERSONAL"].strip()
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experimentos.jsonl")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
PAUSA = 0.13  # ~7.5 requests por segundo; el límite es 10

_cliente = httpx.Client(timeout=15)
_ultimo = 0.0


def _esperar_turno():
    global _ultimo
    falta = PAUSA - (time.time() - _ultimo)
    if falta > 0:
        time.sleep(falta)
    _ultimo = time.time()


def siguiente_id():
    if not os.path.exists(LOG):
        return 1
    with open(LOG, encoding="utf-8") as f:
        return sum(1 for linea in f if linea.strip()) + 1


def reset():
    _esperar_turno()
    r = _cliente.post(f"{URL}/__reset", headers=HEADERS)
    return r.status_code, r.text


def crudo(metodo, ruta, seq, hipotesis, headers=None, cuerpo=None, json_body=None, conclusion=None):
    """Request arbitrario (otras rutas, sin token, cuerpo raro). También se anota en el log."""
    for _ in range(5):
        _esperar_turno()
        r = _cliente.request(metodo, f"{URL}{ruta}", headers=headers if headers is not None else HEADERS,
                             content=cuerpo, json=json_body)
        if r.headers.get("X-Frontier-Infra") != "rate-limit":
            break
        time.sleep(1.5)
    try:
        resp = r.json()
    except ValueError:
        resp = r.text
    if json_body is not None:
        req = json_body
    elif cuerpo is not None:
        req = cuerpo if isinstance(cuerpo, str) else cuerpo.decode("utf-8", "replace")
    else:
        req = None
    linea = {
        "id": siguiente_id(),
        "seq": seq,
        "x_req": r.headers.get("X-Req"),
        "hipotesis": hipotesis,
        "request": req,
        "status": r.status_code,
        "response": resp,
    }
    if metodo != "POST" or ruta != "/msg":
        linea["metodo"] = metodo
        linea["ruta"] = ruta
    if headers is not None:
        linea["auth"] = "personalizado"
    if conclusion:
        linea["conclusion"] = conclusion
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(linea, ensure_ascii=False) + "\n")
    return linea


def msg(seq, m, hipotesis, conclusion=None):
    return crudo("POST", "/msg", seq, hipotesis, json_body={"m": m}, conclusion=conclusion)


def mostrar(linea):
    print(f"#{linea['id']:>4} {linea['status']} {json.dumps(linea['response'], ensure_ascii=False)}  <- {json.dumps(linea['request'], ensure_ascii=False)}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "reset":
        print("RESET ->", *reset())
    elif len(sys.argv) >= 5 and sys.argv[1] == "msg":
        mostrar(msg(*sys.argv[2:6]))
    else:
        print(__doc__)
