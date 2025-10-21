class WakeWordManager {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.checkInterval = null;
        this.serverAvailable = false;
        this.audioInteracted = false;
        this.lastDetectionTime = 0;
        this.detectionCooldown = 3000; // 3 segundos entre detecciones
    }

    async startListening() {
        try {
            console.log("🚀 INICIANDO SISTEMA DE WAKE WORD MEJORADO...");
            this.updateUI('🔄 Iniciando sistema...', 'loading');

            // Mostrar consejos de uso
            this.showVoiceTips();
            
            // Verificar permisos de audio primero
            await this.ensureAudioPermissions();
            
            this.serverAvailable = await this.checkServer();
            
            if (this.serverAvailable) {
                console.log("✅ Servidor disponible - usando wake word del servidor");
                return await this.startServerWakeWord();
            } else {
                console.log("⚠️ Servidor no disponible - usando wake word local");
                return this.startLocalWakeWord();
            }

        } catch (error) {
            console.error('❌ Error crítico:', error);
            return this.startLocalWakeWord();
        }
    }

    showVoiceTips() {
        console.log("🎧 CONSEJOS PARA MEJOR DETECCIÓN:");
        console.log("💡 Habla en un entorno tranquilo");
        console.log("💡 Di 'Gwen' seguido inmediatamente de tu comando");
        console.log("💡 Ejemplo: 'Gwen agrega 10 latas de atún'");
        console.log("💡 Habla claro y a velocidad normal");
        console.log("💡 Mantén el micrófono a 10-20 cm de tu boca");
    }

    async ensureAudioPermissions() {
        try {
            // Solicitar permisos de audio silenciosamente
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            stream.getTracks().forEach(track => track.stop());
            this.audioInteracted = true;
            console.log("✅ Permisos de audio concedidos con optimizaciones");
        } catch (error) {
            console.warn("⚠️ Permisos de audio no concedidos:", error);
            // No bloquear si no hay permisos, seguir igual
        }
    }

    async checkServer() {
        try {
            const response = await fetch('/api/check-awake', { 
                signal: AbortSignal.timeout(2000) 
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    }

    async startServerWakeWord() {
        try {
            const response = await fetch('/api/start-wake-word', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            if (data.success) {
                this.isListening = true;
                this.startServerCheck();
                this.updateUI('🎯 Escuchando... Di "GWEN"', 'listening');
                console.log("✅ WAKE WORD DEL SERVIDOR ACTIVADO");
                return true;
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('❌ Error con servidor:', error);
            this.serverAvailable = false;
            return this.startLocalWakeWord();
        }
    }

    startLocalWakeWord() {
        try {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                this.updateUI('❌ Navegador no compatible con voz', 'error');
                return false;
            }

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'es-ES';
            this.recognition.maxAlternatives = 3; // Aumentado para mejores resultados

            this.recognition.onstart = () => {
                this.isListening = true;
                this.updateUI('🎯 Escuchando localmente... Di "GWEN"', 'listening');
                console.log("✅ WAKE WORD LOCAL ACTIVADO CON DETECCIÓN MEJORADA");
            };

            this.recognition.onresult = (event) => {
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        const transcript = event.results[i][0].transcript.toLowerCase();
                        const confidence = event.results[i][0].confidence;
                        
                        console.log(`🔍 Texto detectado: "${transcript}" (confianza: ${confidence})`);
                        
                        // Procesar todas las alternativas
                        for (let j = 0; j < event.results[i].length; j++) {
                            const alternative = event.results[i][j].transcript.toLowerCase();
                            console.log(`   Alternativa ${j}: "${alternative}"`);
                            
                            if (this.detectWakeWord(alternative)) {
                                console.log("🎯 ¡GWEN DETECTADO LOCALMENTE!");
                                this.onWakeWordDetected();
                                break;
                            }
                        }
                    }
                }
            };

            this.recognition.onerror = (event) => {
                console.error('❌ Error reconocimiento:', event.error);
                
                if (event.error === 'not-allowed') {
                    this.updateUI('❌ Permiso de micrófono denegado', 'error');
                    this.isListening = false;
                } else {
                    // Reintentar automáticamente
                    setTimeout(() => {
                        if (this.isListening) {
                            this.recognition.start();
                        }
                    }, 1000);
                }
            };

            this.recognition.onend = () => {
                if (this.isListening && this.recognition) {
                    setTimeout(() => {
                        try {
                            this.recognition.start();
                        } catch (e) {
                            console.error('Error reiniciando:', e);
                        }
                    }, 500);
                }
            };

            this.recognition.start();
            return true;

        } catch (error) {
            console.error('❌ Error iniciando wake word local:', error);
            this.updateUI('❌ Error iniciando escucha', 'error');
            return false;
        }
    }

    detectWakeWord(text) {
        // Verificar cooldown para evitar detecciones múltiples
        const now = Date.now();
        if (now - this.lastDetectionTime < this.detectionCooldown) {
            console.log('⏳ En cooldown, ignorando...');
            return false;
        }

        // VARIANTES EXPANDIDAS MEJORADAS
        const wakeWords = [
            'gwen', 'guen', 'wen', 'buen', 'güen', 'gween', 'guenn',
            // Variantes que el reconocimiento confunde - EXPANDIDAS
            'wendy', 'when', 'wenn', 'wend', 'guan', 'güenn', 'buenn',
            'wen di', 'when di', 'wendi', 'guendi', 'güendi', 'wenti',
            'guenti', 'huen', 'güen', 'güenn', 'güendi', 'güenti', 
            'güenny', 'wén', 'guén', 'buén', 'güén', 'weni', 'gueni',
            'bwen', 'gwenn', 'wenn', 'bwén', 'gwén', 'wénn'
        ];
        
        const textLower = text.toLowerCase().trim();
        
        console.log(`🔍 Frontend analizando: "${textLower}"`);
        
        // Buscar coincidencias directas
        const directMatch = wakeWords.some(word => {
            // Buscar palabra completa o como inicio de palabra
            return textLower.includes(word) || 
                   textLower.split(' ').some(w => w.startsWith(word));
        });
        
        if (directMatch) {
            console.log('🎯 Wake word detectada por coincidencia directa');
            this.lastDetectionTime = now;
            return true;
        }
        
        // Detección por sonido similar MEJORADA
        const words = textLower.split(' ');
        for (let word of words) {
            if (word.length >= 2) { // Reducido a 2 caracteres mínimo
                // Palabras que comienzan con w/g/b/gu/gw/bu y tienen "en" o sonidos similares
                const startsWithSound = word.startsWith('w') || word.startsWith('g') || word.startsWith('b') || 
                                      word.startsWith('gu') || word.startsWith('gw') || word.startsWith('bu') ||
                                      word.startsWith('hu') || word.startsWith('wu');
                
                const containsEnSound = word.includes('en') || word.includes('an') || word.includes('on') || 
                                      word.includes('in') || word.includes('un') || word.includes('wen') || 
                                      word.includes('gen') || word.includes('ben') || word.includes('uen') ||
                                      word.includes('én') || word.includes('án') || word.includes('ón');
                
                if (startsWithSound && containsEnSound) {
                    console.log(`🎯 Detección por sonido: "${word}" suena como "gwen"`);
                    this.lastDetectionTime = now;
                    return true;
                }
                
                // Detectar por primera sílaba MEJORADO
                const firstSyllables = ['wen', 'gen', 'ben', 'guen', 'gwen', 'when', 'buen', 'güen', 'wén', 'guén'];
                for (let syllable of firstSyllables) {
                    if (word.startsWith(syllable) || 
                        word.substring(0, 4).includes(syllable) ||
                        this.calculateSimilarity(word.substring(0, 3), syllable) > 0.6) {
                        console.log(`🎯 Detección por sílaba: "${word}" -> "${syllable}"`);
                        this.lastDetectionTime = now;
                        return true;
                    }
                }
                
                // Detección por similitud fonética
                if (this.calculateSimilarity(word, 'gwen') > 0.6) {
                    console.log(`🎯 Detección por similitud: "${word}" -> "gwen"`);
                    this.lastDetectionTime = now;
                    return true;
                }
            }
        }
        
        console.log('❌ No se detectó wake word');
        return false;
    }

    calculateSimilarity(word1, word2) {
        // Método simple de similitud
        const set1 = new Set(word1);
        const set2 = new Set(word2);
        const intersection = new Set([...set1].filter(x => set2.has(x)));
        const union = new Set([...set1, ...set2]);
        return intersection.size / union.size;
    }

    startServerCheck() {
        console.log("🔄 Iniciando verificación del servidor...");
        this.checkInterval = setInterval(async () => {
            if (!this.isListening) return;
            
            try {
                const response = await fetch('/api/check-awake');
                if (response.ok) {
                    const data = await response.json();
                    if (data.awake) {
                        console.log("🎯 ¡WAKE WORD DETECTADO EN SERVIDOR!");
                        this.onWakeWordDetected();
                    }
                }
            } catch (error) {
                // Error silencioso
            }
        }, 800);
    }

    async stopListening() {
        console.log("🛑 DETENIENDO WAKE WORD...");
        this.isListening = false;

        if (this.recognition) {
            this.recognition.stop();
            this.recognition = null;
        }

        this.stopServerCheck();

        try {
            await fetch('/api/stop-wake-word', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (error) {
            // Ignorar errores
        }

        this.updateUI('🔇 Wake word desactivado', 'stopped');
        console.log("✅ WAKE WORD DETENIDO");
    }

    stopServerCheck() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }

    onWakeWordDetected() {
        console.log("🎯 ACTIVANDO GRABACIÓN AUTOMÁTICA...");
        this.updateUI('✅ ¡GWEN ACTIVADA! Iniciando grabación...', 'activated');

        setTimeout(() => {
            const startBtn = document.getElementById('startBtn');
            if (startBtn && !startBtn.disabled) {
                console.log("🎯 EJECUTANDO GRABACIÓN...");
                
                // Forzar interacción con el documento primero
                this.forceUserInteraction();
                
                startBtn.click();

                const statusElement = document.getElementById('status');
                if (statusElement) {
                    statusElement.textContent = "🎤 Activado por voz - Habla ahora";
                    statusElement.classList.add('auto-recording');
                }

                // Reactivar después de 10 segundos para comandos largos
                setTimeout(() => {
                    if (this.isListening) {
                        this.updateUI('🎯 Escuchando... Di "GWEN"', 'listening');
                        console.log("✅ WAKE WORD REACTIVADO");
                    }
                }, 10000);

            } else {
                console.log("⚠️ Botón de grabación no disponible");
                this.updateUI('⚠️ Error al activar grabación', 'warning');
                
                setTimeout(() => {
                    if (this.isListening) {
                        this.updateUI('🎯 Escuchando... Di "GWEN"', 'listening');
                    }
                }, 3000);
            }
        }, 1000);
    }

    forceUserInteraction() {
        // Crear un clic silencioso para cumplir con la política de autoplay
        try {
            const clicker = document.createElement('button');
            clicker.style.display = 'none';
            document.body.appendChild(clicker);
            clicker.click();
            document.body.removeChild(clicker);
            console.log("✅ Interacción forzada para políticas de audio");
        } catch (e) {
            console.warn("⚠️ No se pudo forzar interacción:", e);
        }
    }

    updateUI(message, status) {
        const statusElement = document.getElementById('wakeWordStatus');
        const button = document.getElementById('wakeWordButton');
        
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `wake-word-status ${status}`;
        }
        
        if (button) {
            if (this.isListening) {
                button.textContent = '🛑 Detener Escucha';
                button.classList.add('active');
            } else {
                button.textContent = '🎯 Activar Escucha por Voz';
                button.classList.remove('active');
            }
        }
        
        console.log(`🟡 WAKE WORD UI [${status}]: ${message}`);
    }
}

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 INICIALIZANDO WAKE WORD MANAGER MEJORADO...");
    window.wakeWordManager = new WakeWordManager();
    
    const wakeWordButton = document.getElementById('wakeWordButton');
    if (wakeWordButton) {
        wakeWordButton.addEventListener('click', function() {
            if (window.wakeWordManager.isListening) {
                window.wakeWordManager.stopListening();
            } else {
                window.wakeWordManager.startListening();
            }
        });
    }
});