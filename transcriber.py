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
        
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_running = False
        self.listen_thread = None
        
        # ⭐ OPTIMIZACIÓN 1: Wake words más específicas y reducidas
        self.wake_words = {
            'gwen',      # Principal
            'wen',       # Variante corta
            'gen',       # Variante fonética
            'gueen',
            'uen',
            'bueno',
            'buen'
        }
        
        # ⭐ OPTIMIZACIÓN 2: Comandos compuestos optimizados
        self.compound_commands = {
            'wendy': 'vendí',
            'gwendi': 'vendí',
            'gendi': 'vendí',
            'gendy': 'vendí',
        }
        
        # ⭐ OPTIMIZACIÓN 3: Configuración mejorada del reconocedor
        self.recognizer.pause_threshold = 1.2  # Reducido de 1.8
        self.recognizer.energy_threshold = 300  # Aumentado de 80
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_adjustment_ratio = 1.5
        self.recognizer.phrase_threshold = 0.3  # Aumentado de 0.1
        self.recognizer.non_speaking_duration = 0.8  # Reducido de 1.5
        
        # ⭐ OPTIMIZACIÓN 4: Cache de transcripciones recientes
        self.recent_transcriptions = []
        self.max_cache_size = 5
        
        self._calibrate_microphone()
    
    def _calibrate_microphone(self):
        """Calibración optimizada con ajuste automático"""
        print("🔧 Calibrando micrófono...")
        try:
            with self.microphone as source:
                print("   📊 Analizando ruido ambiente (2 segundos)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                
                # ⭐ OPTIMIZACIÓN 5: Ajuste dinámico basado en ambiente
                if self.recognizer.energy_threshold < 200:
                    self.recognizer.energy_threshold = 300
                    print(f"   ⚙️ Ajustado a threshold mínimo: 300")
                elif self.recognizer.energy_threshold > 4000:
                    self.recognizer.energy_threshold = 2000
                    print(f"   ⚙️ Ajustado a threshold máximo: 2000")
                
                print(f"   ✅ Energy threshold: {self.recognizer.energy_threshold}")
                print(f"   ✅ Pause threshold: {self.recognizer.pause_threshold}s")
                
        except Exception as e:
            print(f"⚠️ Advertencia al calibrar: {e}")
            self.recognizer.energy_threshold = 300
    
    def _calculate_similarity(self, word1, word2):
        """⭐ OPTIMIZACIÓN 6: Similitud mejorada con peso fonético"""
        word1_lower = word1.lower()
        word2_lower = word2.lower()
        
        # Similitud de secuencia (Levenshtein-like)
        similarity1 = SequenceMatcher(None, word1_lower, word2_lower).ratio()
        
        # Similitud de caracteres comunes
        set1 = set(word1_lower)
        set2 = set(word2_lower)
        common = len(set1 & set2)
        total = len(set1 | set2)
        similarity2 = common / total if total > 0 else 0
        
        # ⭐ MEJORA: Bonus por inicio similar (fonética)
        if len(word1_lower) >= 2 and len(word2_lower) >= 2:
            if word1_lower[:2] == word2_lower[:2]:
                similarity3 = 0.8
            else:
                similarity3 = 0
        else:
            similarity3 = 0
        
        # Promedio ponderado optimizado
        return (similarity1 * 0.5 + similarity2 * 0.3 + similarity3 * 0.2)
    
    def _detect_compound_command(self, text):
        """⭐ OPTIMIZACIÓN 7: Detección más rápida de comandos compuestos"""
        if not text or len(text) < 3:
            return False, None, None
        
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        if not words:
            return False, None, None
        
        first_word = words[0]
        
        # Búsqueda exacta primero (más rápido)
        if first_word in self.compound_commands:
            rest = ' '.join(words[1:])
            print(f"🎯 COMANDO COMPUESTO: '{first_word}' → 'gwen {self.compound_commands[first_word]} {rest}'")
            return True, self.compound_commands[first_word], rest
        
        # Solo buscar similitud si la palabra tiene longitud razonable
        if len(first_word) >= 4:
            for compound, action in self.compound_commands.items():
                similarity = self._calculate_similarity(first_word, compound)
                if similarity >= 0.85:  # Aumentado de 0.80
                    rest = ' '.join(words[1:])
                    print(f"🎯 COMANDO COMPUESTO SIMILAR: '{first_word}' ≈ '{compound}' ({similarity:.2%})")
                    return True, action, rest
        
        return False, None, None
    
    def _has_command_words(self, text):
        if not text or len(text) < 3:
            return False
        
        text_lower = text.lower()
        
        # ⭐ MEJORA: Usar sets para búsqueda O(1)
        command_keywords = {
            # Acciones principales
            'agrega', 'agregar', 'añade', 'añadir', 'pon', 'poner',
            'vendí', 'vender', 'vende', 'vendido',
            'actualiza', 'actualizar', 'cambia', 'cambiar',
            'muestra', 'mostrar', 'ver', 'consultar',
            'cuánto', 'cuanto', 'hay',
            
            # ⭐ Comandos de apagado + VARIANTES FONÉTICAS
            'apagar', 'apágate', 'apagate', 'desactivar', 'detener', 
            'stop', 'adiós', 'adios', 'chao', 'bye',
            'pagar', 'pagate',
            
            # Productos más comunes (reducido)
            'arroz', 'leche', 'pan', 'galleta', 'atún', 'agua',
            'aceite', 'azúcar', 'sal', 'café', 'huevo',
            
            # Temporales
            'hoy', 'ayer', 'semana'
        }
        
        # Verificar números primero (más rápido)
        if any(char.isdigit() for char in text_lower):
            print(f"   ✅ Tiene números - Es comando válido")
            return True
        
        # ⭐ NUEVO: Limpiar puntuación de las palabras antes de comparar
        import re
        text_words = set(re.sub(r'[^\w\s]', '', text_lower).split())  # Elimina puntuación
        
        if text_words & command_keywords:  # Intersección de sets
            matching = text_words & command_keywords
            print(f"   ✅ Contiene palabra clave: {matching}")
            return True
        
        print(f"   ❌ No contiene palabras de comando")
        return False
    
    def _is_wake_word_detected(self, text):
        """⭐ OPTIMIZACIÓN 9: Detección más precisa y rápida"""
        if not text or len(text.strip()) < 3:
            return False
        
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        print(f"🔍 Analizando: '{text_lower}'")
        
        # CASO 1: Comandos compuestos (prioridad máxima)
        is_compound, action, rest = self._detect_compound_command(text_lower)
        if is_compound and rest and len(rest) >= 3:
            print(f"✅ Comando compuesto válido: '{action} {rest}'")
            return True
        
        # CASO 2: Wake word normal
        wake_word_found = False
        wake_word_position = -1
        
        # ⭐ MEJORA: Solo revisar las primeras 2 palabras (más rápido)
        for i, word in enumerate(words[:2]):
            # Coincidencia exacta primero
            if word in self.wake_words:
                wake_word_found = True
                wake_word_position = i
                print(f"🎯 Wake word exacta: '{word}' en posición {i}")
                break
            
            # Similitud solo para palabras >=3 caracteres
            if len(word) >= 3:
                for wake_word in self.wake_words:
                    similarity = self._calculate_similarity(word, wake_word)
                    if similarity >= 0.75:  # Aumentado de 0.70
                        wake_word_found = True
                        wake_word_position = i
                        print(f"🎯 Wake word similar: '{word}' ≈ '{wake_word}' ({similarity:.2%})")
                        break
            
            if wake_word_found:
                break
        
        if not wake_word_found:
            print(f"❌ No se encontró wake word")
            return False
        
        # Validar comando después de wake word
        remaining_text = ' '.join(words[wake_word_position + 1:])
        
        if not remaining_text or len(remaining_text) < 3:
            print(f"❌ Wake word sin comando suficiente")
            return False
        
        if self._has_command_words(remaining_text):
            print(f"✅ Wake word + comando válido: '{remaining_text}'")
            return True
        
        print(f"❌ Wake word sin palabras de comando")
        return False
    
    def _extract_command_after_wake_word(self, text):
        """⭐ OPTIMIZACIÓN 10: Extracción optimizada de comandos"""
        if not text:
            return None
        
        text_lower = text.lower().strip()
        print(f"🔧 Extrayendo comando de: '{text_lower}'")
        
        # CASO 1: Comando compuesto
        is_compound, action, rest = self._detect_compound_command(text_lower)
        if is_compound and rest and len(rest) >= 3:
            expanded = f"{action} {rest}".strip()
            print(f"   ✅ Comando expandido: '{expanded}'")
            return expanded
        
        # CASO 2: Wake word normal
        words = text_lower.split()
        wake_word_position = -1
        
        # Buscar posición de wake word (solo primeras 2 palabras)
        for i, word in enumerate(words[:2]):
            if word in self.wake_words:
                wake_word_position = i
                break
            
            for wake_word in self.wake_words:
                if self._calculate_similarity(word, wake_word) >= 0.75:
                    wake_word_position = i
                    break
            
            if wake_word_position != -1:
                break
        
        if wake_word_position == -1:
            print(f"   ❌ No se encontró wake word")
            return None
        
        # Extraer comando
        command = ' '.join(words[wake_word_position + 1:])
        
        if command and len(command) >= 3:
            print(f"   ✅ Comando extraído: '{command}'")
            return command
        
        print(f"   ❌ Comando vacío o muy corto")
        return None
    
    def _record_audio(self, timeout=8, phrase_time_limit=20):
        """⭐ OPTIMIZACIÓN 11: Grabación más eficiente"""
        try:
            with self.microphone as source:
                # Ajuste rápido de ruido (0.2s en lugar de 0.3s)
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                
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
        """⭐ OPTIMIZACIÓN 12: Priorización inteligente de servicios"""
        if not audio:
            return None
        
        transcription_methods = [
            ("Groq Whisper", self._transcribe_with_groq),
            ("Google ES", lambda a: self.recognizer.recognize_google(a, language='es-ES')),
            ("Google MX", lambda a: self.recognizer.recognize_google(a, language='es-MX'))
        ]
        
        for method_name, method in transcription_methods:
            try:
                print(f"🔄 Transcribiendo con {method_name}...")
                text = method(audio)
                
                if text:
                    text_clean = text.lower().strip()
                    
                    # ⭐ MEJORA: Evitar transcripciones repetidas
                    if text_clean in self.recent_transcriptions:
                        print(f"⚠️ Transcripción duplicada, ignorando")
                        continue
                    
                    # Agregar a cache
                    self.recent_transcriptions.append(text_clean)
                    if len(self.recent_transcriptions) > self.max_cache_size:
                        self.recent_transcriptions.pop(0)
                    
                    print(f"✅ {method_name}: '{text_clean}'")
                    return text_clean
                    
            except sr.UnknownValueError:
                print(f"❌ {method_name} no entendió")
            except sr.RequestError as e:
                print(f"⚠️ Error {method_name} API: {e}")
            except Exception as e:
                print(f"❌ {method_name} falló: {e}")
        
        return None
    
    def _transcribe_with_groq(self, audio):
        """Transcripción optimizada con Groq"""
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
                    temperature=0.0  # ⭐ Reducido de 0.2 para más consistencia
                )
            
            try:
                os.remove(temp_file)
            except:
                pass
            
            result = transcription.strip()
            if result:
                return result.lower()
            return None
            
        except Exception as e:
            print(f"❌ Error Groq: {e}")
            return None
    
    def start_wake_word_system(self, on_command_callback):
        """⭐ OPTIMIZACIÓN 13: Loop de escucha más eficiente"""
        if self.is_running:
            print("⚠️ Sistema ya corriendo")
            return
        
        self.is_running = True
        
        def listen_loop():
            print("\n" + "="*60)
            print("🎯 SISTEMA DE VOZ OPTIMIZADO ACTIVADO")
            print("📋 Wake words: gwen, wen, guen")
            print("⭐ Especiales: wendy, gwendi, gendi = 'gwen vendí'")
            print("="*60 + "\n")
            
            consecutive_errors = 0
            max_errors = 3
            successful_detections = 0
            last_recalibration = time.time()
            
            while self.is_running:
                try:
                    # ⭐ MEJORA: Recalibración periódica cada 2 minutos
                    if time.time() - last_recalibration > 120:
                        print("🔄 Recalibración automática...")
                        self._calibrate_microphone()
                        last_recalibration = time.time()
                    
                    audio = self._record_audio(timeout=8, phrase_time_limit=20)
                    
                    if audio is None:
                        continue
                    
                    text = self._transcribe_audio(audio)
                    
                    if not text or len(text.strip()) < 3:
                        print("⚠️ Texto muy corto o vacío")
                        continue
                    
                    print(f"\n📊 Transcrito: '{text}'")
                    
                    if self._is_wake_word_detected(text):
                        print("🎉 ¡ACTIVADO!")
                        successful_detections += 1
                        
                        command = self._extract_command_after_wake_word(text)
                        
                        if command and len(command) >= 3:
                            print(f"✅ Ejecutando: '{command}'")
                            consecutive_errors = 0
                            on_command_callback(command)
                            time.sleep(1.5)  # Reducido de 2s
                        else:
                            print("❌ No se pudo extraer comando válido")
                    else:
                        print("❌ No cumple criterios de activación")
                    
                    consecutive_errors = 0
                    
                except KeyboardInterrupt:
                    print("\n🛑 Detenido por usuario")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    consecutive_errors += 1
                    
                    if consecutive_errors >= max_errors:
                        print(f"⚠️ Recalibrando por errores consecutivos...")
                        self._calibrate_microphone()
                        consecutive_errors = 0
                        last_recalibration = time.time()
                        time.sleep(1)
            
            print(f"\n📊 Detecciones exitosas: {successful_detections}")
            print("🔇 Sistema detenido")
        
        self.listen_thread = threading.Thread(target=listen_loop, daemon=True)
        self.listen_thread.start()
        print("✅ Sistema iniciado")
    
    def stop_all(self):
        """Detener sistema limpiamente"""
        print("🛑 Deteniendo...")
        self.is_running = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        self.recent_transcriptions.clear()
        print("✅ Detenido")