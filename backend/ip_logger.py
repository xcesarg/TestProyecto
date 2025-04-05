from flask import Flask, request, jsonify
from datetime import datetime
import requests
import json
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

# ----------- Función para obtener IP real -----------
def get_real_ip(req):
    """Intenta obtener la IP real del visitante, incluso detrás de un proxy o CDN."""
    for header in ['X-Forwarded-For', 'X-Real-IP', 'CF-Connecting-IP']:
        if header in req.headers:
            return req.headers[header].split(',')[0].strip()
    return req.remote_addr


# ----------- Ruta principal: pixel tracking invisible -----------
@app.route('/')
def index():
    ip = get_real_ip(request)
    
    headers_info = {header: value for header, value in request.headers}
    
    try:
        geo = requests.get(f"http://ip-api.com/json/{ip}").json()
        if geo.get("status") == "success":
            location = f"{geo.get('city', 'Unknown')}, {geo.get('country', 'Unknown')} - ISP: {geo.get('isp', 'Unknown')}"
        else:
            location = "Ubicación no disponible"
        geo_info = geo
    except Exception as e:
        location = "Error al obtener geolocalización"
        geo_info = {"error": str(e)}
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "timestamp": timestamp,
        "ip": ip,
        "location": location,
        "geo_info": geo_info,
        "headers": headers_info,
        "user_agent": request.headers.get('User-Agent', 'Unknown'),
        "method": request.method,
        "path": request.path,
        "query_params": dict(request.args),
        "cookies": dict(request.cookies)
    }
    
    with open("logs.txt", "a") as f:
        f.write(f"[{timestamp}] IP: {ip} - {location}\n")
    
    with open("detailed_logs.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    return '', 204  # Imagen transparente


# ----------- Ruta para recibir eventos o info del navegador -----------
@app.route('/info', methods=['POST', 'OPTIONS'])
def info():
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.json
        ip = get_real_ip(request)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_entry = {
            "timestamp": timestamp,
            "ip": ip,
            "user_agent": request.headers.get('User-Agent', 'Unknown'),
            "data": data
        }

        with open("extra_info.txt", "a") as f:
            f.write(f"[{timestamp}] IP: {ip} - {json.dumps(data)}\n")

        with open("extra_info.json", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        return '', 204
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return jsonify({"error": str(e)}), 400


# ----------- Ver logs en texto (protegido con contraseña) -----------
@app.route('/logs')
def ver_logs():
    if request.args.get('password') != 'tu_contraseña_secreta':
        return "Acceso denegado. Se requiere contraseña.", 403

    logs = ""

    try:
        with open("logs.txt", "r") as f:
            logs += "Logs de IP:\n" + f.read()
    except Exception as e:
        logs += f"No se pudo leer logs.txt: {str(e)}\n"

    try:
        with open("extra_info.txt", "r") as f:
            logs += "\nExtra Info:\n" + f.read()
    except Exception as e:
        logs += f"\nNo se pudo leer extra_info.txt: {str(e)}\n"

    return f"<pre>{logs}</pre>"


# ----------- Ver logs en JSON (protegido) -----------
@app.route('/json-logs')
def json_logs():
    if request.args.get('password') != 'tu_contraseña_secreta':
        return jsonify({"error": "Acceso denegado. Se requiere contraseña."}), 403

    detailed_logs = []
    extra_info = []

    try:
        if os.path.exists("detailed_logs.json"):
            with open("detailed_logs.json", "r") as f:
                for line in f:
                    try:
                        detailed_logs.append(json.loads(line))
                    except:
                        pass
    except:
        pass

    try:
        if os.path.exists("extra_info.json"):
            with open("extra_info.json", "r") as f:
                for line in f:
                    try:
                        extra_info.append(json.loads(line))
                    except:
                        pass
    except:
        pass

    return jsonify({
        "ip_logs": detailed_logs,
        "browser_info": extra_info
    })


# ----------- Servir el script JS de tracking -----------
@app.route('/collector.js')
def collector_script():
    script = """
    (function() {
        async function collectData() {
            const data = {
                url: window.location.href,
                title: document.title,
                referrer: document.referrer,
                cookies: document.cookie,
                screenSize: {
                    width: screen.width,
                    height: screen.height
                },
                windowSize: {
                    width: window.innerWidth,
                    height: window.innerHeight
                },
                colorDepth: screen.colorDepth,
                timestamp: new Date().toString(),
                timezoneOffset: new Date().getTimezoneOffset(),
                localStorage: Object.keys(localStorage).length,
                navigatorInfo: {
                    userAgent: navigator.userAgent,
                    language: navigator.language,
                    platform: navigator.platform,
                    doNotTrack: navigator.doNotTrack
                }
            };

            fetch('/info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        }

        collectData();

        document.addEventListener('click', function(e) {
            const clickData = {
                type: 'click',
                x: e.clientX,
                y: e.clientY,
                target: e.target.tagName,
                timestamp: new Date().toString()
            };

            fetch('/info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(clickData)
            });
        });
    })();
    """
    return script, 200, {'Content-Type': 'application/javascript'}


# ----------- Iniciar servidor -----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
