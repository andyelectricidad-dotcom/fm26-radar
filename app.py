import os
from flask import Flask, render_template_string, jsonify, request
from PIL import Image
import json
import base64
import io
import re
from groq import Groq

app = Flask(__name__)

API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=API_KEY) if API_KEY else None

@app.route('/escanear', methods=['POST'])
def escanear():
    if not client: return jsonify({"status": "error", "message": "API Key no configurada."})
    
    try:
        data = request.json
        image_bytes = base64.b64decode(data.get("image", "").split(",", 1)[1])
        img = Image.open(io.BytesIO(image_bytes)).convert('L') # Blanco y negro
        img.thumbnail((800, 600), Image.Resampling.LANCZOS) # Resolución reducida para velocidad
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=50)
        final_image_url = f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"

        # Prompt optimizado para velocidad máxima
        prompt = "Extrae los atributos de FM26 de la imagen. Devuelve SOLO JSON. Atributos: 36. Si no hay valor, pon 0."

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": final_image_url}}]}],
            model="llama-3.2-11b-vision-preview",
            response_format={"type": "json_object"}, # ESTO ESTABILIZA EL TIEMPO
            temperature=0,
        )
        return jsonify({"status": "ok", "data": json.loads(chat_completion.choices[0].message.content)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/')
def inicio():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="es"><head><meta charset="UTF-8"><title>FM26 HUD Turbo</title><script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        :root { --bg:#06090e; --accent:#00e6a8; }
        body { background:var(--bg); color:#fff; font-family:sans-serif; margin:0; padding:20px; }
        .btn-scan { background:var(--accent); color:#000; padding:20px; font-weight:900; border-radius:10px; cursor:pointer; width:100%; border:none; font-size:18px; }
        .main { display:flex; gap:20px; }
        #radarChart { width:500px; height:500px; }
    </style></head>
    <body>
        <div class="main">
            <div style="flex:1">
                <button class="btn-scan" onclick="capturarPantalla()" id="btnScan">⚡ ANALIZAR FM26</button>
                <div id="radarChart"></div>
                <p id="debugText">Pulsa y selecciona la ventana de FM26.</p>
            </div>
            <div id="info" style="flex:1"></div>
        </div>
        <script>
            let videoStream = null; const videoElement = document.createElement('video'); videoElement.autoplay = true;
            async function capturarPantalla() {
                const btn = document.getElementById('btnScan');
                try {
                    btn.disabled = true;
                    if (!videoStream) {
                        videoStream = await navigator.mediaDevices.getDisplayMedia({video: {cursor:"never"}, audio:false});
                        videoElement.srcObject = videoStream;
                        await new Promise(r => videoElement.onplaying = r);
                    }
                    const canvas = document.createElement('canvas');
                    canvas.width = videoElement.videoWidth; canvas.height = videoElement.videoHeight;
                    canvas.getContext('2d').drawImage(videoElement, 0, 0);
                    const res = await fetch('/escanear', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({image:canvas.toDataURL('image/jpeg', 0.6)})});
                    const response = await res.json();
                    if(response.status==="ok") updateUI(response.data);
                    btn.disabled = false;
                } catch(e) { btn.disabled = false; document.getElementById('debugText').innerText = "Error: " + e; }
            }
            function updateUI(d) {
                document.getElementById('debugText').innerText = "✅ Análisis instantáneo.";
                // Aquí iría tu lógica de actualización de gráficos
            }
        </script>
    </body></html>
    """)

if __name__ == '__main__': app.run(host='0.0.0.0', port=5000, debug=False)
