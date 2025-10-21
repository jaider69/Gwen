from groq import Groq
import os
from dotenv import load_dotenv
import speech_recognition as sr
import threading
import time
import queue
from difflib import SequenceMatcher

class Transcriber:
    def __init__(self, groq_client=None):
        load_dotenv()
        
        if groq_client:
            self.client = groq_client
        else:
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                print("❌ ERROR: GROQ_API_KEY no encontrada en .env")
                raise ValueError("GROQ_API_KEY no configurada")
            print(f"✅ Groq API Key cargada: {api_key[:20]}...")
            self.client = Groq(api_key=api_key)
        
        # Configuración MEJORADA del reconocedor
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_running = False
        self.listen_thread = None
        self.audio_queue = queue.Queue()
        
        # CONFIGURACIÓN OPTIMIZADA PARA MEJOR DETECCIÓN
        self.recognizer.pause_threshold = 1.0  # MÁS PAUSA para separar "Gwen" del comando
        self.recognizer.energy_threshold = 150  # AÚN MÁS SENSIBLE
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.10  # Más agresivo
        self.recognizer.dynamic_energy_adjustment_ratio = 1.8  # Más adaptable
        self.recognizer.operation_timeout = None
        self.recognizer.phrase_threshold = 0.2  # Más sensible a frases cortas
        self.recognizer.non_speaking_duration = 0.6  # Más tiempo de silencio
        
        # VARIANTES EXPANDIDAS Y ORGANIZADAS de "Gwen"
        # NOTA: "buen/bueno" funciona MEJOR que "gwen" en este micrófono
        self.wake_words = {
            # MÁS COMUNES (mejor detección)
            'bueno', 'buen', 'buena', 'when', 'wen',
            # Pronunciaciones directas de Gwen
            'gwen', 'guen', 'guin', 'gwenn', 'guenn',
            # Variaciones comunes por micrófono
            'wuen', 'wein', 'wenn',
            # Con B inicial (confusión común) - MUY IMPORTANTE
            'bwen', 'buenn', 'bween', 'bendy', 'bendi', 'wendy', 'wendi',
            # Con G fuerte
            'guan', 'guian', 'guien',
            # Variaciones con diéresis/acentos
            'güen', 'güenn', 'güen',
            # Combinaciones con sufijos
            'gwendi', 'guendi', 'wendi', 'gwendy', 'guendy',
            # Fonética española
            'guen di', 'guen ti',
            # Otras variaciones detectadas
            'queen', 'qwen', 'kwen', 'gween',
            # Variantes con "bendy" y "wendy"
            'bendy', 'bendi', 'vendi', 'vendy'
        }
        
        # Calibrar micrófono
        self._calibrate_microphone()
    
    def _calibrate_microphone(self):
        """Calibración mejorada del micrófono con ajuste dinámico"""
        print("🔧 Calibrando micrófono...")
        try:
            with self.microphone as source:
                print("   📊 Analizando ruido ambiente (2 segundos)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                
                # Ajustar threshold más bajo para mayor sensibilidad
                if self.recognizer.energy_threshold > 500:
                    self.recognizer.energy_threshold = 300
                
                print(f"   ✅ Energy threshold: {self.recognizer.energy_threshold}")
                print(f"   ✅ Pause threshold: {self.recognizer.pause_threshold}s")
        except Exception as e:
            print(f"⚠️ Advertencia al calibrar: {e}")
            # Valores seguros por defecto
            self.recognizer.energy_threshold = 400
    
    def _calculate_similarity(self, word1, word2):
        """Calcular similitud entre dos palabras usando múltiples métodos"""
        # Método 1: SequenceMatcher (más preciso)
        similarity1 = SequenceMatcher(None, word1.lower(), word2.lower()).ratio()
        
        # Método 2: Letras en común
        set1 = set(word1.lower())
        set2 = set(word2.lower())
        common = len(set1 & set2)
        total = len(set1 | set2)
        similarity2 = common / total if total > 0 else 0
        
        # Método 3: Inicio de palabra (importante para "wen" vs "gwen")
        if word1.lower().startswith(word2.lower()[:3]) or word2.lower().startswith(word1.lower()[:3]):
            similarity3 = 0.8
        else:
            similarity3 = 0
        
        # Retornar el máximo de las tres similitudes
        return max(similarity1, similarity2, similarity3)
    
    def _is_wake_word_detected(self, text):
        """Detección ULTRA OPTIMIZADA de la palabra de activación"""
        if not text or len(text.strip()) < 2:
            return False
        
        text_lower = text.lower().strip()
        
        # Remover puntuación y caracteres especiales
        text_clean = ''.join(c for c in text_lower if c.isalnum() or c.isspace())
        words = text_clean.split()
        
        print(f"🔍 Analizando: '{text_clean}'")
        
        # NIVEL 1: Coincidencia exacta
        for word in words:
            if word in self.wake_words:
                print(f"🎯 EXACTO: '{word}'")
                return True
        
        # NIVEL 2: Coincidencia por similitud alta (>80%)
        for word in words:
            if len(word) >= 2:  # REDUCIDO A 2 LETRAS
                for wake_word in self.wake_words:
                    similarity = self._calculate_similarity(word, wake_word)
                    if similarity >= 0.65:  # REDUCIDO A 65%
                        print(f"🎯 SIMILAR: '{word}' ≈ '{wake_word}' ({similarity:.2%})")
                        return True
        
        # NIVEL 3: Búsqueda de subcadenas (para captar "gwen" dentro de palabras)
        for wake_word in ['gwen', 'guen', 'wen']:
            if wake_word in text_clean:
                print(f"🎯 SUBCADENA: '{wake_word}' en '{text_clean}'")
                return True
        
        # NIVEL 4: Verificación fonética flexible
        phonetic_matches = {
            'g': ['g', 'j', 'k', 'q'],
            'w': ['w', 'u', 'v'],
            'e': ['e', 'i'],
            'n': ['n', 'm', 'nn']
        }
        
        for word in words:
            if len(word) >= 3:
                # Transformar palabra usando equivalencias fonéticas
                word_variants = [word]
                # Generar variantes fonéticas
                if word[0] in ['g', 'k', 'q', 'j']:
                    for w in list(word_variants):
                        word_variants.append('g' + w[1:])
                        word_variants.append('w' + w[1:])
                
                for variant in word_variants:
                    if variant in self.wake_words:
                        print(f"🎯 FONÉTICO: '{word}' → '{variant}'")
                        return True
        
        return False
    
    def _extract_command_after_wake_word(self, text):
        """Extraer comando con limpieza AGRESIVA de wake words"""
        if not text:
            return None
        
        text_lower = text.lower().strip()
        original_text = text_lower
        
        print(f"🔧 Limpiando: '{text_lower}'")
        
        # Lista de patrones a remover (ordenados por especificidad)
        patterns_to_remove = [
            'gwen', 'guen', 'guin', 'gwenn', 'guenn',
            'wen', 'when', 'wuen', 'wein', 'wenn',
            'buen', 'bwen', 'buenn', 'bween',
            'guan', 'guian', 'guien',
            'güen', 'güenn',
            'gwendi', 'guendi', 'wendi',
            'guen di', 'guen ti',
            'queen', 'qwen', 'kwen', 'gween'
        ]
        
        # Remover wake words del inicio (más común)
        for pattern in patterns_to_remove:
            if text_lower.startswith(pattern + ' '):
                text_lower = text_lower[len(pattern):].strip()
                print(f"   🧹 Removido del inicio: '{pattern}'")
                break
            elif text_lower.startswith(pattern):
                text_lower = text_lower[len(pattern):].strip()
                print(f"   🧹 Removido pegado: '{pattern}'")
                break
        
        # Remover wake words de cualquier posición (backup)
        for pattern in patterns_to_remove:
            if pattern in text_lower:
                text_lower = text_lower.replace(pattern, ' ').strip()
                print(f"   🧹 Removido medio: '{pattern}'")
        
        # Limpiar espacios múltiples
        text_lower = ' '.join(text_lower.split())
        
        # Si quedó muy corto o vacío, intentar extraer de otra forma
        if len(text_lower) < 3:
            # Buscar la primera palabra que no sea wake word
            words = original_text.split()
            command_words = []
            for word in words:
                if not any(self._calculate_similarity(word, wake) > 0.7 for wake in patterns_to_remove):
                    command_words.append(word)
            text_lower = ' '.join(command_words)
        
        if text_lower and len(text_lower) >= 3:
            print(f"   ✅ Comando final: '{text_lower}'")
            return text_lower
        
        print(f"   ⚠️ Comando muy corto o vacío")
        return None
    
    def _record_audio(self, timeout=5, phrase_time_limit=15):
        """Grabar audio con configuración optimizada"""
        try:
            with self.microphone as source:
                # Ajuste rápido de ruido ambiente
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                
                print(f"🎤 Grabando... (max {phrase_time_limit}s)")
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
                print(f"✅ Audio capturado ({len(audio.frame_data)} bytes)")
                return audio
        except sr.WaitTimeoutError:
            print("⏱️ Timeout - no se detectó audio")
            return None
        except Exception as e:
            print(f"❌ Error grabando: {e}")
            return None
    
    def _transcribe_audio(self, audio):
        """Transcribir audio con estrategia de múltiples intentos"""
        if not audio:
            return None
        
        # INTENTO 1: Google (rápido y preciso para español)
        try:
            print("🔄 Transcribiendo con Google...")
            text = self.recognizer.recognize_google(audio, language='es-ES')
            if text:
                print(f"✅ Google: '{text}'")
                return text.lower().strip()
        except sr.UnknownValueError:
            print("❓ Google no entendió el audio")
        except sr.RequestError as e:
            print(f"⚠️ Error de Google API: {e}")
        
        # INTENTO 2: Google con variante de idioma
        try:
            print("🔄 Reintentando con Google (es-MX)...")
            text = self.recognizer.recognize_google(audio, language='es-MX')
            if text:
                print(f"✅ Google MX: '{text}'")
                return text.lower().strip()
        except:
            pass
        
        # INTENTO 3: Groq Whisper (más lento pero más robusto)
        try:
            print("🔄 Transcribiendo con Groq Whisper...")
            return self._transcribe_with_groq(audio)
        except Exception as e:
            print(f"❌ Groq Whisper falló: {e}")
        
        return None
    
    def _transcribe_with_groq(self, audio):
        """Transcribir usando Groq Whisper"""
        try:
            temp_file = "temp_audio.wav"
            with open(temp_file, "wb") as f:
                f.write(audio.get_wav_data())
            
            with open(temp_file, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    language="es",
                    response_format="text",
                    temperature=0.2  # Menor temperatura = más determinístico
                )
            
            try:
                os.remove(temp_file)
            except:
                pass
            
            result = transcription.strip()
            if result:
                print(f"✅ Groq: '{result}'")
                return result.lower()
            return None
            
        except Exception as e:
            print(f"❌ Error Groq: {e}")
            return None
    
    def start_wake_word_system(self, on_command_callback):
        """Sistema ULTRA OPTIMIZADO de detección continua"""
        if self.is_running:
            print("⚠️ El sistema ya está corriendo")
            return
        
        self.is_running = True
        
        def listen_loop():
            print("\n" + "="*60)
            print("🎯 SISTEMA DE VOZ ULTRA OPTIMIZADO INICIADO")
            print("👂 Escuchando 'Gwen' continuamente...")
            print("💡 Tips: Habla claro, a volumen normal, sin gritar")
            print("💡 Ejemplo: 'Gwen agrega 10 latas de atún'")
            print("="*60 + "\n")
            
            consecutive_errors = 0
            max_errors = 3
            successful_detections = 0
            
            while self.is_running:
                try:
                    # ESTRATEGIA: Escuchar en bloques cortos para mayor responsividad
                    audio = self._record_audio(timeout=2, phrase_time_limit=12)  # timeout MÁS CORTO
                    
                    if audio is None:
                        continue
                    
                    # TRANSCRIBIR
                    text = self._transcribe_audio(audio)
                    
                    if not text or len(text.strip()) < 2:
                        continue
                    
                    print(f"\n📝 Texto: '{text}'")
                    
                    # VERIFICAR WAKE WORD
                    if self._is_wake_word_detected(text):
                        print("🎉 ¡GWEN DETECTADO!")
                        successful_detections += 1
                        
                        # EXTRAER COMANDO
                        command = self._extract_command_after_wake_word(text)
                        
                        if command and len(command) >= 3:
                            print(f"✅ Ejecutando: '{command}'")
                            consecutive_errors = 0
                            on_command_callback(command)
                            time.sleep(1.5)  # Pausa para evitar re-detección
                        else:
                            # Wake word sin comando - esperar comando separado
                            print("🎤 ¿Cuál es tu comando?")
                            time.sleep(0.3)
                            
                            command_audio = self._record_audio(timeout=4, phrase_time_limit=10)
                            if command_audio:
                                command_text = self._transcribe_audio(command_audio)
                                if command_text and len(command_text.strip()) >= 3:
                                    print(f"✅ Comando: '{command_text}'")
                                    on_command_callback(command_text)
                                else:
                                    print("⚠️ No entendí el comando")
                                    on_command_callback("no_entendido")
                            time.sleep(1)
                    
                    consecutive_errors = 0
                    
                except KeyboardInterrupt:
                    print("\n🛑 Detenido por usuario")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    consecutive_errors += 1
                    time.sleep(0.5)
                    
                    if consecutive_errors >= max_errors:
                        print(f"⚠️ {consecutive_errors} errores consecutivos. Recalibrando...")
                        self._calibrate_microphone()
                        consecutive_errors = 0
                        time.sleep(2)
            
            print(f"\n📊 Sesión finalizada - Detecciones exitosas: {successful_detections}")
            print("🔇 Sistema de voz detenido")
        
        self.listen_thread = threading.Thread(target=listen_loop, daemon=True)
        self.listen_thread.start()
        print("✅ Sistema iniciado - Thread activo")
    
    def stop_all(self):
        """Detener el sistema de forma limpia"""
        print("🛑 Deteniendo sistema de voz...")
        self.is_running = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        print("✅ Sistema detenido completamente")