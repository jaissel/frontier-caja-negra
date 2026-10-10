"""Repite las secuencias grabadas del original contra el clon y compara (misma regla que el set).

Uso:
    python replay.py <url>          # secuencias de la versión 2 (después de las 15:30)
    python replay.py <url> v1       # secuencias de la versión 1 (ejemplos + log de la mañana)
"""
import json
import os
import sys
from collections import OrderedDict

import httpx2 as httpx
from dotenv import load_dotenv

load_dotenv()
BASE = sys.argv[1].rstrip("/")
VERSION = sys.argv[2] if len(sys.argv) > 2 else "v2"



def es_v2(seq):
    return seq.startswith(("r2-", "v2", "fz", "llm"))


TOKEN = os.environ["TOKEN_EQUIPO"].strip()
H = {"Authorization": f"Bearer {TOKEN}"}
cli = httpx.Client(timeout=10)


def cargar(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def es_crudo(l):
    """El log guarda igual un cuerpo crudo y un string JSON: si el texto es un objeto JSON o dio E100, fue crudo."""
    req = l["request"]
    if isinstance(l["response"], dict) and l["response"].get("error") in ("E100", "E101"):
        return True
    try:
        return isinstance(json.loads(req), (dict, list))
    except ValueError:
        return False


def secuencias():
    seqs = OrderedDict()
    for l in cargar("pruebas/ejemplos.jsonl"):
        seqs.setdefault("ejemplos", []).append(l)
    if os.path.exists("experimentos.jsonl"):
        for l in cargar("experimentos.jsonl"):
            seqs.setdefault(l["seq"], []).append(l)
    return seqs


def enviar(l):
    metodo, ruta = l.get("metodo", "POST"), l.get("ruta", "/msg")
    req = l["request"]
    if l.get("auth") == "personalizado":
        return None  # no guardamos qué header se usó; se prueba aparte
    if isinstance(req, dict) or isinstance(req, list):
        return cli.request(metodo, BASE + ruta, headers=H, json=req)
    if isinstance(req, str):
        if es_crudo(l):
            return cli.request(metodo, BASE + ruta, headers=H, content=req.encode())
        return cli.request(metodo, BASE + ruta, headers=H, json=req)
    return cli.request(metodo, BASE + ruta, headers=H)


def main():
    pasos = iguales = tests = tests_ok = 0
    fallos = []
    for seq, lineas in secuencias().items():
        if es_v2(seq) != (VERSION == "v2"):
            continue
        cli.post(BASE + "/__reset", headers=H)
        todo_ok = True
        for l in lineas:
            r = enviar(l)
            if r is None:
                continue
            try:
                cuerpo = r.json()
            except ValueError:
                cuerpo = r.text
            pasos += 1
            if r.status_code == l["status"] and cuerpo == l["response"]:
                iguales += 1
            else:
                todo_ok = False
                fallos.append((seq, l.get("id", l.get("n")), l["request"], (l["status"], l["response"]), (r.status_code, cuerpo)))
        tests += 1
        tests_ok += todo_ok
    print(f"Pasos idénticos: {iguales}/{pasos} ({100 * iguales / max(pasos, 1):.1f}%)")
    print(f"Secuencias completas: {tests_ok}/{tests}")
    for f in fallos[:40]:
        print("FALLA", f)


if __name__ == "__main__":
    main()
