import os
from flask import Flask, render_template_string, jsonify, request
from PIL import Image
import json
import base64
import io
import re
from google import genai
from google.genai import types

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=API_KEY) if API_KEY else None

@app.route('/escanear', methods=['POST'])
def escanear():
    if not client:
        return jsonify({"status": "error", "message": "API Key de Gemini no configurada en Render."})
    
    try:
        data = request.json
        image_data = data.get("image", "")
        
        header, encoded = image_data.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        prompt = """Extrae el perfil y los 36 atributos de esta imagen de Football Manager. 
Devuelve ÚNICAMENTE un objeto JSON.
Estructura exacta:
{"nombre":"","nacionalidad":"","valor":"","edad":"","equipo":"","salario":"","contrato":"","calidad":"","cabeceo":0,"centros":0,"control":0,"entradas":0,"marcaje":0,"pases":0,"regate":0,"remate":0,"tecnica":0,"tiros_lejanos":0,"penaltis":0,"saques_esquina":0,"saques_largos":0,"tiros_libres":0,"agresividad":0,"anticipacion":0,"colocacion":0,"concentracion":0,"decisiones":0,"desmarques":0,"determinacion":0,"juego_equipo":0,"liderazgo":0,"sacrificio":0,"serenidad":0,"talento":0,"valentia":0,"vision":0,"aceleracion":0,"agilidad":0,"salto":0,"equilibrio":0,"fuerza":0,"recuperacion":0,"resistencia":0,"velocidad":0}
Si no ves un dato, pon 0 o ""."""

        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[img, prompt],
            # Forzamos JSON nativo para máxima velocidad y evitar fallos
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0),
        )

        respuesta_texto = response.text
        match = re.search(r'\{.*\}', respuesta_texto, re.DOTALL)
        json_puro = match.group(0) if match else respuesta_texto
        
        return jsonify({"status": "ok", "data": json.loads(json_puro)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/')
def inicio():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>FM26 - Tactical Web HUD</title>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            :root { --bg-main: #06090e; --bg-panel: #0d131d; --accent: #00e6a8; --accent-hover: #00ffbc; --text-main: #e1e4e8; --text-muted: #8b949e; --border: #1f293d; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg-main); color: var(--text-main); margin: 0; padding: 2vh 2vw; height: 96vh; display: flex; flex-direction: column; }
            .header-panel { background: var(--bg-panel); border: 1px solid var(--border); border-left: 5px solid var(--accent); border-radius: 10px; padding: 20px 25px; margin-bottom: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
            .player-name { font-size: 2.2em; font-weight: 800; color: #fff; margin: 0 0 10px 0; letter-spacing: -0.5px; }
            .badge-container { display: flex; flex-wrap: wrap; gap: 12px; }
            .badge { background: #161f2e; color: var(--text-muted); font-size: 12px; padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border); display: flex; align-items: center; gap: 6px;}
            .badge span { color: #fff; font-weight: 600; }
            .badge-accent { border-color: rgba(0, 230, 168, 0.3); color: var(--accent); background: rgba(0, 230, 168, 0.05); }
            .badge-accent span { color: var(--accent); }
            .main-layout { display: flex; gap: 20px; flex-grow: 1; min-height: 0; }
            .left-panel { flex: 0 0 45%; display: flex; flex-direction: column; gap: 15px; }
            .btn-scan { background: linear-gradient(135deg, #00c690 0%, #009970 100%); color: #000; border: none; padding: 20px; font-size: 18px; font-weight: 800; border-radius: 10px; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; box-shadow: 0 8px 20px rgba(0, 230, 168, 0.2); transition: all 0.2s ease; display: flex; justify-content: center; align-items: center; gap: 10px;}
            .btn-scan:hover { background: linear-gradient(135deg, var(--accent-hover) 0%, #00b383 100%); transform: translateY(-2px); }
            .btn-scan:disabled { filter: grayscale(0.5); cursor: not-allowed; transform: none; }
            .radar-container { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 10px; flex-grow: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; padding: 20px;}
            #radarChart { width: 100%; height: 100%; max-height: 600px; display: flex; justify-content: center; align-items: center; overflow: visible; }
            .status-box { position: absolute; bottom: 15px; left: 15px; right: 15px; background: rgba(5,8,13,0.8); border: 1px solid var(--border); padding: 10px 15px; border-radius: 6px; font-family: monospace; font-size: 11px; color: var(--accent); display: flex; justify-content: space-between; }
            .right-panel { flex: 1; display: flex; gap: 15px; overflow-y: auto; padding-right: 5px;}
            .col { flex: 1; display: flex; flex-direction: column; gap: 15px; }
            .category-box { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 10px; padding: 15px; height: fit-content; }
            .category-box h4 { font-size: 1em; color: #fff; margin: 0 0 15px 0; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
            .input-item { display: flex; justify-content: space-between; align-items: center; background: #0b0f17; padding: 6px 10px; border-radius: 6px; margin-bottom: 6px; gap: 10px; }
            label { font-size: 11px; color: var(--text-muted); font-weight: 500; width: 85px; flex-shrink: 0; text-transform: uppercase;}
            input[type="range"] { flex-grow: 1; -webkit-appearance: none; background: #161f2e; height: 4px; border-radius: 2px; outline: none; }
            input[type="range"]::-webkit-slider-thumb { -webkit-appearance: none; width: 12px; height: 12px; border-radius: 50%; background: var(--accent); cursor: pointer; }
            .val-display { font-size: 14px; font-weight: 800; color: #fff; width: 22px; text-align: right; }
            ::-webkit-scrollbar { width: 6px; }::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="header-panel">
            <h2 id="pName" class="player-name">---</h2>
            <div class="badge-container">
                <div class="badge">Nacionalidad <span id="pNac">---</span></div>
                <div class="badge">Edad <span id="pEdad">---</span></div>
                <div class="badge">Equipo <span id="pEquipo">---</span></div>
                <div class="badge badge-accent">Calidad <span id="pCalidad">---</span></div>
                <div class="badge">Valor <span id="pVal">---</span></div>
                <div class="badge">Salario <span id="pSalario">---</span></div>
                <div class="badge">Contrato <span id="pContrato">---</span></div>
            </div>
        </div>
        <div class="main-layout">
            <div class="left-panel">
                <button class="btn-scan" onclick="capturarPantalla()" id="btnScan">⚡ Enlazar FM26 y Analizar</button>
                <div class="radar-container">
                    <div id="radarChart"></div>
                    <div class="status-box">
                        <span id="debugText">Listo para enlazar el juego. (Precisión Gemini IA)</span>
                        <span id="statsText" style="color: var(--text-muted);"></span>
                    </div>
                </div>
            </div>
            <div class="right-panel">
                <div class="col">
                    <div class="category-box">
                        <h4>⚽ Técnico</h4>
                        <div class="input-item"><label>Cabeceo</label><input type="range" id="cabeceo" min="1" max="20" value="10" oninput="updateVal(this, 'v_cabeceo')"><span id="v_cabeceo" class="val-display">-</span></div>
                        <div class="input-item"><label>Centros</label><input type="range" id="centros" min="1" max="20" value="10" oninput="updateVal(this, 'v_centros')"><span id="v_centros" class="val-display">-</span></div>
                        <div class="input-item"><label>Control</label><input type="range" id="control" min="1" max="20" value="10" oninput="updateVal(this, 'v_control')"><span id="v_control" class="val-display">-</span></div>
                        <div class="input-item"><label>Entradas</label><input type="range" id="entradas" min="1" max="20" value="10" oninput="updateVal(this, 'v_entradas')"><span id="v_entradas" class="val-display">-</span></div>
                        <div class="input-item"><label>Marcaje</label><input type="range" id="marcaje" min="1" max="20" value="10" oninput="updateVal(this, 'v_marcaje')"><span id="v_marcaje" class="val-display">-</span></div>
                        <div class="input-item"><label>Pases</label><input type="range" id="pases" min="1" max="20" value="10" oninput="updateVal(this, 'v_pases')"><span id="v_pases" class="val-display">-</span></div>
                        <div class="input-item"><label>Regate</label><input type="range" id="regate" min="1" max="20" value="10" oninput="updateVal(this, 'v_regate')"><span id="v_regate" class="val-display">-</span></div>
                        <div class="input-item"><label>Remate</label><input type="range" id="remate" min="1" max="20" value="10" oninput="updateVal(this, 'v_remate')"><span id="v_remate" class="val-display">-</span></div>
                        <div class="input-item"><label>Técnica</label><input type="range" id="tecnica" min="1" max="20" value="10" oninput="updateVal(this, 'v_tecnica')"><span id="v_tecnica" class="val-display">-</span></div>
                        <div class="input-item"><label>T. lejanos</label><input type="range" id="tiros_lejanos" min="1" max="20" value="10" oninput="updateVal(this, 'v_tiros_lejanos')"><span id="v_tiros_lejanos" class="val-display">-</span></div>
                    </div>
                    <div class="category-box">
                        <h4>⚡ Físico</h4>
                        <div class="input-item"><label>Aceleración</label><input type="range" id="aceleracion" min="1" max="20" value="10" oninput="updateVal(this, 'v_aceleracion')"><span id="v_aceleracion" class="val-display">-</span></div>
                        <div class="input-item"><label>Agilidad</label><input type="range" id="agilidad" min="1" max="20" value="10" oninput="updateVal(this, 'v_agilidad')"><span id="v_agilidad" class="val-display">-</span></div>
                        <div class="input-item"><label>Salto</label><input type="range" id="salto" min="1" max="20" value="10" oninput="updateVal(this, 'v_salto')"><span id="v_salto" class="val-display">-</span></div>
                        <div class="input-item"><label>Equilibrio</label><input type="range" id="equilibrio" min="1" max="20" value="10" oninput="updateVal(this, 'v_equilibrio')"><span id="v_equilibrio" class="val-display">-</span></div>
                        <div class="input-item"><label>Fuerza</label><input type="range" id="fuerza" min="1" max="20" value="10" oninput="updateVal(this, 'v_fuerza')"><span id="v_fuerza" class="val-display">-</span></div>
                        <div class="input-item"><label>Recup. física</label><input type="range" id="recuperacion" min="1" max="20" value="10" oninput="updateVal(this, 'v_recuperacion')"><span id="v_recuperacion" class="val-display">-</span></div>
                        <div class="input-item"><label>Resistencia</label><input type="range" id="resistencia" min="1" max="20" value="10" oninput="updateVal(this, 'v_resistencia')"><span id="v_resistencia" class="val-display">-</span></div>
                        <div class="input-item"><label>Velocidad</label><input type="range" id="velocidad" min="1" max="20" value="10" oninput="updateVal(this, 'v_velocidad')"><span id="v_velocidad" class="val-display">-</span></div>
                    </div>
                </div>
                <div class="col">
                    <div class="category-box">
                        <h4>🧠 Mental</h4>
                        <div class="input-item"><label>Agresividad</label><input type="range" id="agresividad" min="1" max="20" value="10" oninput="updateVal(this, 'v_agresividad')"><span id="v_agresividad" class="val-display">-</span></div>
                        <div class="input-item"><label>Anticipación</label><input type="range" id="anticipacion" min="1" max="20" value="10" oninput="updateVal(this, 'v_anticipacion')"><span id="v_anticipacion" class="val-display">-</span></div>
                        <div class="input-item"><label>Colocación</label><input type="range" id="colocacion" min="1" max="20" value="10" oninput="updateVal(this, 'v_colocacion')"><span id="v_colocacion" class="val-display">-</span></div>
                        <div class="input-item"><label>Concentración</label><input type="range" id="concentracion" min="1" max="20" value="10" oninput="updateVal(this, 'v_concentracion')"><span id="v_concentracion" class="val-display">-</span></div>
                        <div class="input-item"><label>Decisiones</label><input type="range" id="decisiones" min="1" max="20" value="10" oninput="updateVal(this, 'v_decisiones')"><span id="v_decisiones" class="val-display">-</span></div>
                        <div class="input-item"><label>Desmarques</label><input type="range" id="desmarques" min="1" max="20" value="10" oninput="updateVal(this, 'v_desmarques')"><span id="v_desmarques" class="val-display">-</span></div>
                        <div class="input-item"><label>Determinación</label><input type="range" id="determinacion" min="1" max="20" value="10" oninput="updateVal(this, 'v_determinacion')"><span id="v_determinacion" class="val-display">-</span></div>
                        <div class="input-item"><label>Juego equipo</label><input type="range" id="juego_equipo" min="1" max="20" value="10" oninput="updateVal(this, 'v_juego_equipo')"><span id="v_juego_equipo" class="val-display">-</span></div>
                        <div class="input-item"><label>Liderazgo</label><input type="range" id="liderazgo" min="1" max="20" value="10" oninput="updateVal(this, 'v_liderazgo')"><span id="v_liderazgo" class="val-display">-</span></div>
                        <div class="input-item"><label>Sacrificio</label><input type="range" id="sacrificio" min="1" max="20" value="10" oninput="updateVal(this, 'v_sacrificio')"><span id="v_sacrificio" class="val-display">-</span></div>
                        <div class="input-item"><label>Serenidad</label><input type="range" id="serenidad" min="1" max="20" value="10" oninput="updateVal(this, 'v_serenidad')"><span id="v_serenidad" class="val-display">-</span></div>
                        <div class="input-item"><label>Talento</label><input type="range" id="talento" min="1" max="20" value="10" oninput="updateVal(this, 'v_talento')"><span id="v_talento" class="val-display">-</span></div>
                        <div class="input-item"><label>Valentía</label><input type="range" id="valentia" min="1" max="20" value="10" oninput="updateVal(this, 'v_valentia')"><span id="v_valentia" class="val-display">-</span></div>
                        <div class="input-item"><label>Visión</label><input type="range" id="vision" min="1" max="20" value="10" oninput="updateVal(this, 'v_vision')"><span id="v_vision" class="val-display">-</span></div>
                    </div>
                    <div class="category-box">
                        <h4>🎯 Balón Parado</h4>
                        <div class="input-item"><label>Penaltis</label><input type="range" id="penaltis" min="1" max="20" value="10" oninput="updateVal(this, 'v_penaltis')"><span id="v_penaltis" class="val-display">-</span></div>
                        <div class="input-item"><label>S. esquina</label><input type="range" id="saques_esquina" min="1" max="20" value="10" oninput="updateVal(this, 'v_saques_esquina')"><span id="v_saques_esquina" class="val-display">-</span></div>
                        <div class="input-item"><label>S. largos</label><input type="range" id="saques_largos" min="1" max="20" value="10" oninput="updateVal(this, 'v_saques_largos')"><span id="v_saques_largos" class="val-display">-</span></div>
                        <div class="input-item"><label>T. libres</label><input type="range" id="tiros_libres" min="1" max="20" value="10" oninput="updateVal(this, 'v_tiros_libres')"><span id="v_tiros_libres" class="val-display">-</span></div>
                    </div>
                </div>
            </div>
        </div>
        <script>
            let videoStream = null;
            const videoElement = document.createElement('video');
            videoElement.autoplay = true;
            
            // Variables para el contador de tiempo medio
            let totalTime = 0;
            let scanCount = 0;

            const inputIds = ['cabeceo', 'centros', 'control', 'entradas', 'marcaje', 'pases', 'regate', 'remate', 'tecnica', 'tiros_lejanos', 'penaltis', 'saques_esquina', 'saques_largos', 'tiros_libres', 'agresividad', 'anticipacion', 'colocacion', 'concentracion', 'decisiones', 'desmarques', 'determinacion', 'juego_equipo', 'liderazgo', 'sacrificio', 'serenidad', 'talento', 'valentia', 'vision', 'aceleracion', 'agilidad', 'salto', 'equilibrio', 'fuerza', 'recuperacion', 'resistencia', 'velocidad'];
            let currentRadarData = {"Defensa":10, "Fisico":10, "Velocidad":10, "Vision":10, "Ataque":10, "Tecnica":10, "Juego Aereo":10, "Mental":10};
            const containerWidth = document.querySelector('.radar-container').clientWidth || 500;
            const containerHeight = document.querySelector('.radar-container').clientHeight || 500;
            const size = Math.min(containerWidth, containerHeight) * 0.95;
            const radius = size / 2 - 85; 
            const svg = d3.select("#radarChart").append("svg").attr("width", size).attr("height", size).attr("viewBox", `0 0 ${size} ${size}`).style("overflow", "visible").append("g").attr("transform", `translate(${size/2},${size/2})`);

            function drawRadar(datos_json) {
                svg.selectAll("*").remove();
                const keys = ["Defensa", "Fisico", "Velocidad", "Vision", "Ataque", "Tecnica", "Juego Aereo", "Mental"];
                const labels = {"Defensa": "Defensa", "Fisico": "Físico", "Velocidad": "Velocidad", "Vision": "Visión", "Ataque": "Ataque", "Tecnica": "Técnica", "Juego Aereo": "Aéreo", "Mental": "Mental"};
                const data = keys.map(key => ({ axis: key, value: datos_json[key] }));
                const angleSlice = Math.PI * 2 / data.length;
                const rScale = d3.scaleLinear().range([0, radius]).domain([0, 20]);
                for (let level = 1; level <= 4; level++) {
                    let r = radius * (level / 4);
                    let points = [];
                    for(let i=0; i<keys.length; i++) {
                        let a = angleSlice * i - Math.PI / 2;
                        points.push(`${r * Math.cos(a)},${r * Math.sin(a)}`);
                    }
                    svg.append("polygon").attr("points", points.join(" ")).style("fill", "none").style("stroke", "#1f293d").style("stroke-width", "1.5px");
                }
                for (let i = 0; i < keys.length; i++) {
                    let angle = angleSlice * i - Math.PI / 2;
                    svg.append("line").attr("x1", 0).attr("y1", 0).attr("x2", radius * Math.cos(angle)).attr("y2", radius * Math.sin(angle)).style("stroke", "#1f293d").style("stroke-width", "1.5px");
                }
                const radarLine = d3.lineRadial().curve(d3.curveLinearClosed).radius(d => rScale(d.value)).angle((d, i) => i * angleSlice);
                svg.append("path").datum(data).attr("d", radarLine).style("fill", "rgba(0, 230, 168, 0.25)").style("stroke", "#00e6a8").style("stroke-width", "3px");
                data.forEach((d, i) => {
                    const angle = angleSlice * i - Math.PI / 2;
                    svg.append("circle").attr("cx", rScale(d.value) * Math.cos(angle)).attr("cy", rScale(d.value) * Math.sin(angle)).attr("r", 5).style("fill", "#00e6a8");
                });
                data.forEach((d, i) => {
                    const radAngle = angleSlice * i - Math.PI / 2; 
                    let dist = radius + 30; 
                    if (Math.abs(Math.cos(radAngle)) < 0.1) dist = radius + 40; 
                    const x = dist * Math.cos(radAngle), y = dist * Math.sin(radAngle);
                    let anchor = "middle";
                    if (Math.abs(Math.cos(radAngle)) > 0.1) anchor = Math.cos(radAngle) > 0 ? "start" : "end";
                    const txtGroup = svg.append("text").attr("x", x).attr("y", y).attr("text-anchor", anchor);
                    txtGroup.append("tspan").attr("x", x).attr("dy", "-0.2em").style("font-size", "14px").style("fill", "#8b949e").style("font-weight", "600").text(labels[d.axis]);
                    txtGroup.append("tspan").attr("x", x).attr("dy", "1.2em").style("font-size", "18px").style("fill", "#00e6a8").style("font-weight", "900").text(d.value);
                });
            }

            function recalcularRadarLocal() {
                const v = (id) => parseInt(document.getElementById(id).value) || 10;
                currentRadarData = {
                    "Defensa": Math.round((v('marcaje') + v('entradas') + v('colocacion')) / 3),
                    "Fisico": Math.round((v('fuerza') + v('resistencia') + v('equilibrio') + v('recuperacion')) / 4),
                    "Velocidad": Math.round((v('aceleracion') + v('velocidad') + v('agilidad')) / 3),
                    "Vision": Math.round((v('vision') + v('anticipacion') + v('decisiones') + v('talento')) / 4),
                    "Ataque": Math.round((v('remate') + v('desmarques') + v('tiros_lejanos') + v('serenidad')) / 4),
                    "Tecnica": Math.round((v('tecnica') + v('control') + v('pases') + v('centros') + v('regate')) / 5),
                    "Juego Aereo": Math.round((v('salto') + v('cabeceo')) / 2),
                    "Mental": Math.round((v('determinacion') + v('concentracion') + v('liderazgo') + v('valentia') + v('juego_equipo') + v('sacrificio') + v('agresividad')) / 7)
                };
                drawRadar(currentRadarData);
            }

            async function capturarPantalla() {
                const status = document.getElementById('debugText');
                const stats = document.getElementById('statsText');
                const btn = document.getElementById('btnScan');
                try {
                    btn.disabled = true;
                    btn.style.opacity = "0.7";
                    if (!videoStream || !videoStream.active) {
                        status.innerText = "Selecciona SOLO la ventana de Football Manager...";
                        videoStream = await navigator.mediaDevices.getDisplayMedia({ video: { cursor: "never" }, audio: false });
                        videoElement.srcObject = videoStream;
                        await new Promise(resolve => videoElement.onplaying = resolve);
                        videoStream.getVideoTracks()[0].onended = () => { videoStream = null; btn.innerHTML = "⚡ Enlazar FM26 y Analizar"; };
                        btn.innerHTML = "⚡ Analizar al Instante";
                    }
                    status.innerText = "Enviando fotograma a la IA...";
                    const t0 = performance.now();
                    const canvas = document.createElement('canvas');
                    canvas.width = videoElement.videoWidth; canvas.height = videoElement.videoHeight;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
                    const res = await fetch('/escanear', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: canvas.toDataURL('image/jpeg', 0.95) })
                    });
                    const response = await res.json();
                    const t1 = performance.now();
                    const tiempo = ((t1 - t0) / 1000).toFixed(1);
                    
                    btn.disabled = false; btn.style.opacity = "1";
                    
                    if(response.status === "ok") {
                        scanCount++;
                        totalTime += parseFloat(tiempo);
                        const tiempoMedio = (totalTime / scanCount).toFixed(1);
                        
                        status.innerText = `✅ ¡Análisis en ${tiempo}s!`;
                        stats.innerText = `(Media: ${tiempoMedio}s | Total: ${scanCount})`;
                        actualizarUI(response.data);
                    } else {
                        status.innerText = "❌ " + response.message;
                    }
                } catch (err) {
                    btn.disabled = false; btn.style.opacity = "1"; videoStream = null;
                    btn.innerHTML = "⚡ Enlazar FM26 y Analizar";
                    status.innerText = "⚠️ Error de captura. Vuelve a intentarlo.";
                }
            }

            function actualizarUI(data) {
                document.getElementById('pName').innerText = data.nombre || "---";
                document.getElementById('pNac').innerText = data.nacionalidad || "---";
                document.getElementById('pEdad').innerText = data.edad || "---";
                document.getElementById('pEquipo').innerText = data.equipo || "---";
                document.getElementById('pCalidad').innerText = data.calidad || "---";
                document.getElementById('pVal').innerText = data.valor || "---";
                document.getElementById('pSalario').innerText = data.salario || "---";
                document.getElementById('pContrato').innerText = data.contrato || "---";
                inputIds.forEach(id => {
                    let val = data[id];
                    if (val !== undefined && val !== "" && val !== null) {
                        document.getElementById(id).value = val;
                        document.getElementById('v_' + id).innerText = val;
                    } else {
                        document.getElementById('v_' + id).innerText = "-";
                    }
                });
                recalcularRadarLocal();
            }

            function updateVal(slider, displayId) {
                document.getElementById(displayId).innerText = slider.value;
                recalcularRadarLocal();
            }

            drawRadar(currentRadarData);
        </script>
    </body>
    </html>
    """
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
