// form.js – time capsule form (text/audio + encryption + upload + confetti)

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', function () {
    const inputTypeSelect = document.getElementById('inputType');
    const textInputContainer = document.getElementById('textInputContainer');
    const audioInputContainer = document.getElementById('audioInputContainer');
    const recordBtn = document.getElementById('recordBtn');
    const audioPlayback = document.getElementById('audioPlayback');
    const audioDataInput = document.getElementById('audioData');
    const form = document.getElementById('timeCapsuleForm');
    const submitBtn = document.getElementById('submitBtn');
    const confettiContainer = document.getElementById('confetti');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const statusMessage = document.getElementById('statusMessage');
    const timeSelect = document.getElementById('timeSelect');
    const customDatetimeContainer = document.getElementById('customDatetimeContainer');
    const customDatetimeInput = document.getElementById('customDatetime');

    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;

    // toggle text/audio
    inputTypeSelect.addEventListener('change', () => {
        const type = inputTypeSelect.value;
        if (type === 'text') {
            textInputContainer.style.display = 'block';
            audioInputContainer.style.display = 'none';
        } else {
            textInputContainer.style.display = 'none';
            audioInputContainer.style.display = 'block';
        }
    });

    // time selector
    timeSelect.addEventListener('change', function () {
        if (this.value === 'custom') {
            customDatetimeContainer.style.display = 'block';
            const tomorrow = new Date();
            const min = tomorrow.toISOString().slice(0, 16);
            customDatetimeInput.min = min;
        } else {
            customDatetimeContainer.style.display = 'none';
        }
    });

    // audio recording
    recordBtn.addEventListener('click', toggleRecording);

    async function toggleRecording() {
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    const arrayBuffer = await audioBlob.arrayBuffer();
                    audioDataInput.arrayBuffer = arrayBuffer; // store raw bytes for encryption

                    const audioURL = URL.createObjectURL(audioBlob);
                    audioPlayback.src = audioURL;
                    audioPlayback.style.display = 'block';
                    stream.getTracks().forEach(track => track.stop());
                };

                mediaRecorder.start();
                recordBtn.textContent = 'Stop Recording';
                recordBtn.style.background = '#e74c3c';
                isRecording = true;
            } catch (err) {
                console.error('Error accessing microphone:', err);
                showStatusMessage('Could not access microphone. Please check permissions.', 'error');
            }
        } else {
            mediaRecorder.stop();
            recordBtn.textContent = 'Start Recording';
            recordBtn.style.background = '#2563eb';
            isRecording = false;
        }
    }

    // === Crypto helpers ===
    function uint8ArrayToWordArray(u8Array) {
        const words = [];
        let i = 0;
        for (; i + 3 < u8Array.length; i += 4) {
            words.push(
                (u8Array[i] << 24) |
                (u8Array[i + 1] << 16) |
                (u8Array[i + 2] << 8) |
                (u8Array[i + 3])
            );
        }
        const remainder = u8Array.length % 4;
        if (remainder) {
            let lastWord = 0;
            if (remainder === 1) lastWord = (u8Array[i] << 24);
            else if (remainder === 2) lastWord = (u8Array[i] << 24) | (u8Array[i + 1] << 16);
            else if (remainder === 3) lastWord = (u8Array[i] << 24) | (u8Array[i + 1] << 16) | (u8Array[i + 2] << 8);
            words.push(lastWord);
        }
        return CryptoJS.lib.WordArray.create(words, u8Array.length);
    }

    function wordArrayToUint8Array(wordArray) {
        const len = wordArray.sigBytes;
        const u8 = new Uint8Array(len);
        let offset = 0;
        for (let i = 0; i < wordArray.words.length; i++) {
            let word = wordArray.words[i];
            u8[offset++] = (word >>> 24) & 0xFF;
            if (offset >= len) break;
            u8[offset++] = (word >>> 16) & 0xFF;
            if (offset >= len) break;
            u8[offset++] = (word >>> 8) & 0xFF;
            if (offset >= len) break;
            u8[offset++] = word & 0xFF;
            if (offset >= len) break;
        }
        return u8;
    }

    function encryptBytesToUint8Array(dataBytes, password) {
        const salt = CryptoJS.lib.WordArray.random(16);
        const iv = CryptoJS.lib.WordArray.random(16);
        const key = CryptoJS.PBKDF2(password, salt, {
            keySize: 256 / 32,
            iterations: 100000,
            hasher: CryptoJS.algo.SHA256
        });

        const dataWordArray = uint8ArrayToWordArray(dataBytes);
        const encrypted = CryptoJS.AES.encrypt(dataWordArray, key, {
            iv: iv,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        });

        const combined = CryptoJS.lib.WordArray.create()
            .concat(salt)
            .concat(iv)
            .concat(encrypted.ciphertext);

        return wordArrayToUint8Array(combined);
    }

    function generateRandomPassword(length) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    // === FORM SUBMIT ===
    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        loadingOverlay.classList.add('active');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sealing...';

        try {
            const messageType = inputTypeSelect.value;
            const email = document.getElementById('email').value.trim();
            if (!email) throw new Error('Please enter an email');

            let fileType, dataBytes, fileExt;

            // unlock time seconds
            let unlockTimeSeconds;
            if (timeSelect.value === 'custom') {
                if (!customDatetimeInput.value) throw new Error('Please select a custom date & time');
                const selectedDate = new Date(customDatetimeInput.value);
                const now = new Date();
                unlockTimeSeconds = Math.floor((selectedDate - now) / 1000);
                if (isNaN(unlockTimeSeconds) || unlockTimeSeconds <= 0) {
                    throw new Error('Please select a future date and time');
                }
            } else {
                unlockTimeSeconds = parseInt(timeSelect.value, 10);
            }

            const encryptionPassword = generateRandomPassword(32);

            if (messageType === 'text') {
                const text = document.getElementById('textMessage').value.trim();
                if (!text) throw new Error('Please enter a message');
                fileType = 'text/plain';
                fileExt = '.txt';
                const encoder = new TextEncoder();
                dataBytes = encoder.encode(text);
            } else if (messageType === 'audio') {
                if (!audioDataInput.arrayBuffer) throw new Error('Please record an audio message');
                fileType = 'audio/webm';
                fileExt = '.webm';
                dataBytes = new Uint8Array(audioDataInput.arrayBuffer);
            } else {
                throw new Error('Invalid message type');
            }

            // encrypt
            const encryptedBytes = encryptBytesToUint8Array(dataBytes, encryptionPassword);

            const blob = new Blob([encryptedBytes], { type: 'application/octet-stream' });
            const formData = new FormData();
            formData.append('email', email);
            formData.append('unlock_time', unlockTimeSeconds.toString());
            formData.append('password', encryptionPassword);
            formData.append('file_mime', fileType);
            formData.append('file_ext', fileExt);
            formData.append('encrypted_file', blob, 'encrypted_message.dat');

            const headers = {};
            const csrf = getCookie('csrftoken');
            if (csrf) headers['X-CSRFToken'] = csrf;

            const response = await fetch(UPLOAD_URL, {
                method: 'POST',
                body: formData,
                headers
            });

            let result = {};
            try {
                result = await response.json();
            } catch (_) {}

            if (response.ok) {
                showStatusMessage('✨ Your time capsule has been sealed!', 'success');
                form.reset();
                if (audioPlayback) audioPlayback.style.display = 'none';
                createConfetti();
            } else {
                throw new Error(result.error || 'Failed to seal time capsule');
            }

        } catch (error) {
            console.error('Error:', error);
            showStatusMessage(`❌ Error: ${error.message}`, 'error');
        } finally {
            setTimeout(() => {
                loadingOverlay.classList.remove('active');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Send';
            }, 800);
        }
    });

    // UI helpers
    function createConfetti() {
        confettiContainer.style.display = 'block';
        confettiContainer.innerHTML = '';

        for (let i = 0; i < 80; i++) {
            const confetti = document.createElement('div');
            confetti.style.position = 'absolute';
            confetti.style.width = '8px';
            confetti.style.height = '8px';
            confetti.style.backgroundColor = getRandomColor();
            confetti.style.borderRadius = '50%';
            confetti.style.left = Math.random() * 100 + '%';
            confetti.style.top = '-10px';
            confetti.style.opacity = '0.8';

            const animation = confetti.animate([
                { top: '-10px', opacity: 0 },
                { top: Math.random() * 80 + '%', opacity: 0.9 },
                { top: '100%', opacity: 0 }
            ], {
                duration: 2000 + Math.random() * 2500,
                easing: 'cubic-bezier(0.1, 0.8, 0.3, 1)'
            });

            confettiContainer.appendChild(confetti);
            animation.onfinish = () => confetti.remove();
        }

        setTimeout(() => {
            confettiContainer.style.display = 'none';
        }, 2800);
    }

    function getRandomColor() {
        const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f1c40f', '#9b59b6', '#1abc9c'];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    function showStatusMessage(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = `status-message ${type}`;
        statusMessage.style.display = 'block';
        setTimeout(() => {
            statusMessage.style.display = 'none';
        }, 4500);
    }
});