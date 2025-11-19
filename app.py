# ============================================
# IMPORTS
# ============================================
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect
import json
import re
import base64
from transcriber import Transcriber
from llm import LLM
from weather import Weather
from tts import TTS
from pc_command import PcCommand
import threading
import time
from datetime import datetime, timedelta
from pywebpush import webpush, WebPushException

load_dotenv()
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 

# ============================================
# 🎯 SISTEMA DE NOTIFICACIONES ALTERNATIVO (SIN VAPID)
# ============================================

# Suscripciones simples (solo IDs de sesión)
push_subscriptions = []

# Historial de notificaciones
notifications_history = []

# ⭐ DICCIONARIO GLOBAL PARA CONTROL DE NOTIFICACIONES ENVIADAS
product_notification_state = {}
product_expiry_notification_state = {}

print("🧹 Limpiando notificaciones iniciales...")
notifications_history.clear()

inventory = [
    {"id": 1, "name": "Arroz", "brand": "Diana", "category": "Granos", "stock": 25, "minStock": 10, "expiryDate": "2026-09-15"},
    {"id": 2, "name": "Frijoles", "brand": "La Constancia", "category": "Granos", "stock": 18, "minStock": 8, "expiryDate": "2026-04-15"},
    {"id": 3, "name": "Aceite", "brand": "Diana", "category": "Aceites", "stock": 12, "minStock": 5, "expiryDate": "2026-10-20"},
    {"id": 4, "name": "Azúcar", "brand": "Incauca", "category": "Endulzantes", "stock": 30, "minStock": 10, "expiryDate": "2026-05-30"},
    {"id": 5, "name": "Sal", "brand": "Refisal", "category": "Condimentos", "stock": 15, "minStock": 5, "expiryDate": "2026-12-31"},
    {"id": 6, "name": "Leche", "brand": "Colanta", "category": "Lácteos", "stock": 8, "minStock": 10, "expiryDate": "2025-11-25"},
    {"id": 7, "name": "Galletas", "brand": "Fest Chip", "category": "Snacks", "stock": 22, "minStock": 15, "expiryDate": "2025-12-15"},
    {"id": 8, "name": "Jabón", "brand": "Protex", "category": "Limpieza", "stock": 14, "minStock": 10, "expiryDate": "2027-03-15"},
    {"id": 9, "name": "Atún", "brand": "Van Camps", "category": "Enlatados", "stock": 15, "minStock": 8, "expiryDate": "2026-01-15"},
    {"id": 10, "name": "Café", "brand": "Sello Rojo", "category": "Bebidas", "stock": 20, "minStock": 10, "expiryDate": "2025-12-20"},
    {"id": 11, "name": "Pan", "brand": "Bimbo", "category": "Panadería", "stock": 5, "minStock": 10, "expiryDate": "2025-11-20"},
    {"id": 12, "name": "Huevos", "brand": "Granja San Martín", "category": "Lácteos", "stock": 30, "minStock": 12, "expiryDate": "2025-11-30"},
    {"id": 13, "name": "Pasta", "brand": "Zuko", "category": "Granos", "stock": 25, "minStock": 10, "expiryDate": "2025-12-10"},
    {"id": 14, "name": "Tomate", "brand": "Agrícola Fresco", "category": "Verduras", "stock": 8, "minStock": 15, "expiryDate": "2025-11-23"},
    {"id": 15, "name": "Cebolla", "brand": "Agrícola Fresco", "category": "Verduras", "stock": 12, "minStock": 10, "expiryDate": "2025-11-25"},
    {"id": 16, "name": "Papa", "brand": "Agrícola Fresco", "category": "Verduras", "stock": 40, "minStock": 20, "expiryDate": "2025-11-28"},
    {"id": 17, "name": "Zanahoria", "brand": "Agrícola Fresco", "category": "Verduras", "stock": 18, "minStock": 12, "expiryDate": "2025-11-30"},
    {"id": 18, "name": "Pollo", "brand": "Pollo Fresco", "category": "Carnes", "stock": 10, "minStock": 8, "expiryDate": "2025-11-19"},
    {"id": 19, "name": "Carne", "brand": "Carnes Premium", "category": "Carnes", "stock": 12, "minStock": 8, "expiryDate": "2025-11-21"},
    {"id": 20, "name": "Refresco", "brand": "Coca-Cola", "category": "Bebidas", "stock": 35, "minStock": 20, "expiryDate": "2026-01-30"},
    {"id": 21, "name": "Agua", "brand": "Cristal", "category": "Bebidas", "stock": 50, "minStock": 30, "expiryDate": "2027-11-30"},
    {"id": 22, "name": "Yogurt", "brand": "Alpina", "category": "Lácteos", "stock": 15, "minStock": 10, "expiryDate": "2025-11-28"},
    {"id": 23, "name": "Mantequilla", "brand": "Colanta", "category": "Lácteos", "stock": 8, "minStock": 5, "expiryDate": "2025-12-18"},
    {"id": 24, "name": "Queso", "brand": "Colanta", "category": "Lácteos", "stock": 10, "minStock": 8, "expiryDate": "2025-12-28"},
    {"id": 25, "name": "Shampoo", "brand": "Head & Shoulders", "category": "Higiene", "stock": 12, "minStock": 8, "expiryDate": "2027-06-30"},
    {"id": 26, "name": "Pasta Dental", "brand": "Colgate", "category": "Higiene", "stock": 18, "minStock": 10, "expiryDate": "2027-12-31"},
    {"id": 27, "name": "Papel Higiénico", "brand": "Familia", "category": "Higiene", "stock": 25, "minStock": 15, "expiryDate": "2028-06-30"},
    {"id": 28, "name": "Detergente", "brand": "Ariel", "category": "Limpieza", "stock": 10, "minStock": 8, "expiryDate": "2027-10-15"},
    {"id": 29, "name": "Servilletas", "brand": "Familia", "category": "Limpieza", "stock": 30, "minStock": 20, "expiryDate": "2027-12-31"},
    {"id": 30, "name": "Cereal", "brand": "Zucaritas", "category": "Desayuno", "stock": 14, "minStock": 10, "expiryDate": "2026-02-28"}
]

# Variable para el último comando
last_command_result = {
    "success": False,
    "message": "",
    "timestamp": 0
}

# Productos interactivos
interactive_products = {1, 6, 7, 9, 11, 20, 21}

# ============================================
# VARIABLES GLOBALES
# ============================================

transcriber = None
is_processing = False

# ============================================
# FUNCIÓN: GENERAR ACTIVIDADES DE EJEMPLO
# ============================================
def generate_sample_activities():
    """Generar actividades de ejemplo de los últimos días - CON MARCAS"""
    activities_list = []
    now = datetime.now()
    
    sample_data = [
        {
            "hours_ago": 1, 
            "type": "sell", 
            "product": "Pan", 
            "brand": "Bimbo",  # ✅ MARCA AGREGADA
            "text": "Venta registrada de 5 Pan marca Bimbo"
        },
        {
            "hours_ago": 2, 
            "type": "add", 
            "product": "Leche", 
            "brand": "Colanta",  # ✅ MARCA AGREGADA
            "text": "Se agregaron 10 unidades de Leche marca Colanta", 
            "expiryDate": "2025-11-25"
        },
        {
            "hours_ago": 3, 
            "type": "sell", 
            "product": "Refresco", 
            "brand": "Coca-Cola",  # ✅ MARCA AGREGADA
            "text": "Venta registrada de 8 Refresco marca Coca-Cola"
        },
        {
            "hours_ago": 4, 
            "type": "update", 
            "product": "Galletas", 
            "brand": "Fest Chip",  # ✅ MARCA AGREGADA
            "text": "Stock actualizado: Galletas marca Fest Chip de 15 a 22", 
            "expiryDate": "2025-12-15"
        },
        {
            "hours_ago": 5, 
            "type": "sell", 
            "product": "Huevos", 
            "brand": "Granja San Martín",  # ✅ MARCA AGREGADA
            "text": "Venta registrada de 12 Huevos marca Granja San Martín"
        },
        {
            "hours_ago": 26, 
            "type": "add", 
            "product": "Arroz", 
            "brand": "Diana",  # ✅ MARCA AGREGADA
            "text": "Se agregaron 20 unidades de Arroz marca Diana", 
            "expiryDate": "2026-09-15"
        },
        {
            "hours_ago": 28, 
            "type": "sell", 
            "product": "Café", 
            "brand": "Sello Rojo",  # ✅ MARCA AGREGADA
            "text": "Venta registrada de 3 Café marca Sello Rojo"
        },
        {
            "hours_ago": 50, 
            "type": "update", 
            "product": "Agua", 
            "brand": "Cristal",  # ✅ MARCA AGREGADA
            "text": "Stock actualizado: Agua marca Cristal de 30 a 50", 
            "expiryDate": "2027-11-30"
        }
    ]
    
    for item in sample_data:
        event_time = now - timedelta(hours=item["hours_ago"])
        
        activity = {
            "time": event_time.strftime("%H:%M"),
            "date": event_time.strftime("%d/%m/%Y"),
            "fullDate": event_time.isoformat(),
            "text": item["text"],
            "type": item["type"],
            "product": item["product"],
            "brand": item["brand"]  # ✅ MARCA INCLUIDA
        }
        
        # Agregar fecha de vencimiento si existe
        if "expiryDate" in item:
            activity["expiryDate"] = item["expiryDate"]
        
        activities_list.append(activity)
    
    return activities_list

# Inicializar actividades
activities = generate_sample_activities()

# ============================================
# FUNCIONES AUXILIARES - TIEMPO Y FECHA
# ============================================
def get_current_time():
    """Obtener hora actual en formato HH:MM"""
    return datetime.now().strftime("%H:%M")

def get_current_date():
    """Obtener fecha actual en formato DD/MM/YYYY"""
    return datetime.now().strftime("%d/%m/%Y")

def get_full_datetime():
    """Obtener fecha y hora completa en formato ISO"""
    return datetime.now().isoformat()

# ============================================
# FUNCIONES AUXILIARES - TEXTO Y VOZ
# ============================================
def clean_text_for_tts(text):
    """Limpiar texto para TTS - OPTIMIZADO"""
    import re
    
    # Formatear fechas primero
    text = format_dates_for_speech(text)
    
    # ⭐ MEJORA: Diccionario de reemplazos más completo
    replacements = {
        '✅': 'Listo',
        '💰': 'Venta',
        '📄': 'Actualizado',
        '📊': 'Reporte',
        '📦': 'Stock',
        '❌': 'Error',
        '⚠️': 'Atención',
        '🔍': 'Buscando',
        '🎯': 'Confirmado'
    }
    
    for emoji, word in replacements.items():
        text = text.replace(emoji, word)
    
    # Limpiar caracteres especiales
    text = re.sub(r'[^\w\s¡!¿?.,;:()\-áéíóúñÁÉÍÓÚÑ]', '', text)
    
    # Limpiar espacios múltiples
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def format_dates_for_speech(text):
    """Convertir fechas a formato hablado - OPTIMIZADO"""
    try:
        import re
        
        months = {
            '01': 'enero', '02': 'febrero', '03': 'marzo', '04': 'abril',
            '05': 'mayo', '06': 'junio', '07': 'julio', '08': 'agosto',
            '09': 'septiembre', '10': 'octubre', '11': 'noviembre', '12': 'diciembre'
        }
        
        def replace_date(match):
            day = match.group(1).lstrip('0') or '1'
            month_num = match.group(2).zfill(2)
            year = match.group(3)
            
            if len(year) == 2:
                year = "20" + year
            
            month_name = months.get(month_num, f"mes {month_num.lstrip('0')}")
            return f"{day} de {month_name} del {year}"
        
        # Patrón único optimizado
        text = re.sub(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})', replace_date, text)
        
        return text
        
    except Exception as e:
        print(f"⚠️ Error formateando fechas: {e}")
        return text

def format_single_date(day, month, year):
    """Formatear una fecha individual para voz"""
    months = {
        '01': 'enero', '02': 'febrero', '03': 'marzo', '04': 'abril',
        '05': 'mayo', '06': 'junio', '07': 'julio', '08': 'agosto',
        '09': 'septiembre', '10': 'octubre', '11': 'noviembre', '12': 'diciembre'
    }
    
    day = day.lstrip('0')
    month_num = month.zfill(2)
    month_name = months.get(month_num, f"mes {month_num.lstrip('0')}")
    
    if len(year) == 2:
        year = "20" + year
    
    return f"{day} de {month_name} del {year}"

def speak_response(text):
    """Generar y reproducir respuesta de voz - MEJORADO para fechas"""
    try:
        # Primero formatear fechas, luego limpiar para TTS
        formatted_text = format_dates_for_speech(text)
        clean_text = clean_text_for_tts(formatted_text)
        
        print(f"🔊 Hablando: {clean_text}")
        
        # Crear instancia de TTS y procesar
        tts = TTS()
        tts.process(clean_text)
        
        # Actualizar la interfaz después de hablar
        threading.Timer(1.0, update_interface).start()
        
    except Exception as e:
        print(f"❌ Error generando voz: {e}")
        import traceback
        traceback.print_exc()

def update_interface():
    """Actualizar la interfaz web después de un comando"""
    try:
        print("🔄 Actualizando interfaz web...")
        pass
    except Exception as e:
        print(f"⚠️ Error actualizando interfaz: {e}")

def improve_voice_recognition_quality():
    """Mostrar tips para mejorar el reconocimiento de voz"""
    print("🎧 Optimizando reconocimiento de voz...")
    
    tips = [
        "💡 Habla en un entorno tranquilo",
        "💡 Di 'Gwen' seguido inmediatamente de tu comando",
        "💡 Ejemplo: 'Gwen agrega 10 latas de atún'",
        "💡 Habla claro y a velocidad normal",
        "💡 Mantén el micrófono a 10-20 cm de tu boca"
    ]
    
    for tip in tips:
        print(tip)

def update_last_command(success, message, filters=None):
    """Actualizar el último comando procesado"""
    global last_command_result
    last_command_result = {
        "success": success,
        "message": message,
        "timestamp": time.time(),
        "filters": filters if filters else None
    }

# ============================================
# FUNCIONES DE SIMILITUD Y EXTRACCIÓN
# ============================================
def calculate_word_similarity(word1, word2):
    """Calcular similitud entre dos palabras usando múltiples métodos"""
    from difflib import SequenceMatcher
    
    # Método 1: SequenceMatcher
    similarity1 = SequenceMatcher(None, word1, word2).ratio()
    
    # Método 2: Letras comunes
    set1 = set(word1)
    set2 = set(word2)
    common = len(set1 & set2)
    total = len(set1 | set2)
    similarity2 = common / total if total > 0 else 0
    
    # Retornar promedio ponderado
    return (similarity1 * 0.6 + similarity2 * 0.4)

_product_cache = {}

def extract_product_from_command(command):
    """Extraer nombre de producto - OPTIMIZADO con caché"""
    try:
        if not command:
            return None
        
        command_lower = command.lower().strip()
        
        # ⭐ Revisar caché primero
        if command_lower in _product_cache:
            print(f"📦 Producto desde caché: '{_product_cache[command_lower]}'")
            return _product_cache[command_lower]
        
        print(f"🔍 Buscando producto en: '{command_lower}'")
        
        # ⭐ MEJORA: Diccionario optimizado con menos variantes (las más comunes)
        product_variants = {
            "Leche": ["leche", "leches"],
            "Pan": ["pan", "panes"],
            "Galletas": ["galletas", "galleta"],
            "Arroz": ["arroz"],
            "Atún": ["atún", "atun"],
            "Refresco": ["refresco", "gaseosa"],
            "Agua": ["agua"],
            "Café": ["café", "cafe"],
            "Huevos": ["huevos", "huevo"],
            "Azúcar": ["azúcar", "azucar"],
            "Frijoles": ["frijoles", "frijol"],
            "Aceite": ["aceite"],
            "Sal": ["sal"],
            "Jabón": ["jabón", "jabon"],
            "Pasta": ["pasta", "fideos"],
            "Tomate": ["tomate"],
            "Cebolla": ["cebolla"],
            "Papa": ["papa", "papas"],
            "Zanahoria": ["zanahoria"],
            "Pollo": ["pollo"],
            "Carne": ["carne"],
            "Yogurt": ["yogurt", "yogur"],
            "Mantequilla": ["mantequilla"],
            "Queso": ["queso"],
            "Shampoo": ["shampoo", "champú"],
            "Pasta Dental": ["pasta dental", "crema dental"],
            "Papel Higiénico": ["papel higiénico", "papel"],
            "Detergente": ["detergente"],
            "Servilletas": ["servilletas"],
            "Cereal": ["cereal"]
        }
        
        # BÚSQUEDA EXACTA PRIMERO (más rápido)
        for product_key, variants in product_variants.items():
            for variant in variants:
                if variant in command_lower:
                    print(f"🎯 Producto encontrado: '{product_key}' (variante: '{variant}')")
                    _product_cache[command_lower] = product_key
                    return product_key
        
        # ⭐ MEJORA: Búsqueda por palabras solo si no hubo coincidencia exacta
        # Y solo para palabras de 4+ caracteres
        words = [w for w in command_lower.split() if len(w) >= 4]
        for word in words:
            for product_key, variants in product_variants.items():
                for variant in variants:
                    if word in variant or variant in word:
                        print(f"🎯 Producto por palabra: '{product_key}' (palabra: '{word}')")
                        _product_cache[command_lower] = product_key
                        return product_key
        
        print(f"❌ No se detectó producto específico")
        return None
        
    except Exception as e:
        print(f"❌ Error extrayendo producto: {e}")
        return None

def extract_quantity_from_command(command):
    """Extraer cantidad - OPTIMIZADO"""
    try:
        # ⭐ MEJORA: Buscar números primero con regex más específico
        import re
        
        # Buscar patrones como "10 unidades", "5 kilos", etc.
        patterns = [
            r'(\d+)\s*(?:unidades?|kilos?|litros?|paquetes?|latas?|cajas?|bolsas?)?',
            r'(\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, command.lower())
            if matches:
                quantity = int(matches[0])
                print(f"🔢 Cantidad detectada: {quantity}")
                return quantity
        
        # Palabras numéricas (solo las más comunes)
        number_words = {
            'un': 1, 'una': 1, 'uno': 1,
            'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
            'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9,
            'diez': 10, 'doce': 12, 'docena': 12,
            'quince': 15, 'veinte': 20
        }
        
        words = command.lower().split()
        for word in words:
            if word in number_words:
                quantity = number_words[word]
                print(f"🔢 Cantidad (palabra): {quantity}")
                return quantity
        
        print(f"🔢 Sin cantidad, usando: 1")
        return 1
        
    except Exception as e:
        print(f"⚠️ Error extrayendo cantidad: {e}")
        return 1

def parse_date_from_command(command):
    """Extraer fecha del comando de voz"""
    try:
        if 'hoy' in command:
            return datetime.now().strftime("%d/%m/%Y")
        elif 'ayer' in command:
            return (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        
        return None
        
    except Exception as e:
        print(f"❌ Error parseando fecha: {e}")
        return None

def extract_brand_from_command(command):
    """Extraer marca - OPTIMIZADO"""
    try:
        if not command:
            return None
            
        command_lower = command.lower().strip()
        print(f"🔍 Buscando MARCA en: '{command_lower}'")
        
        import re
        
        # ⭐ MEJORA: Patrones más específicos
        brand_patterns = [
            r'marca\s+(\w+)',
            r'de\s+(?:la\s+)?marca\s+(\w+)'
        ]
        
        for pattern in brand_patterns:
            match = re.search(pattern, command_lower)
            if match:
                brand = match.group(1).strip().title()
                # ⭐ Lista de palabras a excluir (más completa)
                excluded = {
                    'agregar', 'añadir', 'vender', 'actualizar', 
                    'stock', 'unidades', 'la', 'el', 'de', 'que'
                }
                if brand.lower() not in excluded and len(brand) >= 3:
                    print(f"🎯 Marca encontrada: '{brand}'")
                    return brand
        
        print(f"⚠️ No se detectó marca")
        return None
        
    except Exception as e:
        print(f"❌ Error extrayendo marca: {e}")
        return None

def extract_expiry_date_from_command(command):
    """Extraer fecha de vencimiento - OPTIMIZADO"""
    try:
        if not command:
            return None
            
        command_lower = command.lower().strip()
        print(f"🔍 Buscando FECHA en: '{command_lower}'")
        
        import re
        from datetime import datetime
        
        # ⭐ MEJORA: Patrones más específicos en orden de prioridad
        date_patterns = [
            # Formato DD/MM/YYYY o DD-MM-YYYY
            (r'(?:venc[e|en]|caduc[a|an]|expir[a|an])[^\d]*(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})', 'numeric'),
            
            # Formato "25 de diciembre de 2025"
            (r'(?:venc[e|en]|caduc[a|an])[^\d]*(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(?:de\s+|del\s+)?(\d{4})', 'text'),
            
            # Formato flexible para cualquier fecha cercana
            (r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})', 'numeric_loose')
        ]
        
        months = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        
        for pattern, format_type in date_patterns:
            match = re.search(pattern, command_lower)
            if match:
                try:
                    groups = match.groups()
                    
                    if format_type == 'numeric' or format_type == 'numeric_loose':
                        day = groups[0].zfill(2)
                        month = groups[1].zfill(2)
                        year = groups[2]
                        if len(year) == 2:
                            year = "20" + year
                        
                        # ⭐ Validación básica de fecha
                        try:
                            datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y")
                            formatted_date = f"{day}/{month}/{year}"
                            print(f"✅ Fecha numérica: '{formatted_date}'")
                            return formatted_date
                        except ValueError:
                            print(f"⚠️ Fecha inválida: {day}/{month}/{year}")
                            continue
                    
                    elif format_type == 'text':
                        day = groups[0].zfill(2)
                        month_text = groups[1].lower()
                        year = groups[2]
                        
                        if month_text in months:
                            month = months[month_text]
                            formatted_date = f"{day}/{month}/{year}"
                            print(f"✅ Fecha textual: '{formatted_date}'")
                            return formatted_date
                
                except Exception as e:
                    print(f"⚠️ Error procesando fecha: {e}")
                    continue
        
        print(f"⚠️ No se detectó fecha de vencimiento")
        return None
        
    except Exception as e:
        print(f"❌ Error extrayendo fecha: {e}")
        return None

# ============================================
# FUNCIÓN PRINCIPAL: PROCESAR COMANDOS DE VOZ
# ============================================
def process_voice_command_internal(command):
    """Procesar comando de voz internamente"""
    global is_processing
    
    if is_processing:
        print("⚠️ Ya se está procesando un comando, ignorando...")
        return
    
    is_processing = True
    
    try:
        command = command.lower().strip()
        print(f"🎯 Procesando comando: {command}")
        
        # Limpiar wake words del comando
        wake_words_to_clean = [
            'gwen', 'guen', 'wen', 'when', 'buen', 'bwen',
            'bendy', 'bendi', 'wendy', 'wendi', 'vendi', 'vendy'
        ]
        
        for wake_word in wake_words_to_clean:
            if command.startswith(wake_word + ' '):
                command = command[len(wake_word):].strip()
                print(f"🧹 Limpiado '{wake_word}': '{command}'")
                break
            elif command.startswith(wake_word):
                command = command[len(wake_word):].strip()
                print(f"🧹 Limpiado '{wake_word}': '{command}'")
                break
        
        if command.startswith('o '):
            command = command[2:].strip()
        
        print(f"🔍 Comando limpio: '{command}'")
        
        # ============================================
        # COMANDO: MOSTRAR MOVIMIENTOS/FILTROS - MEJORADO
        # ============================================
        if any(word in command for word in ["muestra", "mostrar", "ver", "consultar", "buscar", "filtra", "filtrar", "historial"]):
            print("🔍 Detectado comando de consulta/filtros")
        
            # Determinar tipo de filtro
            filter_type = "all"
            if any(word in command for word in ["salida", "salidas", "venta", "ventas", "vendido", "vendí", "ventas de", "vendimos"]):
                filter_type = "sell"
                print("🎯 Filtro tipo: VENTAS")
            elif any(word in command for word in ["entrada", "entradas", "agregado", "agregados", "compra", "compras", "agregar", "añadido"]):
                filter_type = "add"
                print("🎯 Filtro tipo: ENTRADAS")
            elif any(word in command for word in ["actualización", "actualizaciones", "actualizado", "modificado", "cambiado"]):
                filter_type = "update"
                print("🎯 Filtro tipo: ACTUALIZACIONES")
            
            # Buscar producto específico
            filter_product = "all"
            product_name = extract_product_from_command(command)
            if product_name:
                filter_product = product_name.title()
                print(f"🎯 Producto filtrado: {filter_product}")
            
            # Buscar fecha
            filter_date = "all"
            specific_date = parse_date_from_command(command)
            
            if specific_date:
                filter_date = "specific"
                print(f"🎯 Fecha específica: {specific_date}")
            elif 'hoy' in command:
                filter_date = "today"
                print("🎯 Filtro fecha: HOY")
            elif any(word in command for word in ['semana', 'última semana', 'últimos 7 días']):
                filter_date = "week"
                print("🎯 Filtro fecha: ÚLTIMA SEMANA")
            elif any(word in command for word in ['mes', 'último mes', 'últimos 30 días']):
                filter_date = "month"
                print("🎯 Filtro fecha: ÚLTIMO MES")
            
            # Construir mensaje para el usuario
            parts = []
            if filter_type != "all":
                type_names = {"sell": "ventas", "add": "entradas", "update": "actualizaciones"}
                parts.append(type_names[filter_type])
            else:
                parts.append("movimientos")
            
            if filter_product != "all":
                parts.append(f"de {filter_product}")
            
            if filter_date == "today":
                parts.append("de hoy")
            elif filter_date == "week":
                parts.append("de la última semana")
            elif filter_date == "month":
                parts.append("del último mes")
            elif filter_date == "specific" and specific_date:
                parts.append(f"del {specific_date}")
            
            message = f"Mostrando {' '.join(parts)} en el historial"
            
            # ENVIAR FILTROS PARA APLICACIÓN AUTOMÁTICA
            filters_data = {
                "type": filter_type,
                "product": filter_product,
                "date": filter_date,
                "specific_date": specific_date,
                "open_tab": "inventory-tab"
            }
            if not product_name:
                filters_data["product"] = "all"

            # Igual con fecha
            if not specific_date and filter_date == "all":
                filters_data["date"] = "all"
            
            print(f"🎯 FILTROS APLICADOS: {filters_data}")
            
            update_last_command(True, message, filters_data)
            speak_response(message)
            
            # Forzar actualización de la interfaz
            threading.Timer(0.5, update_interface).start()
            return
        
        # ============================================
        # COMANDO: AGREGAR PRODUCTO - CON VALIDACIÓN OBLIGATORIA
        # ============================================
        elif any(word in command for word in ["agrega", "añade", "agregar", "pon", "meter", "mete"]):
            quantity = extract_quantity_from_command(command)
            product_name = extract_product_from_command(command)
            brand = extract_brand_from_command(command)
            expiry_date = extract_expiry_date_from_command(command)
            
            print(f"🔍 EXTRAÍDOS - Producto: '{product_name}', Cantidad: {quantity}, Marca: '{brand}', Fecha: '{expiry_date}'")
            
            # VALIDACIÓN OBLIGATORIA: Verificar que TODOS los datos estén presentes
            missing_fields = []
            if not product_name:
                missing_fields.append("nombre del producto")
            if not brand:
                missing_fields.append("marca")
            if not expiry_date:
                missing_fields.append("fecha de vencimiento")
            
            if missing_fields:
                # Construir mensaje de error específico
                if len(missing_fields) == 1:
                    error_msg = f"Falta el dato obligatorio: {missing_fields[0]}"
                else:
                    error_msg = f"Faltan los datos obligatorios: {', '.join(missing_fields)}"
                
                error_msg += ". Por ejemplo: 'agrega 10 galletas marca María que vencen el 25/12/2025'"
                
                print(f"❌ {error_msg}")
                update_last_command(False, error_msg)
                speak_response(error_msg)
            else:
                # Todos los datos presentes - Proceder con el agregado
                existing_product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
                
                if existing_product:
                    # Actualizar stock existente
                    existing_product["stock"] += quantity
                    message = f"Se agregaron {quantity} unidades de {existing_product['name']} marca {brand}, vence el {expiry_date}"
                    product_id = existing_product["id"]
                else:
                    # Crear nuevo producto completo
                    new_product = {
                        "id": len(inventory) + 1,
                        "name": product_name.title(),
                        "brand": brand,
                        "expiryDate": expiry_date,
                        "category": "General",
                        "stock": quantity,
                        "minStock": 5
                    }
                    inventory.append(new_product)
                    message = f"Nuevo producto agregado: {product_name.title()} marca {brand}, {quantity} unidades, vence el {expiry_date}"
                    product_id = new_product["id"]
                
                # Registrar actividad CON MARCA Y FECHA
                activities.insert(0, {
                    "time": get_current_time(),
                    "date": get_current_date(),
                    "fullDate": get_full_datetime(),
                    "text": message,
                    "type": "add",
                    "product": existing_product['name'] if existing_product else product_name.title(),
                    "brand": brand,
                    "expiryDate": expiry_date
                })
                
                interactive_products.add(product_id)
                update_last_command(True, message)
                speak_response(message)

        # ============================================
        # COMANDO: VENDER PRODUCTO - CON VALIDACIÓN OBLIGATORIA DE MARCA
        # ============================================
        elif any(word in command for word in ["vendí", "vender", "vendido", "vendimos", "vende"]):
            product_name = extract_product_from_command(command)
            quantity = extract_quantity_from_command(command)
            brand = extract_brand_from_command(command)
            
            print(f"🔍 EXTRAÍDOS - Producto: '{product_name}', Cantidad: {quantity}, Marca: '{brand}'")
            
            # VALIDACIÓN OBLIGATORIA
            missing_fields = []
            if not product_name:
                missing_fields.append("nombre del producto")
            if not quantity:
                missing_fields.append("cantidad")
            if not brand:
                missing_fields.append("marca")
            
            if missing_fields:
                if len(missing_fields) == 1:
                    error_msg = f"Falta el dato obligatorio para registrar la venta: {missing_fields[0]}"
                else:
                    error_msg = f"Faltan los datos obligatorios para registrar la venta: {', '.join(missing_fields)}"
                
                error_msg += ". Por ejemplo: 'vendí 5 galletas marca María'"
                
                print(f"❌ {error_msg}")
                update_last_command(False, error_msg)
                speak_response(error_msg)
            else:
                # Buscar producto específico con marca
                product = next((p for p in inventory if p["name"].lower() == product_name.lower() and p.get("brand", "").lower() == brand.lower()), None)
                
                # Si no encuentra con marca exacta, busca solo por nombre (compatibilidad)
                if not product:
                    product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
                
                if not product:
                    error_msg = f"Producto '{product_name}' marca {brand} no encontrado en el inventario"
                    update_last_command(False, error_msg)
                    speak_response(error_msg)
                elif product["stock"] < quantity:
                    error_msg = f"No hay suficiente stock de {product['name']} marca {brand}. Stock actual: {product['stock']} unidades"
                    update_last_command(False, error_msg)
                    speak_response(error_msg)
                else:
                    product["stock"] -= quantity
                    message = f"Venta registrada: {quantity} unidades de {product['name']} marca {brand}"
                    
                    # ✅ REGISTRAR MARCA EN LA ACTIVIDAD
                    activities.insert(0, {
                        "time": get_current_time(),
                        "date": get_current_date(),
                        "fullDate": get_full_datetime(),
                        "text": message,
                        "type": "sell",
                        "product": product['name'],
                        "brand": brand  # ✅ Marca incluida
                    })
                    
                    interactive_products.add(product["id"])
                    update_last_command(True, message)
                    speak_response(message)
        
        # ============================================
        # COMANDO: ACTUALIZAR STOCK
        # ============================================
        elif any(word in command for word in ["actualiza", "actualizar", "cambia", "cambiar", "modifica"]):
            product_name = extract_product_from_command(command)
            quantity = extract_quantity_from_command(command)
            brand = extract_brand_from_command(command)
            
            print(f"🔍 Extraído - Producto: '{product_name}', Cantidad: {quantity}, Marca: '{brand}'")
            
            if product_name and quantity:
                product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
                
                if product:
                    old_stock = product["stock"]
                    product["stock"] = quantity
                    
                    # Si no se especificó marca, usar la del producto existente
                    final_brand = brand if brand else product.get("brand", "Sin marca")
                    
                    message = f"Stock actualizado: {product['name']} marca {final_brand} de {old_stock} a {quantity} unidades"
                    
                    # ✅ REGISTRAR MARCA EN LA ACTIVIDAD
                    activities.insert(0, {
                        "time": get_current_time(),
                        "date": get_current_date(),
                        "fullDate": get_full_datetime(),
                        "text": message,
                        "type": "update",
                        "product": product['name'],
                        "brand": final_brand  # ✅ Marca incluida
                    })
                    
                    interactive_products.add(product["id"])
                    update_last_command(True, message)
                    speak_response(message)
                else:
                    error_msg = f"Producto '{product_name}' no encontrado"
                    update_last_command(False, error_msg)
                    speak_response(error_msg)
            else:
                error_msg = "No entendí qué producto o cantidad actualizar. Ejemplo: actualiza el stock de leche a 15"
                update_last_command(False, error_msg)
                speak_response(error_msg)
        
        # ============================================
        # COMANDO: CONSULTAR INVENTARIO GENERAL
        # ============================================
        elif any(word in command for word in ["inventario", "stock", "productos", "existencias"]):
            total = len(inventory)
            low_stock = len([p for p in inventory if p["stock"] <= p["minStock"]])
            message = f"Tienes {total} productos en inventario. {low_stock} productos con stock bajo."
            update_last_command(True, message)
            speak_response(message)
        
        # ============================================
        # COMANDO: CONSULTAR STOCK DE PRODUCTO ESPECÍFICO
        # ============================================
        elif any(word in command for word in ["cuánto", "cuanto", "stock de", "hay de"]):
            product_name = extract_product_from_command(command)
            
            if product_name:
                product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
                if product:
                    stock_status = "BAJO" if product["stock"] <= product["minStock"] else "OK"
                    message = f"{product['name']}: {product['stock']} unidades. Mínimo: {product['minStock']}. Estado: {stock_status}"
                    update_last_command(True, message)
                    speak_response(message)
                else:
                    error_msg = f"Producto '{product_name}' no encontrado"
                    update_last_command(False, error_msg)
                    speak_response(error_msg)
            else:
                error_msg = "No entendí de qué producto quieres saber el stock. Ejemplo: cuánto stock hay de galletas"
                update_last_command(False, error_msg)
                speak_response(error_msg)
        # ============================================
        # COMANDO: APAGAR SISTEMA GWEN
        # ============================================
        elif any(word in command for word in ["apagar", "apágate", "apagate", "pagar", "pagate", "desactivar", "detener", "stop", "adiós", "adios", "chao", "bye"]):
            message = "Sistema Gwen apagándose. Hasta pronto."
            print(f"👋 {message}")
            update_last_command(True, message)
            speak_response(message)
            
            # Detener el sistema de voz después de hablar
            def stop_system_delayed():
                time.sleep(2)  # Esperar a que termine de hablar
                global transcriber, is_processing
                if transcriber:
                    transcriber.stop_all()
                    transcriber = None
                is_processing = False
                print("🔴 Sistema Gwen detenido completamente")
                
                # ⭐ NUEVO: Marcar que el sistema fue detenido por voz
                update_last_command(True, "SYSTEM_STOPPED", {"action": "stop_voice_system"})
            
            threading.Thread(target=stop_system_delayed, daemon=True).start()
            return
        
        # ============================================
        # COMANDO NO RECONOCIDO
        # ============================================
        else:
            error_msg = f"No entendí el comando: '{command}'. Puedo ayudarte con: agregar, vender, actualizar stock, consultar inventario o mostrar movimientos"
            update_last_command(False, error_msg)
            speak_response(error_msg)
    
    except Exception as e:
        print(f"❌ Error procesando comando: {e}")
        import traceback
        traceback.print_exc()
        error_msg = "Hubo un error procesando tu comando. Intenta de nuevo."
        update_last_command(False, error_msg)
        speak_response(error_msg)
    
    finally:
        is_processing = False

# ============================================
# RUTAS FLASK - INTERFAZ WEB
# ============================================

@app.route("/")
@app.route("/welcome")
def landing():
    """Ruta de bienvenida/landing page"""
    return render_template("landing.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Ruta de inicio de sesión"""
    if request.method == "POST":
        # Aquí iría la lógica de autenticación real
        # Por ahora, simplemente redirigimos a gwen.html
        return redirect("/gwen")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Ruta de registro"""
    if request.method == "POST":
        # Aquí iría la lógica de registro real
        # Por ahora, simplemente redirigimos al login
        return redirect("/login")
    return render_template("register.html")

@app.route("/terminos")
def terminos():
    return render_template("terminos.html")

@app.route("/politicas")
def politicas():
    return render_template("politicas.html")

@app.route("/gwen")
def gwen():
    """Ruta principal de la interfaz Gwen"""
    return render_template("gwen.html")

# ============================================
# RUTAS API - INVENTARIO
# ============================================

@app.route("/api/inventory", methods=["GET"])
def get_inventory():
    """Obtener todo el inventario"""
    return jsonify(inventory)

@app.route("/api/interactive-products", methods=["GET"])
def get_interactive_products():
    """Obtener solo productos con actividad reciente"""
    interactive_list = [p for p in inventory if p["id"] in interactive_products]
    print(f"🎯 Productos interactivos solicitados: {len(interactive_list)}")
    return jsonify(interactive_list)
        
@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Obtener alertas de stock bajo Y productos próximos a vencer"""
    try:
        # Alertas de stock bajo
        low_stock_alerts = []
        for product in inventory:
            if product["stock"] <= product["minStock"]:
                urgency = "CRÍTICO" if product["stock"] == 0 else "ALTO" if product["stock"] <= product["minStock"] // 2 else "MEDIO"
                low_stock_alerts.append({
                    "id": product["id"],
                    "name": product["name"],
                    "brand": product.get("brand", "Sin marca"),
                    "stock": product["stock"],
                    "minStock": product["minStock"],
                    "expiryDate": product.get("expiryDate"),
                    "urgency": urgency
                })
        
        # Alertas de vencimiento (30 días o menos)
        expiring_alerts = []
        today_date = datetime.now()
        
        for product in inventory:
            if product.get("expiryDate"):
                try:
                    expiry_date = datetime.strptime(product["expiryDate"], "%Y-%m-%d")
                    days_until_expiry = (expiry_date - today_date).days
                    
                    if 0 < days_until_expiry <= 30:
                        urgency = "CRÍTICO" if days_until_expiry <= 7 else "ALTO" if days_until_expiry <= 15 else "MEDIO"
                        expiring_alerts.append({
                            "id": product["id"],
                            "name": product["name"],
                            "brand": product.get("brand", "Sin marca"),
                            "expiryDate": product["expiryDate"],
                            "daysUntilExpiry": days_until_expiry,
                            "urgency": urgency
                        })
                except:
                    continue
        
        return jsonify({
            "lowStock": low_stock_alerts,
            "expiring": expiring_alerts
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo alertas: {e}")
        return jsonify({"lowStock": [], "expiring": []})
    
@app.route("/api/inventory/add", methods=["POST"])
def add_product():
    """Agregar producto al inventario"""
    try:
        data = request.json
        product_name = data.get("name")
        quantity = data.get("quantity", 1)
        category = data.get("category", "General")
        
        existing_product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
        
        if existing_product:
            existing_product["stock"] += quantity
            message = f"✅ Se agregaron {quantity} unidades de {existing_product['name']}. Stock actual: {existing_product['stock']} unidades"
            product_id = existing_product["id"]
        else:
            new_product = {
                "id": len(inventory) + 1,
                "name": product_name.title(),
                "category": category,
                "stock": quantity,
                "minStock": 5
            }
            inventory.append(new_product)
            message = f"✅ Se agregó nuevo producto: {product_name.title()} con {quantity} unidades"
            product_id = new_product["id"]
        
        activities.insert(0, {
            "time": get_current_time(),
            "date": get_current_date(),
            "fullDate": get_full_datetime(),
            "text": message,
            "type": "add",
            "product": existing_product['name'] if existing_product else product_name.title()
        })
        
        interactive_products.add(product_id)

        threading.Thread(target=notify_system_event, args=(message,), daemon=True).start()
        
        return jsonify({"success": True, "message": message, "inventory": inventory})
    
    except Exception as e:
        print(f"❌ Error agregando producto: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/inventory/sell", methods=["POST"])
def sell_product():
    """Registrar venta de producto"""
    try:
        data = request.json
        product_name = data.get("name")
        quantity = data.get("quantity", 1)
        brand = data.get("brand", "Sin marca")  # ✅ Obtener marca
        
        product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
        
        if not product:
            return jsonify({"success": False, "message": f"❌ Producto '{product_name}' no encontrado"}), 404
        
        if product["stock"] < quantity:
            return jsonify({"success": False, "message": f"❌ No hay suficiente stock"}), 400
        
        product["stock"] -= quantity
        
        # Si no se proporcionó marca, usar la del producto
        final_brand = brand if brand != "Sin marca" else product.get("brand", "Sin marca")
        
        message = f"💰 Venta registrada: {quantity} unidades de {product['name']} marca {final_brand}"
        
        # ✅ REGISTRAR MARCA EN LA ACTIVIDAD
        activities.insert(0, {
            "time": get_current_time(),
            "date": get_current_date(),
            "fullDate": get_full_datetime(),
            "text": message,
            "type": "sell",
            "product": product['name'],
            "brand": final_brand  # ✅ Marca incluida
        })
        
        interactive_products.add(product["id"])
        threading.Thread(target=notify_sale, args=(product, quantity), daemon=True).start()
        
        return jsonify({"success": True, "message": message})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

        
@app.route("/api/inventory/update", methods=["POST"])
def update_stock():
    """Actualizar stock de producto"""
    try:
        data = request.json
        product_name = data.get("name")
        quantity = data.get("quantity")
        brand = data.get("brand", "Sin marca")  # ✅ Obtener marca
        
        product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
        
        if not product:
            return jsonify({"success": False, "message": f"❌ Producto no encontrado"}), 404
        
        old_stock = product["stock"]
        product["stock"] = quantity
        
        # Si no se proporcionó marca, usar la del producto
        final_brand = brand if brand != "Sin marca" else product.get("brand", "Sin marca")
        
        message = f"🔄 Stock actualizado: {product['name']} marca {final_brand} de {old_stock} a {quantity} unidades"
        
        # ✅ REGISTRAR MARCA EN LA ACTIVIDAD
        activities.insert(0, {
            "time": get_current_time(),
            "date": get_current_date(),
            "fullDate": get_full_datetime(),
            "text": message,
            "type": "update",
            "product": product['name'],
            "brand": final_brand  # ✅ Marca incluida
        })
        
        interactive_products.add(product["id"])
        threading.Thread(target=notify_system_event, args=(message,), daemon=True).start()
        
        return jsonify({"success": True, "message": message})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    
@app.route("/api/activities", methods=["GET"])
def get_activities():
    """Obtener historial de actividades"""
    return jsonify(activities)

@app.route("/api/apply-filters", methods=["POST"])
def apply_filters():
    """Aplicar filtros específicos y abrir pestaña de inventario"""
    try:
        data = request.json
        filter_type = data.get("type", "all")
        filter_product = data.get("product", "all")
        filter_date = data.get("date", "all")
        specific_date = data.get("specific_date", None)
        
        print(f"🔍 APLICANDO FILTROS:")
        print(f"   Tipo: {filter_type}")
        print(f"   Producto: {filter_product}")
        print(f"   Fecha: {filter_date}")
        if specific_date:
            print(f"   Fecha específica: {specific_date}")
        
        return jsonify({
            "success": True,
            "message": "Filtros aplicados",
            "filters": {
                "type": filter_type,
                "product": filter_product,
                "date": filter_date,
                "specific_date": specific_date,
                "open_tab": "inventory-tab"
            }
        })
        
    except Exception as e:
        print(f"❌ Error aplicando filtros: {e}")
        return jsonify({"success": False, "message": str(e)})

# ============================================
# RUTAS API - SISTEMA DE VOZ
# ============================================

@app.route("/api/start-voice-system", methods=["POST"])
def start_voice_system():
    """Iniciar el sistema completo de voz controlado por 'Gwen'"""
    global transcriber
    
    try:
        if transcriber:
            try:
                transcriber.stop_all()
                time.sleep(0.5)
            except:
                pass
        
        print("🎯 INICIANDO SISTEMA DE VOZ COMPLETO...")
        improve_voice_recognition_quality()
        transcriber = Transcriber()
        
        def on_command_received(command_text):
            """Callback cuando se recibe un comando después de decir 'Gwen'"""
            print(f"📝 Comando recibido: {command_text}")
            process_voice_command_internal(command_text)
        
        transcriber.start_wake_word_system(on_command_received)
        
        return jsonify({
            "success": True,
            "message": "Sistema de voz activado. Di 'Gwen' seguido de tu comando."
        })
        
    except Exception as e:
        print(f"❌ Error iniciando sistema de voz: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/api/stop-voice-system", methods=["POST"])
def stop_voice_system():
    """Detener el sistema de voz"""
    global transcriber
    
    try:
        if transcriber:
            transcriber.stop_all()
            transcriber = None
        
        return jsonify({"success": True, "message": "Sistema de voz detenido"})
    
    except Exception as e:
        print(f"❌ Error deteniendo sistema: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/get-last-command", methods=["GET"])
def get_last_command():
    global last_command_result
    # garantizamos un dict válido
    if not isinstance(last_command_result, dict):
        last_command_result = {"success": False, "message": "", "timestamp": 0}
    payload = last_command_result.copy()
    if payload.get("filters") and (time.time() - payload.get("timestamp", 0)) < 10:
        payload["fresh"] = True
    else:
        payload["filters"] = None
        payload["fresh"] = False
    return jsonify(payload)

@app.route("/api/consume-filters", methods=["POST"])
def consume_filters():
    global last_command_result
    last_command_result["filters"] = None
    return jsonify({"ok": True})

@app.route("/api/process-voice", methods=["POST"])
def process_voice_command():
    """Procesar comando de voz desde la interfaz web (botones)"""
    try:
        data = request.json
        command = data.get("command", "")
        
        print(f"🎯 Comando desde interfaz: {command}")
        
        if not command or command.strip() == "":
            return jsonify({
                "success": False, 
                "message": "No se recibió ningún comando. Por favor, intenta de nuevo."
            })
        
        process_voice_command_internal(command)
        
        time.sleep(1)
        return jsonify(last_command_result)
            
    except Exception as e:
        print(f"❌ Error procesando comando: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False, 
            "message": f"Error procesando comando: {str(e)}"
        })

@app.route("/api/gwen-voice", methods=["POST"])
def gwen_voice_response():
    """Generar respuesta de voz para texto específico"""
    try:
        data = request.json
        text = data.get("text", "")
        
        print(f"🔊 Generando voz para: {text}")
        
        if not text or text.strip() == "":
            return jsonify({"success": False, "message": "No hay texto para convertir a voz"})
        
        clean_text = clean_text_for_tts(text)
        tts_file = TTS().process(clean_text)
        
        return jsonify({
            "success": True, 
            "message": "Audio generado exitosamente",
            "file": tts_file,
            "original_text": text
        })
        
    except Exception as e:
        print(f"❌ Error generando voz: {e}")
        return jsonify({"success": False, "message": f"Error generando voz: {str(e)}"})

@app.route("/api/check-awake", methods=["GET"])
def check_awake():
    """Verificar si el servidor detectó wake word"""
    global last_command_result
    try:
        is_awake = last_command_result.get("success", False) and last_command_result.get("timestamp", 0) > time.time() - 5
        return jsonify({"awake": is_awake})
    except Exception as e:
        return jsonify({"awake": False})

@app.route("/api/start-wake-word", methods=["POST"])
def start_wake_word():
    """Iniciar detección de wake word en el servidor"""
    try:
        print("🎯 Servidor: Wake word system iniciado")
        return jsonify({"success": True, "message": "Wake word system iniciado"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/stop-wake-word", methods=["POST"])
def stop_wake_word():
    """Detener detección de wake word en el servidor"""
    try:
        print("🎯 Servidor: Wake word system detenido")
        return jsonify({"success": True, "message": "Wake word system detenido"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/test-microphone", methods=["GET"])
def test_microphone():
    """Probar si el micrófono funciona"""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        m = sr.Microphone()
        
        with m as source:
            r.adjust_for_ambient_noise(source, duration=1)
        
        return jsonify({
            "success": True,
            "message": "Micrófono funcionando correctamente",
            "energy_threshold": r.energy_threshold
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })

# ============================================
# SISTEMA DE NOTIFICACIONES - VERSIÓN SIMPLIFICADA (POLLING)
# ============================================
last_viewed_notification_id = 0

def notify_low_stock(product):
    """Notificar cuando un producto tiene stock bajo - SOLUCIÓN DEFINITIVA"""
    try:
        product_id = product["id"]
        today = get_current_date()
        
        # ⭐ VERIFICACIÓN CRÍTICA: ¿Ya se notificó este producto hoy?
        if (product_id in product_notification_state and 
            product_notification_state[product_id].get("last_notified_date") == today and
            product_notification_state[product_id].get("notified_today") == True):
            print(f"⏭️ {product['name']} YA notificado hoy, OMITIENDO")
            return False
        
        # Determinar nivel de urgencia
        if product["stock"] == 0:
            urgency = "🚨 AGOTADO"
            title = "📦 PRODUCTO AGOTADO"
            message = f"🚨 {product['name']} SE AGOTÓ - Stock: {product['stock']} | Mínimo: {product['minStock']}"
        elif product["stock"] <= product["minStock"] // 2:
            urgency = "🔴 URGENTE"
            title = "📦 STOCK CRÍTICO"
            message = f"🔴 {product['name']} - Stock CRÍTICO: {product['stock']} | Mínimo: {product['minStock']}"
        else:
            urgency = "🟡 ALERTA"
            title = "📦 Stock Bajo"
            message = f"🟡 {product['name']} - Stock bajo: {product['stock']} | Mínimo: {product['minStock']}"

        print(f"🔔 ENVIANDO NOTIFICACIÓN: {product['name']}")
        
        # Guardar en historial
        notification = {
            "id": len(notifications_history) + 1,
            "title": title,
            "message": message,
            "type": "low-stock",
            "product_id": product_id,
            "urgency": urgency,
            "time": get_current_time(),
            "date": today,
            "timestamp": time.time(),
            "viewed": False
        }
        notifications_history.insert(0, notification)
        
        # ⭐ MARCAR COMO NOTIFICADO HOY (ESTADO PERSISTENTE)
        product_notification_state[product_id] = {
            "last_notified_date": today,
            "notified_today": True,
            "product_name": product["name"]
        }
        
        # Mantener solo las últimas 50 notificaciones
        if len(notifications_history) > 50:
            notifications_history.pop()
            
        print(f"✅ Notificación ENVIADA y REGISTRADA: {product['name']}")
        return True
        
    except Exception as e:
        print(f"❌ Error en notify_low_stock: {e}")
        return False
    
def notify_expiring_product(product):
    """Notificar cuando un producto está próximo a vencer (30 días)"""
    try:
        product_id = product["id"]
        today = get_current_date()
        
        # ⭐ VERIFICACIÓN: ¿Ya se notificó este producto hoy?
        if (product_id in product_expiry_notification_state and 
            product_expiry_notification_state[product_id].get("last_notified_date") == today and
            product_expiry_notification_state[product_id].get("notified_today") == True):
            print(f"⏭️ {product['name']} vencimiento YA notificado hoy, OMITIENDO")
            return False
        
        # Calcular días hasta vencimiento
        expiry_date = datetime.strptime(product["expiryDate"], "%Y-%m-%d")
        today_date = datetime.now()
        days_until_expiry = (expiry_date - today_date).days
        
        # Determinar nivel de urgencia
        if days_until_expiry <= 7:
            urgency = "🔴 URGENTE"
            title = "📅 PRODUCTO POR VENCER"
            message = f"🔴 {product['name']} vence en {days_until_expiry} días - Fecha: {product['expiryDate']}"
        elif days_until_expiry <= 15:
            urgency = "🟡 IMPORTANTE"
            title = "📅 Vencimiento Cercano"
            message = f"🟡 {product['name']} vence en {days_until_expiry} días - Fecha: {product['expiryDate']}"
        else:
            urgency = "🟢 AVISO"
            title = "📅 Próximo a Vencer"
            message = f"🟢 {product['name']} vence en {days_until_expiry} días - Fecha: {product['expiryDate']}"

        print(f"📅 ENVIANDO NOTIFICACIÓN DE VENCIMIENTO: {product['name']}")
        
        # Guardar en historial
        notification = {
            "id": len(notifications_history) + 1,
            "title": title,
            "message": message,
            "type": "expiry",
            "product_id": product_id,
            "brand": product.get("brand", "Sin marca"),
            "expiryDate": product["expiryDate"],
            "urgency": urgency,
            "time": get_current_time(),
            "date": today,
            "timestamp": time.time(),
            "viewed": False
        }
        notifications_history.insert(0, notification)
        
        # ⭐ MARCAR COMO NOTIFICADO HOY
        product_expiry_notification_state[product_id] = {
            "last_notified_date": today,
            "notified_today": True,
            "product_name": product["name"]
        }
        
        # Mantener solo las últimas 50 notificaciones
        if len(notifications_history) > 50:
            notifications_history.pop()
            
        print(f"✅ Notificación de vencimiento ENVIADA: {product['name']}")
        return True
        
    except Exception as e:
        print(f"❌ Error en notify_expiring_product: {e}")
        return False

# ============================================
# ENDPOINTS API PARA NOTIFICACIONES (POLLING)
# ============================================

@app.route("/api/notifications/subscribe", methods=["POST"])
def subscribe_push():
    """Suscripción simulada para mantener compatibilidad"""
    try:
        print("✅ Usuario 'suscrito' a notificaciones (modo polling)")
        
        # Enviar notificación de bienvenida
        welcome_notification = {
            "id": len(notifications_history) + 1,
            "title": "🎉 Gwen - Alertas Activadas",
            "message": "Recibirás notificaciones cuando tus productos estén por agotarse",
            "type": "system",
            "urgency": "normal",
            "time": get_current_time(),
            "date": get_current_date(),
            "timestamp": time.time()
        }
        notifications_history.insert(0, welcome_notification)
        
        return jsonify({
            "success": True, 
            "message": "Sistema de alertas activado (modo polling)",
            "polling_mode": True
        })
        
    except Exception as e:
        print(f"❌ Error en suscripción: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    
@app.route("/api/notifications/mark-all-read", methods=["POST"])
def mark_all_notifications_read():
    """Marcar todas las notificaciones como leídas (sin afectar product_notification_state)"""
    try:
        for notification in notifications_history:
            notification["viewed"] = True
        print("✅ Todas las notificaciones marcadas como leídas")
        return jsonify({"success": True, "message": "Notificaciones marcadas como leídas"})
    except Exception as e:
        print(f"❌ Error marcando notificaciones como leídas: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    
@app.route("/api/notifications/unsubscribe", methods=["POST"])
def unsubscribe_push():
    """Desuscripción simulada"""
    try:
        print("🔇 Usuario 'desuscrito' de notificaciones")
        return jsonify({"success": True, "message": "Alertas desactivadas"})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/notifications/send", methods=["POST"])
def send_notification_endpoint():
    """Endpoint para enviar notificación manual"""
    try:
        data = request.json
        title = data.get("title", "Gwen")
        message = data.get("message", "")
        type_ = data.get("type", "system")
        
        if not message:
            return jsonify({"success": False, "message": "Mensaje vacío"}), 400
        
        # Guardar en historial
        notification = {
            "id": len(notifications_history) + 1,
            "title": title,
            "message": message,
            "type": type_,
            "urgency": "normal",
            "time": get_current_time(),
            "date": get_current_date(),
            "timestamp": time.time()
        }
        notifications_history.insert(0, notification)
        
        # Mantener solo las últimas 50
        if len(notifications_history) > 50:
            notifications_history.pop()
        
        print(f"✅ Notificación manual guardada: {title}")
        
        return jsonify({
            "success": True,
            "message": "Notificación guardada",
            "notification": notification
        })
        
    except Exception as e:
        print(f"❌ Error enviando notificación: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/notifications/history", methods=["GET"])
def get_notifications_history():
    """Obtener historial de notificaciones (marca como vistas la primera vez)"""
    global last_viewed_notification_id
    
    try:
        # Si es la primera carga, marcar todo como visto
        if last_viewed_notification_id == 0 and notifications_history:
            last_viewed_notification_id = max(n["id"] for n in notifications_history)
            for n in notifications_history:
                n["viewed"] = True
        
        return jsonify(notifications_history[:50])
        
    except Exception as e:
        print(f"❌ Error obteniendo historial: {e}")
        return jsonify([])

# Remplaza esta función en app.py
# ============================================
# CAMBIOS EN app.py - REEMPLAZAR ESTAS FUNCIONES
# ============================================

# 1. REEMPLAZAR la función get_new_notifications:
@app.route("/api/notifications/new", methods=["GET"])
def get_new_notifications():
    """Obtener solo notificaciones no vistas Y marcarlas como vistas automáticamente"""
    try:
        # 1. Filtrar notificaciones que NO han sido vistas
        new_notifications = [n for n in notifications_history if not n.get("viewed", False)]
        
        # 2. ⭐ CAMBIO CRÍTICO: Marcarlas como vistas INMEDIATAMENTE
        #    Esto previene que se muestren múltiples veces
        for notification in new_notifications:
            notification["viewed"] = True
        
        # 3. Log para depuración
        if new_notifications:
            print(f"📢 {len(new_notifications)} notificaciones nuevas enviadas (ahora marcadas como vistas)")
        
        return jsonify({
            "success": True,
            "notifications": new_notifications,
            "count": len(new_notifications)
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo notificaciones nuevas: {e}")
        return jsonify({"success": False, "notifications": [], "count": 0})


# 2. AGREGAR nueva función para resetear el badge cuando se abre la pestaña:
@app.route("/api/notifications/mark-viewed", methods=["POST"])
def mark_notifications_viewed():
    """Marcar notificaciones específicas como vistas"""
    try:
        data = request.json
        notification_ids = data.get("ids", [])
        
        for notification in notifications_history:
            if notification["id"] in notification_ids:
                notification["viewed"] = True
        
        print(f"✅ {len(notification_ids)} notificaciones marcadas como vistas")
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"❌ Error marcando notificaciones: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
# ============================================
# VERIFICACIÓN PERIÓDICA DE STOCK BAJO - VERSIÓN DEFINITIVA
# ============================================

def check_low_stock_periodically():
    """Verificar stock bajo Y productos próximos a vencer - VERSIÓN DEFINITIVA"""
    print("🔍 SISTEMA DE MONITORIZACIÓN INICIADO (cada 1 minuto)")
    
    while True:
        try:
            today = get_current_date()
            print(f"\n🔍 Verificación periódica: {datetime.now().strftime('%H:%M:%S')}")
            
            # 1. Limpiar estado de notificaciones de stock si es un nuevo día
            for product_id, state in list(product_notification_state.items()):
                if state.get("last_notified_date") != today:
                    product_notification_state[product_id]["notified_today"] = False
                    print(f"🔄 Reset diario stock: {state.get('product_name', 'Producto ' + str(product_id))}")
            
            # 2. Limpiar estado de notificaciones de vencimiento si es un nuevo día
            for product_id, state in list(product_expiry_notification_state.items()):
                if state.get("last_notified_date") != today:
                    product_expiry_notification_state[product_id]["notified_today"] = False
                    print(f"🔄 Reset diario vencimiento: {state.get('product_name', 'Producto ' + str(product_id))}")
            
            # 3. Verificar productos con stock bajo
            low_stock_products = [p for p in inventory if p["stock"] <= p["minStock"]]
            low_stock_notifications_sent = 0
            for product in low_stock_products:
                if notify_low_stock(product):
                    low_stock_notifications_sent += 1
            
            # 4. Verificar productos próximos a vencer (30 días)
            today_date = datetime.now()
            expiring_products = []
            for product in inventory:
                if product.get("expiryDate"):
                    try:
                        expiry_date = datetime.strptime(product["expiryDate"], "%Y-%m-%d")
                        days_until_expiry = (expiry_date - today_date).days
                        
                        # Notificar si faltan 30 días o menos
                        if 0 < days_until_expiry <= 30:
                            expiring_products.append(product)
                    except:
                        continue
            
            expiry_notifications_sent = 0
            for product in expiring_products:
                if notify_expiring_product(product):
                    expiry_notifications_sent += 1
            
            # 5. Resumen
            if low_stock_notifications_sent > 0:
                print(f"✅ {low_stock_notifications_sent} notificaciones de STOCK BAJO enviadas")
            
            if expiry_notifications_sent > 0:
                print(f"✅ {expiry_notifications_sent} notificaciones de VENCIMIENTO enviadas")
            
            if low_stock_notifications_sent == 0 and expiry_notifications_sent == 0:
                if len(low_stock_products) > 0 or len(expiring_products) > 0:
                    print(f"ℹ️ {len(low_stock_products)} stock bajo + {len(expiring_products)} por vencer (ya notificados)")
                else:
                    print("✅ Todo en orden: stock adecuado y sin vencimientos próximos")
                
        except Exception as e:
            print(f"❌ Error en verificación periódica: {e}")
        
        time.sleep(60)

# Iniciar el hilo de monitorización
print("🚀 Iniciando hilo de monitorización de stock (cada 1 minuto)...")
threading.Thread(target=check_low_stock_periodically, daemon=True).start()

# ============================================
# INICIAR SERVIDOR FLASK
# ============================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 INICIANDO ASISTENTE VIRTUAL GWEN")
    print("=" * 60)
    print(f"📦 Inventario cargado: {len(inventory)} productos")
    print(f"📋 Actividades históricas: {len(activities)}")
    print(f"🎤 Sistema de voz: Listo")
    print(f"🔔 Sistema de alertas: ACTIVO (modo polling)")
    print(f"📡 Monitorización stock: Cada 1 minuto")
    print("=" * 60)
    
    # Iniciar Flask
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # Cambiar a True para desarrollo
        threaded=True,
        use_reloader=False  # Desactivar reloader para evitar duplicación de hilos
    )

