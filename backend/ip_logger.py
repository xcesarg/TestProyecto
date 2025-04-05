from flask import Flask, request
from datetime import datetime
import requests

app = Flask(__name__)

@app.route('/')
def index():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    try:
        geo = requests.get(f"http://ip-api.com/json/{ip}").json()
        location = f"{geo.get('city')}, {geo.get('country')} - ISP: {geo.get('isp')}"
    except:
        location = "Geo info not available"
    with open("logs.txt", "a") as f:
        f.write(f"[{datetime.now()}] IP: {ip} - {location}\n")
    return '', 204

@app.route('/info', methods=['POST'])
def info():
    data = request.json
    with open("extra_info.txt", "a") as f:
        f.write(f"[{datetime.now()}] {data}\n")
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
