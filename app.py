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

print("🧹 Limpiando notificaciones iniciales...")
notifications_history.clear()

inventory = [
    {"id": 1, "name": "Arroz", "category": "Granos", "stock": 25, "minStock": 10},
    {"id": 2, "name": "Frijoles", "category": "Granos", "stock": 18, "minStock": 8},
    {"id": 3, "name": "Aceite", "category": "Aceites", "stock": 12, "minStock": 5},
    {"id": 4, "name": "Azúcar", "category": "Endulzantes", "stock": 30, "minStock": 10},
    {"id": 5, "name": "Sal", "category": "Condimentos", "stock": 15, "minStock": 5},
    {"id": 6, "name": "Leche", "category": "Lácteos", "stock": 8, "minStock": 10},
    {"id": 7, "name": "Galletas", "category": "Snacks", "stock": 22, "minStock": 15},
    {"id": 8, "name": "Jabón", "category": "Limpieza", "stock": 14, "minStock": 10},
    {"id": 9, "name": "Atún", "category": "Enlatados", "stock": 15, "minStock": 8},
    {"id": 10, "name": "Café", "category": "Bebidas", "stock": 20, "minStock": 10},
    {"id": 11, "name": "Pan", "category": "Panadería", "stock": 5, "minStock": 10},
    {"id": 12, "name": "Huevos", "category": "Lácteos", "stock": 30, "minStock": 12},
    {"id": 13, "name": "Pasta", "category": "Granos", "stock": 25, "minStock": 10},
    {"id": 14, "name": "Tomate", "category": "Verduras", "stock": 8, "minStock": 15},
    {"id": 15, "name": "Cebolla", "category": "Verduras", "stock": 12, "minStock": 10},
    {"id": 16, "name": "Papa", "category": "Verduras", "stock": 40, "minStock": 20},
    {"id": 17, "name": "Zanahoria", "category": "Verduras", "stock": 18, "minStock": 12},
    {"id": 18, "name": "Pollo", "category": "Carnes", "stock": 10, "minStock": 8},
    {"id": 19, "name": "Carne", "category": "Carnes", "stock": 12, "minStock": 8},
    {"id": 20, "name": "Refresco", "category": "Bebidas", "stock": 35, "minStock": 20},
    {"id": 21, "name": "Agua", "category": "Bebidas", "stock": 50, "minStock": 30},
    {"id": 22, "name": "Yogurt", "category": "Lácteos", "stock": 15, "minStock": 10},
    {"id": 23, "name": "Mantequilla", "category": "Lácteos", "stock": 8, "minStock": 5},
    {"id": 24, "name": "Queso", "category": "Lácteos", "stock": 10, "minStock": 8},
    {"id": 25, "name": "Shampoo", "category": "Higiene", "stock": 12, "minStock": 8},
    {"id": 26, "name": "Pasta Dental", "category": "Higiene", "stock": 18, "minStock": 10},
    {"id": 27, "name": "Papel Higiénico", "category": "Higiene", "stock": 25, "minStock": 15},
    {"id": 28, "name": "Detergente", "category": "Limpieza", "stock": 10, "minStock": 8},
    {"id": 29, "name": "Servilletas", "category": "Limpieza", "stock": 30, "minStock": 20},
    {"id": 30, "name": "Cereal", "category": "Desayuno", "stock": 14, "minStock": 10}
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
    """Generar actividades de ejemplo de los últimos días"""
    activities_list = []
    now = datetime.now()
    
    sample_data = [
        {"hours_ago": 1, "type": "sell", "product": "Pan", "text": "Venta registrada de 5 Pan"},
        {"hours_ago": 2, "type": "add", "product": "Leche", "text": "Se agregaron 10 unidades de Leche"},
        {"hours_ago": 3, "type": "sell", "product": "Refresco", "text": "Venta registrada de 8 Refresco"},
        {"hours_ago": 4, "type": "update", "product": "Galletas", "text": "Stock actualizado: Galletas de 15 a 22"},
        {"hours_ago": 5, "type": "sell", "product": "Huevos", "text": "Venta registrada de 12 Huevos"},
        {"hours_ago": 26, "type": "add", "product": "Arroz", "text": "Se agregaron 20 unidades de Arroz"},
        {"hours_ago": 28, "type": "sell", "product": "Café", "text": "Venta registrada de 3 Café"},
        {"hours_ago": 50, "type": "update", "product": "Agua", "text": "Stock actualizado: Agua de 30 a 50"},
    ]
    
    for item in sample_data:
        event_time = now - timedelta(hours=item["hours_ago"])
        activities_list.append({
            "time": event_time.strftime("%H:%M"),
            "date": event_time.strftime("%d/%m/%Y"),
            "fullDate": event_time.isoformat(),
            "text": item["text"],
            "type": item["type"],
            "product": item["product"]
        })
    
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
    """Limpiar texto para convertir a voz (TTS) - MEJORADO para fechas"""
    # Primero formatear las fechas antes de limpiar otros caracteres
    text = format_dates_for_speech(text)
    
    # Remover caracteres especiales excepto puntuación básica
    clean_text = re.sub(r'[^\w\s¡!¿?.,;:()\-]', '', text)
    
    # Reemplazar emojis con texto
    clean_text = clean_text.replace('✅', 'Listo')
    clean_text = clean_text.replace('💰', 'Venta registrada')
    clean_text = clean_text.replace('🔄', 'Actualizado')
    clean_text = clean_text.replace('📊', 'Informe')
    clean_text = clean_text.replace('📦', 'Stock')
    clean_text = clean_text.replace('❌', 'Error')
    clean_text = clean_text.replace('⚠️', 'Atención')
    
    # Limpiar espacios múltiples
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text

def format_dates_for_speech(text):
    """Convertir fechas numéricas a formato hablado"""
    try:
        # Patrón para fechas en formato DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
        date_patterns = [
            r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})',
        ]
        
        months = {
            '01': 'enero', '02': 'febrero', '03': 'marzo', '04': 'abril',
            '05': 'mayo', '06': 'junio', '07': 'julio', '08': 'agosto',
            '09': 'septiembre', '10': 'octubre', '11': 'noviembre', '12': 'diciembre'
        }
        
        def replace_date(match):
            day = match.group(1).lstrip('0')
            month_num = match.group(2).zfill(2)
            year = match.group(3)
            
            # Si el año tiene 2 dígitos, asumir siglo 21
            if len(year) == 2:
                year = "20" + year
            
            # Convertir mes numérico a texto
            month_name = months.get(month_num, f"mes {month_num.lstrip('0')}")
            
            return f"{day} de {month_name} del {year}"
        
        # Aplicar reemplazo para cada patrón de fecha
        for pattern in date_patterns:
            text = re.sub(pattern, replace_date, text)
        
        # También formatear fechas que ya están en variables (como expiry_date)
        # Buscar patrones como "vence el 25/12/2025" y convertirlos
        text = re.sub(
            r'(venc[e|é|en]|caduc[a|á|an]|expir[a|á|an])\s+el\s+(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})',
            lambda m: f"{m.group(1)} el {format_single_date(m.group(2), m.group(3), m.group(4))}",
            text
        )
        
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

def extract_product_from_command(command):
    """Extraer nombre de producto del comando de voz - MEJORADO"""
    try:
        if not command:
            return None
        
        command_lower = command.lower().strip()
        print(f"🔍 Buscando producto en: '{command_lower}'")
        
        # MAPEO MEJORADO DE PRODUCTOS CON MÁS VARIANTES
        product_variants = {
            "Leche": ["leche", "leches", "lácteo", "lacteo", "lechería"],
            "Pan": ["pan", "panes", "panadería", "bollo", "bollos"],
            "Galletas": ["galletas", "galleta", "cookie", "cookies", "bizcocho"],
            "Arroz": ["arroz", "arroces", "grano"],
            "Atún": ["atún", "atun", "atunes", "lata de atún", "latas de atún", "atún enlatado"],
            "Refresco": ["refresco", "refrescos", "gaseosa", "soda", "bebida gaseosa"],
            "Agua": ["agua", "aguas", "botella de agua", "agua embotellada"],
            "Café": ["café", "cafe", "cafés", "cafecito"],
            "Huevos": ["huevos", "huevo", "docena de huevos", "huevito"],
            "Azúcar": ["azúcar", "azucar", "endulzante", "dulce"],
            "Frijoles": ["frijoles", "frijol", "porotos", "judías"],
            "Aceite": ["aceite", "aceites", "aceite vegetal", "aceite de cocina"],
            "Sal": ["sal", "sales", "sal de mesa"],
            "Jabón": ["jabón", "jabon", "jabones", "jabón de baño"],
            "Pasta": ["pasta", "pastas", "fideos", "espagueti", "macarrones"],
            "Tomate": ["tomate", "tomates", "jitomate"],
            "Cebolla": ["cebolla", "cebollas", "cebollín"],
            "Papa": ["papa", "papas", "patatas", "patata"],
            "Zanahoria": ["zanahoria", "zanahorias"],
            "Pollo": ["pollo", "pollos", "pollo entero"],
            "Carne": ["carne", "carnes", "carne de res", "bistec"],
            "Yogurt": ["yogurt", "yogur", "yogures"],
            "Mantequilla": ["mantequilla", "manteca", "margarina"],
            "Queso": ["queso", "quesos", "quesillo"],
            "Shampoo": ["shampoo", "champu", "champú", "shampú"],
            "Pasta Dental": ["pasta dental", "pasta de dientes", "crema dental", "dentífrico"],
            "Papel Higiénico": ["papel higiénico", "papel", "rollo de papel"],
            "Detergente": ["detergente", "jabón en polvo", "detergente para ropa"],
            "Servilletas": ["servilletas", "servilleta", "papel servilleta"],
            "Cereal": ["cereal", "cereales", "cereal de desayuno"]
        }
        
        # BUSCAR COINCIDENCIAS EXACTAS PRIMERO
        for product_key, variants in product_variants.items():
            for variant in variants:
                if variant in command_lower:
                    print(f"🎯 Producto encontrado: '{product_key}' (variante: '{variant}')")
                    return product_key
        
        # BÚSQUEDA POR PALABRAS CLAVE SI NO HAY COINCIDENCIA EXACTA
        words = command_lower.split()
        for word in words:
            for product_key, variants in product_variants.items():
                for variant in variants:
                    # Verificar similitud
                    if word in variant or variant in word:
                        if len(word) >= 3:  # Evitar coincidencias con palabras muy cortas
                            print(f"🎯 Producto encontrado por palabra clave: '{product_key}' (palabra: '{word}')")
                            return product_key
        
        print(f"❌ No se detectó producto específico en: '{command_lower}'")
        return None
        
    except Exception as e:
        print(f"❌ Error extrayendo producto: {e}")
        return None

def extract_quantity_from_command(command):
    """Extraer cantidad del comando de voz"""
    try:
        # Buscar números directos
        numbers = re.findall(r'\d+', command)
        if numbers:
            quantity = int(numbers[0])
            print(f"🔢 Cantidad detectada (número): {quantity}")
            return quantity
        
        # Palabras numéricas
        number_words = {
            'un': 1, 'una': 1, 'uno': 1,
            'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
            'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9,
            'diez': 10, 'once': 11, 'doce': 12, 'docena': 12,
            'quince': 15, 'veinte': 20, 'treinta': 30
        }
        
        words = command.lower().split()
        for word in words:
            if word in number_words:
                quantity = number_words[word]
                print(f"🔢 Cantidad detectada (palabra): {quantity}")
                return quantity
        
        print(f"🔢 Sin cantidad específica, usando: 1")
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
    """EXTRAER MARCA del comando de voz"""
    try:
        if not command:
            return None
            
        command_lower = command.lower().strip()
        print(f"🔍 Buscando MARCA en: '{command_lower}'")
        
        # Patrones comunes para marcas
        # Busca palabras después de "marca", "de la marca", "marca:"
        brand_patterns = [
            r'marca\s+(\w+)',
            r'de\s+la\s+marca\s+(\w+)',
            r'marca:\s*(\w+)',
            r'fabricante\s+(\w+)',
        ]
        
        for pattern in brand_patterns:
            match = re.search(pattern, command_lower)
            if match:
                brand = match.group(1).strip().title()
                # Verificar que no sea una palabra común de comando
                common_words = {'agregar', 'añadir', 'vender', 'actualizar', 'stock', 'unidades'}
                if brand.lower() not in common_words:
                    print(f"🎯 Marca encontrada: '{brand}'")
                    return brand
        
        print(f"⚠️ No se detectó marca en: '{command_lower}'")
        return None
        
    except Exception as e:
        print(f"❌ Error extrayendo marca: {e}")
        return None

def extract_expiry_date_from_command(command):
    """EXTRAER FECHA DE VENCIMIENTO del comando de voz - VERSIÓN DEFINITIVA"""
    try:
        if not command:
            return None
            
        command_lower = command.lower().strip()
        print(f"🔍 Buscando FECHA DE VENCIMIENTO en: '{command_lower}'")
        
        # Patrones mejorados y más flexibles
        date_patterns = [
            # Formato numérico: 25/12/2025, 25-12-2025, 25.12.2025
            # Acepta: vence, vencen, caduca, caducan, expira, expiran
            r'(?:venc[e|é|en]|caduc[a|á|an]|expir[a|á|an]|fecha\s+de\s+vencimiento)(?:\s+el)?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            
            # Formato texto: "25 de diciembre de 2025" o "25 de diciembre del 2025"
            # Acepta: vence, vencen, caduca, caducan, expira, expiran + el/del
            r'(?:venc[e|é|en]|caduc[a|á|an]|expir[a|á|an])(?:\s+el|\s+del)?\s*(\d{1,2})\s+de\s+([a-z]+)\s+(?:de\s+|del\s+)?(\d{4})',
            
            # Muy flexible: encuentra cualquier fecha DD/MM/YYYY cerca de palabras de vencimiento
            r'(?:venc[e|é|en]|caduc[a|á|an]|expir[a|á|an]).*?(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            
            # Fallback: busca mes escrito completo
            r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+|del\s+)?(\d{4})'
        ]
        
        months = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        
        for pattern in date_patterns:
            match = re.search(pattern, command_lower)
            if match:
                groups = match.groups()
                
                # Formato numérico directo
                if len(groups) == 1:
                    date_str = groups[0]
                    try:
                        # Detectar separador
                        sep = '/' if '/' in date_str else '-' if '-' in date_str else '.' if '.' in date_str else '/'
                        parts = date_str.split(sep)
                        
                        if len(parts) == 3:
                            day = parts[0].zfill(2)
                            month = parts[1].zfill(2)
                            year = parts[2]
                            if len(year) == 2:
                                year = "20" + year
                            formatted_date = f"{day}/{month}/{year}"
                            print(f"✅ Fecha numérica encontrada: '{formatted_date}'")
                            return formatted_date
                    except:
                        continue
                
                # Formato texto con día, mes, año
                elif len(groups) == 3:
                    day = groups[0].zfill(2)
                    month_text = groups[1].lower()
                    year = groups[2]
                    
                    if month_text in months:
                        month = months[month_text]
                        formatted_date = f"{day}/{month}/{year}"
                        print(f"✅ Fecha textual encontrada: '{formatted_date}'")
                        return formatted_date
        
        print(f"⚠️ No se detectó fecha de vencimiento en: '{command_lower}'")
        return None
        
    except Exception as e:
        print(f"❌ Error extrayendo fecha de vencimiento: {e}")
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
                
                # Registrar actividad
                activities.insert(0, {
                    "time": get_current_time(),
                    "date": get_current_date(),
                    "fullDate": get_full_datetime(),
                    "text": message,
                    "type": "add",
                    "product": existing_product['name'] if existing_product else product_name.title()
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
            
            # VALIDACIÓN OBLIGATORIA: Verificar que TODOS los datos estén presentes
            missing_fields = []
            if not product_name:
                missing_fields.append("nombre del producto")
            if not quantity:
                missing_fields.append("cantidad")
            if not brand:
                missing_fields.append("marca")
            
            if missing_fields:
                # Construir mensaje de error específico para ventas
                if len(missing_fields) == 1:
                    error_msg = f"Falta el dato obligatorio para registrar la venta: {missing_fields[0]}"
                else:
                    error_msg = f"Faltan los datos obligatorios para registrar la venta: {', '.join(missing_fields)}"
                
                error_msg += ". Por ejemplo: 'vendí 5 galletas marca María'"
                
                print(f"❌ {error_msg}")
                update_last_command(False, error_msg)
                speak_response(error_msg)
            else:
                # Todos los datos presentes - Buscar producto específico con marca
                product = next((p for p in inventory if p["name"].lower() == product_name.lower() and p.get("brand", "").lower() == brand.lower()), None)
                
                # Si no encuentra con marca exacta, busca solo por nombre (compatibilidad hacia atrás)
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
                    
                    activities.insert(0, {
                        "time": get_current_time(),
                        "date": get_current_date(),
                        "fullDate": get_full_datetime(),
                        "text": message,
                        "type": "sell",
                        "product": product['name']
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
            
            print(f"🔍 Extraído - Producto: '{product_name}', Cantidad: {quantity}")
            
            if product_name and quantity:
                product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
                
                if product:
                    old_stock = product["stock"]
                    product["stock"] = quantity
                    message = f"Stock actualizado: {product['name']} de {old_stock} a {quantity} unidades"
                    
                    activities.insert(0, {
                        "time": get_current_time(),
                        "date": get_current_date(),
                        "fullDate": get_full_datetime(),
                        "text": message,
                        "type": "update",
                        "product": product['name']
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
    """Obtener alertas de stock bajo"""
    try:
        low_stock_alerts = []
        for product in inventory:
            if product["stock"] <= product["minStock"]:
                urgency = "CRÍTICO" if product["stock"] == 0 else "ALTO" if product["stock"] <= product["minStock"] // 2 else "MEDIO"
                low_stock_alerts.append({
                    "id": product["id"],
                    "name": product["name"],
                    "stock": product["stock"],
                    "minStock": product["minStock"],
                    "urgency": urgency
                })
        
        expiring_alerts = []
        
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
        
        product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
        
        if not product:
            return jsonify({"success": False, "message": f"❌ Producto '{product_name}' no encontrado en el inventario"}), 404
        
        if product["stock"] < quantity:
            return jsonify({"success": False, "message": f"❌ No hay suficiente stock de {product['name']}. Stock actual: {product['stock']} unidades"}), 400
        
        product["stock"] -= quantity
        message = f"💰 Se registró la venta de {quantity} unidades de {product['name']}. Stock restante: {product['stock']} unidades"
        
        activities.insert(0, {
            "time": get_current_time(),
            "date": get_current_date(),
            "fullDate": get_full_datetime(),
            "text": message,
            "type": "sell",
            "product": product['name']
        })
        
        interactive_products.add(product["id"])

        threading.Thread(target=notify_sale, args=(product, quantity), daemon=True).start()
        
        return jsonify({"success": True, "message": message, "inventory": inventory})
    
    except Exception as e:
        print(f"❌ Error registrando venta: {e}")
        return jsonify({"success": False, "message": str(e)})
        
@app.route("/api/inventory/update", methods=["POST"])
def update_stock():
    """Actualizar stock de producto"""
    try:
        data = request.json
        product_name = data.get("name")
        quantity = data.get("quantity")
        
        product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
        
        if not product:
            return jsonify({"success": False, "message": f"❌ Producto '{product_name}' no encontrado"}), 404
        
        old_stock = product["stock"]
        product["stock"] = quantity
        message = f"🔄 Se actualizó el stock de {product['name']} de {old_stock} a {quantity} unidades"
        
        activities.insert(0, {
            "time": get_current_time(),
            "date": get_current_date(),
            "fullDate": get_full_datetime(),
            "text": message,
            "type": "update",
            "product": product['name']
        })
        
        interactive_products.add(product["id"])

        threading.Thread(target=notify_system_event, args=(message,), daemon=True).start()
        
        return jsonify({"success": True, "message": message, "inventory": inventory})
    
    except Exception as e:
        print(f"❌ Error actualizando stock: {e}")
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

@app.route("/api/notifications/new", methods=["GET"])
def get_new_notifications():
    """Obtener solo notificaciones no vistas (polling optimizado)"""
    try:
        # 1. Filtrar notificaciones que NO han sido vistas
        new_notifications = [n for n in notifications_history if not n.get("viewed", False)]
        
        # 2. Marcar SOLO estas notificaciones como vistas (sin resetear las demás)
        for n in new_notifications:
            n["viewed"] = True
        
        # 3. Log para depuración
        if new_notifications:
            print(f"📢 {len(new_notifications)} notificaciones nuevas enviadas al frontend")
        
        return jsonify({
            "success": True,
            "notifications": new_notifications,
            "count": len(new_notifications)
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo notificaciones nuevas: {e}")
        return jsonify({"success": False, "notifications": [], "count": 0})

# ============================================
# VERIFICACIÓN PERIÓDICA DE STOCK BAJO - VERSIÓN DEFINITIVA
# ============================================

def check_low_stock_periodically():
    """Verificar stock bajo - SOLUCIÓN DEFINITIVA SIN REPETICIONES"""
    print("🔔 SISTEMA DE MONITORIZACIÓN INICIADO (cada 1 minuto)")
    
    while True:
        try:
            today = get_current_date()
            print(f"\n🔍 Verificación de stock: {datetime.now().strftime('%H:%M:%S')}")
            
            # Limpiar estado si es un nuevo día
            for product_id, state in list(product_notification_state.items()):
                if state.get("last_notified_date") != today:
                    product_notification_state[product_id]["notified_today"] = False
                    print(f"🔄 Reset diario: {state.get('product_name', 'Producto ' + str(product_id))}")
            
            # Verificar productos con stock bajo
            products_to_notify = []
            for product in inventory:
                if product["stock"] <= product["minStock"]:
                    products_to_notify.append(product)
            
            # Enviar notificaciones solo para productos no notificados hoy
            new_notifications_sent = 0
            for product in products_to_notify:
                if notify_low_stock(product):
                    new_notifications_sent += 1
            
            if new_notifications_sent > 0:
                print(f"✅ {new_notifications_sent} notificaciones NUEVAS enviadas")
            elif len(products_to_notify) > 0:
                print(f"ℹ️ {len(products_to_notify)} productos con stock bajo (ya notificados)")
            else:
                print("✅ Todo el stock está en niveles adecuados")
                
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