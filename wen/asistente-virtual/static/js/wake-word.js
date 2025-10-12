class WakeWordManager {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.checkInterval = null;
        this.serverAvailable = false;
        this.audioInteracted = false;
    }

    async startListening() {
        try {
            console.log("🚀 INICIANDO SISTEMA DE WAKE WORD...");
            this.updateUI('🔄 Iniciando sistema...', 'loading');

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

    async ensureAudioPermissions() {
        try {
            // Solicitar permisos de audio silenciosamente
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop());
            this.audioInteracted = true;
            console.log("✅ Permisos de audio concedidos");
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
            this.recognition.maxAlternatives = 1;

            this.recognition.onstart = () => {
                this.isListening = true;
                this.updateUI('🎯 Escuchando localmente... Di "GWEN"', 'listening');
                console.log("✅ WAKE WORD LOCAL ACTIVADO");
            };

            this.recognition.onresult = (event) => {
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        const transcript = event.results[i][0].transcript.toLowerCase();
                        console.log(`🔍 Texto detectado: "${transcript}"`);
                        
                        if (this.detectWakeWord(transcript)) {
                            console.log("🎯 ¡GWEN DETECTADO LOCALMENTE!");
                            this.onWakeWordDetected();
                            break;
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
        const wakeWords = ['gwen', 'guen', 'wen', 'buen', 'güen'];
        return wakeWords.some(word => text.includes(word));
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