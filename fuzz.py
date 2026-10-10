"""Set de prueba con la forma del set oculto: 40 tests de 1 request, 45 de 2-5 y 15 de 6-12.

Cada test: reset en el original y en el clon, se manda cada request a los dos y se compara.
Lo que se manda al original queda en experimentos.jsonl (seq = fz-<n>).

Uso: python fuzz.py <url_clon> [semilla]
"""
import json
import os
import random
import sys

import httpx2 as httpx
from dotenv import load_dotenv

from control import firmar
from enviar import crudo, reset

load_dotenv()
CLON = sys.argv[1].rstrip("/")
rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 2026)
HC = {"Authorization": f"Bearer {os.environ['TOKEN_EQUIPO'].strip()}"}
cli = httpx.Client(timeout=10)

NOMBRES = ["Ana", "Beto", "Lucia", "Mateo", "José", "Ana Maria", "X", "123"]
MONTOS_OK = ["1", "5", "100", "999", "5000", "20000", "49999", "50000", "50001", "75000", "100000", "100001", "250000", "9999999999"]
MONTOS_MAL = ["0", "-5", "10.5", "abc", "007", "+5", " 5", "10000000000"]


class Gen:
    """Genera mensajes plausibles según el estado que se va armando en la secuencia."""

    def __init__(self):
        self.cuentas = 0
        self.ops = 0

    def cuenta(self, existente=True):
        if existente and self.cuentas and rnd.random() < 0.9:
            return f"AC-{rnd.randint(1, self.cuentas):04d}"
        return rnd.choice(["AC-0099", "AC-0009", "ac-0001", "AC-1", "XX-0001"])

    def monto(self):
        return rnd.choice(MONTOS_OK) if rnd.random() < 0.85 else rnd.choice(MONTOS_MAL)

    def cuerpo_valido(self):
        r = rnd.random()
        if self.cuentas == 0 or r < 0.18:
            self.cuentas += 1
            return f"ALTA;{rnd.choice(NOMBRES)}"
        if r < 0.38:
            return f"DEPOSITO;{self.cuenta()};{self.monto()}"
        if r < 0.62:
            a, b = self.cuenta(), self.cuenta()
            if rnd.random() < 0.08:
                b = a
            return f"TRANSFER;{a};{b};{self.monto()}"
        if r < 0.80:
            return f"CONSULTA;{self.cuenta()}"
        if r < 0.92:
            op = f"OP-{rnd.randint(1, max(self.ops, 1) + 1):04d}"
            return f"ANULA;{op}"
        return rnd.choice(["PING", "HALT;X", "HALT;1", "HALT;0"])

    def mensaje(self):
        """Devuelve (kind, payload) donde kind es 'json' o 'raw'."""
        r = rnd.random()
        if r < 0.70:
            m = firmar(self.cuerpo_valido())
            if m.startswith(("DEPOSITO", "TRANSFER")):
                self.ops += 1
            if rnd.random() < 0.15:
                m = m.lower() if rnd.random() < 0.5 else m.replace("CONSULTA", "CONSULTa")
            return "json", {"m": m}
        if r < 0.80:  # control malo o mal formado
            cuerpo = self.cuerpo_valido()
            return "json", {"m": f"{cuerpo};{rnd.choice(['0', '99', '5X', '100', '014', ' 7'])}"}
        if r < 0.88:  # comando desconocido o aridad mala, con control válido
            return "json", {"m": firmar(rnd.choice(["CONSULT;AC-0001", "SALDOS;AC-0001", "HELP", "TRANSFERENCIA;1",
                                                     "ALTA;Ana;Lopez", "CONSULTA", "DEPOSITO;AC-0001", "XYZ;1", "ANUL;OP-0001"]))}
        if r < 0.95:  # problemas de forma
            return "json", rnd.choice([{"m": "PING"}, {"m": ""}, {"m": ";"}, {"m": "CONSULTA;;14"}, {"x": 1}, {"m": 5},
                                       {"m": "PING;XX"}, {"m": "PING;1;2"}])
        return "raw", rnd.choice([b"", b"no json", b'{"m": "PING;1"'])


def enviar_clon(kind, payload):
    if kind == "json":
        r = cli.post(CLON + "/msg", headers=HC, json=payload)
    else:
        r = cli.post(CLON + "/msg", headers=HC, content=payload)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, r.text


def main():
    tamanos = [1] * 40 + [rnd.randint(2, 5) for _ in range(45)] + [rnd.randint(6, 12) for _ in range(15)]
    ok_tests = 0
    pasos = pasos_ok = 0
    fallos = []
    por_grupo = {"1": [0, 0], "2-5": [0, 0], "6-12": [0, 0]}
    for n, tam in enumerate(tamanos, 1):
        grupo = "1" if tam == 1 else ("2-5" if tam <= 5 else "6-12")
        reset()
        cli.post(CLON + "/__reset", headers=HC)
        g = Gen()
        bien = True
        for _ in range(tam):
            kind, payload = g.mensaje()
            seq = f"fz-{n:03d}"
            hip = "set de prueba aleatorio con la forma del set oculto: ¿el clon responde igual?"
            if kind == "json":
                lo = crudo("POST", "/msg", seq, hip, json_body=payload)
            else:
                lo = crudo("POST", "/msg", seq, hip, cuerpo=payload)
            sc, bc = enviar_clon(kind, payload)
            pasos += 1
            if (sc, bc) == (lo["status"], lo["response"]):
                pasos_ok += 1
            else:
                bien = False
                fallos.append((seq, lo["id"], payload if kind == "json" else payload.decode(),
                               (lo["status"], lo["response"]), (sc, bc)))
        ok_tests += bien
        por_grupo[grupo][0] += bien
        por_grupo[grupo][1] += 1
    print(f"Tests que pasan: {ok_tests}/{len(tamanos)}")
    for gname, (a, b) in por_grupo.items():
        print(f"  {gname:>4} requests: {a}/{b}")
    print(f"Pasos idénticos: {pasos_ok}/{pasos}")
    for f in fallos[:30]:
        print("FALLA", json.dumps(f, ensure_ascii=False))


if __name__ == "__main__":
    main()
