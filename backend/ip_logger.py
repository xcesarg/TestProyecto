from flask import Flask, request, jsonify
from datetime import datetime
import requests
import json
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

@app.route('/')
def index():
    # Obtener IP: si X-Forwarded-For existe (detrás de proxy), sino usa remote_addr
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Recopilar información de cabeceras HTTP
    headers_info = {}
    for header, value in request.headers:
        headers_info[header] = value
    
    # Intentar obtener información geográfica
    try:
        geo = requests.get(f"http://ip-api.com/json/{ip}").json()
        location = f"{geo.get('city', 'Unknown')}, {geo.get('country', 'Unknown')} - ISP: {geo.get('isp', 'Unknown')}"
        geo_info = geo
    except Exception as e:
        location = "Geo info not available"
        geo_info = {"error": str(e)}
    
    # Registrar timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Crear registro completo
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
    
    # Guardar log en formato JSON para mejor procesamiento
    with open("logs.txt", "a") as f:
        f.write(f"[{timestamp}] IP: {ip} - {location}\n")
    
    # Guardar log detallado en formato JSON
    with open("detailed_logs.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    # Retornar una imagen transparente 1x1 para tracking pixel
    return '', 204

@app.route('/info', methods=['POST', 'OPTIONS'])
def info():
    # Manejar preflight requests para CORS
    if request.method == 'OPTIONS':
        return '', 204
    
    # Procesar datos recibidos del cliente
    try:
        data = request.json
        
        # Añadir información de cabeceras y IP
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Crear un registro completo
        log_entry = {
            "timestamp": timestamp,
            "ip": ip,
            "user_agent": request.headers.get('User-Agent', 'Unknown'),
            "data": data
        }
        
        # Guardar en formato legible
        with open("extra_info.txt", "a") as f:
            f.write(f"[{timestamp}] IP: {ip} - {json.dumps(data)}\n")
        
        # Guardar en formato JSON para mejor procesamiento
        with open("extra_info.json", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        return '', 204
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/logs')
def ver_logs():
    logs = ""
    
    # Verificar si hay parámetro de contraseña (básico, no seguro para producción)
    if request.args.get('password') != 'tu_contraseña_secreta':
        return "Acceso denegado. Se requiere contraseña.", 403
    
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

@app.route('/json-logs')
def json_logs():
    # Verificar si hay parámetro de contraseña (básico, no seguro para producción)
    if request.args.get('password') != 'tu_contraseña_secreta':
        return jsonify({"error": "Acceso denegado. Se requiere contraseña."}), 403
    
    # Leer logs JSON
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
    except Exception as e:
        pass
    
    try:
        if os.path.exists("extra_info.json"):
            with open("extra_info.json", "r") as f:
                for line in f:
                    try:
                        extra_info.append(json.loads(line))
                    except:
                        pass
    except Exception as e:
        pass
    
    return jsonify({
        "ip_logs": detailed_logs,
        "browser_info": extra_info
    })

# Ruta para servir un script JS para recolección de datos
@app.route('/collector.js')
def collector_script():
    script = """
    // Script de recolección de datos
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
            
            // Enviar datos al backend
            fetch('/info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        }
        
        // Ejecutar inmediatamente
        collectData();
        
        // También registrar eventos de interacción
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)