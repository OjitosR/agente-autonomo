import os
import time
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
from google import genai
import resend

# 1. Configuración de clientes
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
resend.api_key = os.environ.get("RESEND_API_KEY")

# Lista de destinatarios en memoria
EMAIL_BASE = os.environ.get("EMAIL_DESTINO")
suscriptores = {EMAIL_BASE} if EMAIL_BASE else set()

# 2. Servidor web para Render y Webhooks de Stripe
class WebhookHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(f"Tech Alpha Intel activo. Suscriptores registrados: {len(suscriptores)}".encode('utf-8'))

    def do_POST(self):
        if self.path == "/webhook":
            longitud = int(self.headers.get('Content-Length', 0))
            cuerpo = self.rfile.read(longitud)
            try:
                evento = json.loads(cuerpo.decode('utf-8'))
                
                # Detectar suscripción pagada en Stripe
                if evento.get('type') == 'checkout.session.completed':
                    datos = evento['data']['object']
                    email_cliente = datos.get('customer_details', {}).get('email')
                    if email_cliente:
                        suscriptores.add(email_cliente)
                        print(f"🎉 Nuevo suscriptor registrado automaticamente: {email_cliente}")
                        
                        # Correo de bienvenida inmediato
                        resend.Emails.send({
                            "from": "onboarding@resend.dev",
                            "to": email_cliente,
                            "subject": "🚀 Bienvenido a Tech Alpha Intel",
                            "html": "<p>¡Tu suscripcion esta activa! Recibiras tu reporte de oportunidades cada manana.</p>"
                        })
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            except Exception as e:
                print(f"Error procesando webhook: {e}")
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

def iniciar_servidor_web():
    puerto = int(os.environ.get("PORT", 10000))
    servidor = HTTPServer(('0.0.0.0', puerto), WebhookHandler)
    print(f"Servidor web escuchando en el puerto {puerto}")
    servidor.serve_forever()

# 3. Extracción y análisis de mercado
def extraer_datos():
    url = "https://news.ycombinator.com/"
    resp = requests.get(url, timeout=10)
    sopa = BeautifulSoup(resp.text, 'html.parser')
    titulos = [el.text for el in sopa.find_all('span', class_='titleline')[:5]]
    return "\n".join(titulos)

def analizar_con_gemini(datos):
    prompt = f"Resume brevemente estas oportunidades o novedades destacando su angulo comercial:\n\n{datos}"
    modelos = ["gemini-3.6-flash", "gemini-3.1-pro-preview"]
    for modelo in modelos:
        for intento in range(2):
            try:
                respuesta = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                )
                return respuesta.text
            except Exception as e:
                print(f"Aviso con {modelo}: {e}. Pausa de 8s...")
                time.sleep(8)
    raise RuntimeError("No fue posible generar el informe.")

def ejecutar_tarea():
    try:
        print("Iniciando escaneo de mercado...")
        datos = extraer_datos()
        reporte = analizar_con_gemini(datos)
        
        destinatarios = list(suscriptores)
        if destinatarios:
            for correo in destinatarios:
                resend.Emails.send({
                    "from": "onboarding@resend.dev",
                    "to": correo,
                    "subject": "⚡ Tech Alpha Intel - Reporte Diario",
                    "html": f"<pre style='font-family: sans-serif; font-size: 14px;'>{reporte}</pre>"
                })
            print(f"Reporte enviado con exito a {len(destinatarios)} suscriptor(es).")
    except Exception as err:
        print(f"Error en ciclo de envio: {err}")

def bucle_agente():
    ejecutar_tarea()
    while True:
        time.sleep(86400)
        ejecutar_tarea()

if __name__ == "__main__":
    hilo = threading.Thread(target=bucle_agente, daemon=True)
    hilo.start()
    iniciar_servidor_web()
