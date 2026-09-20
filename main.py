import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
from google import genai
import resend

# 1. Configuración de accesos
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
resend.api_key = os.environ.get("RESEND_API_KEY")
DESTINATARIO = os.environ.get("EMAIL_DESTINO")

# 2. Servidor web mínimo para mantener Render activo y saludable
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Agente activo y operando 24/7.")

def iniciar_servidor_web():
    puerto = int(os.environ.get("PORT", 10000))
    servidor = HTTPServer(('0.0.0.0', puerto), HealthHandler)
    print(f"Servidor web escuchando en el puerto {puerto}")
    servidor.serve_forever()

# 3. Lógica del agente
def extraer_datos():
    url = "https://news.ycombinator.com/"
    resp = requests.get(url, timeout=10)
    sopa = BeautifulSoup(resp.text, 'html.parser')
    titulos = [el.text for el in sopa.find_all('span', class_='titleline')[:5]]
    return "\n".join(titulos)

def analizar_con_gemini(datos):
    prompt = f"Resume brevemente estas oportunidades o novedades destacando su ángulo comercial:\n\n{datos}"
    modelos = ["gemini-3.6-flash", "gemini-3.1-pro-preview"]
    
    for modelo in modelos:
        for intento in range(2):
            try:
                print(f"Consultando modelo {modelo} (intento {intento+1})...")
                respuesta = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                )
                return respuesta.text
            except Exception as e:
                print(f"Aviso con {modelo}: {e}. Pausa de 8s antes de reintentar...")
                time.sleep(8)
    raise RuntimeError("No fue posible obtener respuesta tras reintentar.")

def ejecutar_tarea():
    try:
        print("Recolectando datos...")
        datos = extraer_datos()
        print("Generando analisis con Gemini...")
        reporte = analizar_con_gemini(datos)
        
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": DESTINATARIO,
            "subject": "⚡ Radar Diario de Negocios - Reporte Autonomo",
            "html": f"<pre style='font-family: sans-serif; font-size: 14px;'>{reporte}</pre>"
        })
        print("Reporte enviado con exito.")
    except Exception as err:
        print(f"Error en el ciclo de envio: {err}")

def bucle_agente():
    ejecutar_tarea()
    while True:
        time.sleep(86400)
        ejecutar_tarea()

if __name__ == "__main__":
    # Arrancar el bucle del agente en un hilo independiente
    hilo = threading.Thread(target=bucle_agente, daemon=True)
    hilo.start()
    # Mantener el servidor HTTP principal activo para Render
    iniciar_servidor_web()
