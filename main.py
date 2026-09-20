import os
import time
import requests
from bs4 import BeautifulSoup
from google import genai
import resend

# 1. Configuración de clientes
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
resend.api_key = os.environ.get("RESEND_API_KEY")
DESTINATARIO = os.environ.get("EMAIL_DESTINO")

def extraer_datos():
    url = "https://news.ycombinator.com/"
    resp = requests.get(url)
    sopa = BeautifulSoup(resp.text, 'html.parser')
    titulos = [el.text for el in sopa.find_all('span', class_='titleline')[:5]]
    return "\n".join(titulos)

def analizar_con_gemini(datos):
    prompt = f"Resume brevemente estas oportunidades o novedades destacando su ángulo comercial:\n\n{datos}"
    respuesta = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return respuesta.text

def ejecutar_tarea():
    print("Recolectando datos...")
    datos = extraer_datos()
    reporte = analizar_con_gemini(datos)
    
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": DESTINATARIO,
        "subject": "⚡ Radar Diario de Negocios - Reporte Autónomo",
        "html": f"<pre style='font-family: sans-serif; font-size: 14px;'>{reporte}</pre>"
    })
    print("Reporte enviado con éxito.")

if __name__ == "__main__":
    ejecutar_tarea()
    while True:
        time.sleep(86400)
        ejecutar_tarea()
