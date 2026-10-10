"""Repite secuencias grabadas CONTRA EL ORIGINAL para detectar si cambió. Todo se anota en el log.

Uso: python regresion.py <etiqueta> [seq1 seq2 ...]     (por defecto: ejemplos + e1..e11)
"""
import json
import sys

from enviar import crudo, reset
from replay import secuencias

etiqueta = sys.argv[1]
pedidas = sys.argv[2:] or ["ejemplos"] + [f"e{i}" for i in range(1, 12)]

todas = secuencias()
difs = 0
total = 0
for seq in pedidas:
    reset()
    nueva = f"{etiqueta}-{seq}"
    for l in todas[seq]:
        if l.get("auth") == "personalizado":
            continue
        req = l["request"]
        ref = l.get("id", l.get("n"))
        hip = f"regresión: ¿{seq} #{ref} responde igual que antes?"
        metodo, ruta = l.get("metodo", "POST"), l.get("ruta", "/msg")
        if isinstance(req, (dict, list)):
            r = crudo(metodo, ruta, nueva, hip, json_body=req)
        elif isinstance(req, str):
            if isinstance(l["response"], dict) and l["response"].get("error") == "E100":
                r = crudo(metodo, ruta, nueva, hip, cuerpo=req.encode())
            else:
                r = crudo(metodo, ruta, nueva, hip, json_body=req)
        else:
            r = crudo(metodo, ruta, nueva, hip)
        total += 1
        if (r["status"], r["response"]) != (l["status"], l["response"]):
            difs += 1
            print(f"CAMBIO {seq} #{ref} -> nuevo #{r['id']}: {json.dumps(req, ensure_ascii=False)}")
            print(f"     antes: {l['status']} {json.dumps(l['response'], ensure_ascii=False)}")
            print(f"     ahora: {r['status']} {json.dumps(r['response'], ensure_ascii=False)}")
print(f"\n{total - difs}/{total} iguales, {difs} cambios")
