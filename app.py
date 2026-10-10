import os
import re
import json
import time
import threading
import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=None)
BASE = os.path.dirname(os.path.abspath(__file__))

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
MAX_PER_MINUTE = int(os.environ.get("MAX_PER_MINUTE", "6"))   # por IP
MAX_PER_DAY = int(os.environ.get("MAX_PER_DAY", "400"))       # global, protege tu cuota

ATTRS = [
    "cabeceo", "centros", "control", "entradas", "marcaje", "pases", "regate", "remate",
    "tecnica", "tiros_lejanos", "penaltis", "saques_esquina", "saques_largos", "tiros_libres",
    "agresividad", "anticipacion", "colocacion", "concentracion", "decisiones", "desmarques",
    "determinacion", "juego_equipo", "liderazgo", "sacrificio", "serenidad", "talento",
    "valentia", "vision", "aceleracion", "agilidad", "salto", "equilibrio", "fuerza",
    "recuperacion", "resistencia", "velocidad",
]
RADAR = ["radar_defensa", "radar_fisico", "radar_velocidad", "radar_vision", "radar_ataque", "radar_tecnica", "radar_aereo", "radar_mental"]
PROFILE = ["nombre", "nacionalidad", "edad", "equipo", "posicion", "calidad", "valor", "salario", "contrato"]

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        **{k: {"type": "STRING"} for k in PROFILE},
        **{k: {"type": "INTEGER"} for k in ATTRS + RADAR},
    },
    "required": PROFILE + ATTRS + RADAR,
}

PROMPT = (
    "Imagen de una pantalla de Football Manager (interfaz en español). Devuelve JSON con el perfil y dos bloques de datos. "
    "REGLA CLAVE: solo transcribe numeros que se vean de verdad en la imagen. NUNCA inventes ni estimes: si algo no se ve, pon 0. "
    "1) Atributos (36, enteros 1-20): solo si la imagen muestra las listas Tecnico/Mental/Fisico/Balon parado con el numero junto a cada nombre. "
    "Si esas listas NO aparecen (por ejemplo cuando solo se ve el grafico de radar), pon 0 en los 36. "
    "Lee cada digito con cuidado, sobre todo 15 frente a 16, 13 frente a 18 y 6 frente a 8. "
    "Mapeo: tecnica=Tecnica, tiros_lejanos=Tiros lejanos, saques_esquina=Saques de esquina, saques_largos=Saques largos, "
    "tiros_libres=Tiros libres, juego_equipo=Juego en equipo, salto=Alcance de salto, recuperacion=Recuperacion fisica. "
    "2) Radar del juego: si la imagen muestra el grafico de radar con ocho etiquetas y un numero junto a cada una "
    "(Defensa arriba, y en sentido horario Fisico, Velocidad, Vision, Ataque, Tecnica, Aereo, Mental), copia esos ocho numeros en "
    "radar_defensa, radar_fisico, radar_velocidad, radar_vision, radar_ataque, radar_tecnica, radar_aereo, radar_mental. Si no hay radar, 0. "
    "Perfil: calidad = estrellas del rol seleccionado (fila resaltada), por ejemplo 2.5 estrellas; "
    "valor = valor de mercado; salario = texto tal cual aparece; posicion = posicion del jugador."
)

_lock = threading.Lock()
_hits = {}
_day = {"date": "", "n": 0}


def allowed(ip):
    now = time.time()
    today = time.strftime("%Y-%m-%d")
    with _lock:
        if _day["date"] != today:
            _day["date"], _day["n"] = today, 0
        if _day["n"] >= MAX_PER_DAY:
            return False, "Se ha alcanzado el limite diario de la web. Prueba manana."
        recent = [t for t in _hits.get(ip, []) if now - t < 60]
        if len(recent) >= MAX_PER_MINUTE:
            return False, "Demasiadas peticiones seguidas. Espera un minuto."
        recent.append(now)
        _hits[ip] = recent
        _day["n"] += 1
    return True, ""


def clean(data):
    out = {k: str(data.get(k, "") or "").strip() for k in PROFILE}
    for k in ATTRS + RADAR:
        try:
            v = int(data.get(k, 0))
        except (TypeError, ValueError):
            v = 0
        out[k] = v if 1 <= v <= 20 else 0
    return out


@app.route("/")
def index():
    return send_from_directory(BASE, "index.html")


@app.route("/health")
def health():
    return jsonify({"ok": True, "key": bool(API_KEY), "model": MODEL})


@app.route("/escanear", methods=["POST"])
def escanear():
    if not API_KEY:
        return jsonify({"status": "error", "message": "Falta GEMINI_API_KEY en el servidor."}), 500

    ip = (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()
    ok, msg = allowed(ip)
    if not ok:
        return jsonify({"status": "error", "message": msg}), 429

    body = request.get_json(silent=True) or {}
    image = body.get("image", "")
    if "," not in image:
        return jsonify({"status": "error", "message": "Imagen no valida."}), 400
    header, b64 = image.split(",", 1)
    if len(b64) > 4_000_000:
        return jsonify({"status": "error", "message": "Imagen demasiado grande."}), 413
    mime = "image/png" if "png" in header else "image/jpeg"

    payload = {
        "contents": [{"parts": [{"text": PROMPT}, {"inlineData": {"mimeType": mime, "data": b64}}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
        },
    }
    payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

    last = ""
    for attempt in range(3):
        try:
            r = requests.post(url, headers={"x-goog-api-key": API_KEY}, json=payload, timeout=40)
        except requests.RequestException as e:
            last = f"Sin conexion con Google: {e}"
            time.sleep(1.2)
            continue
        if r.status_code == 200:
            try:
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                m = re.search(r"\{.*\}", text, re.DOTALL)
                return jsonify({"status": "ok", "data": clean(json.loads(m.group(0) if m else text))})
            except Exception as e:
                last = f"Respuesta inesperada de Gemini: {e}"
                break
        try:
            detail = r.json().get("error", {}).get("message", r.text)
        except ValueError:
            detail = r.text
        last = f"Gemini {r.status_code}: {detail[:200]}"
        if r.status_code == 400 and "thinking" in detail.lower():
            payload["generationConfig"].pop("thinkingConfig", None)
            continue
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
            time.sleep(1.5 * (attempt + 1))
            continue
        break
    return jsonify({"status": "error", "message": last}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
