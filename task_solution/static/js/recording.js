// recording.js - 共通化された録画・フレーム送信機能

// DOM要素の参照
const recordBtn = document.getElementById('recordBtn');
const statusMessage = document.getElementById('statusMessage');
const result = document.getElementById('result');

class Recorder {
    constructor(config) {
        this.config = Object.assign({
            captureInterval: 500,
            frameThreshold: 60,
            pythonUrl: '/record_frame'
        }, config);
        this.isRecording = false;
        this.mediaStream = null;
        this.videoElement = null;
        this.samplingInterval = null;
        this.canvas = null;
        this.ctx = null;
        this.frameBuffer = [];
        this.latestFrameForAINotify = null; // Added for AI notify
        this.lastFrameSentToAINotify = null; // Added to track last sent frame for AI notify
    }

    async start() {
        try {
            this.showStatus('', '');
            // 画面共有を取得
            this.mediaStream = await navigator.mediaDevices.getDisplayMedia({
                video: { cursor: "always", displaySurface: "monitor" },
                audio: false
            });
            // 動画要素の作成
            this.videoElement = document.createElement('video');
            this.videoElement.srcObject = this.mediaStream;
            // キャンバスの作成
            this.canvas = document.createElement('canvas');
            this.ctx = this.canvas.getContext('2d');
            // ビデオのメタデータ読み込みを待つ
            await new Promise(resolve => {
                this.videoElement.onloadedmetadata = () => {
                    this.videoElement.play();
                    this.canvas.width = this.videoElement.videoWidth;
                    this.canvas.height = this.videoElement.videoHeight;
                    resolve();
                };
            });
            // 録画状態に設定
            this.isRecording = true;
            startSupportCheck(); // Start polling if conditions are met
            recordBtn.textContent = '録画を停止';
            recordBtn.className = 'stop-btn';
            // 録画中インジケーターの追加
            const indicator = document.createElement('span');
            indicator.className = 'recording-indicator';
            indicator.id = 'recordingIndicator';
            recordBtn.prepend(indicator);
            // 結果表示エリアの表示
            if (result) {
                result.classList.remove('hidden');
            }
            // 指定間隔でフレームキャプチャを開始
            this.samplingInterval = setInterval(() => this.captureAndProcessFrame(), this.config.captureInterval);
            this.showStatus('録画を開始しました', 'success');
            // ストリーム終了時の処理
            this.mediaStream.getVideoTracks()[0].onended = () => {
                this.stop();
            };
        } catch (err) {
            console.error("エラーが発生しました:", err);
            if (err.name === 'NotAllowedError') {
                this.showStatus('画面共有がキャンセルされました。', 'error');
            } else {
                this.showStatus('エラーが発生しました: ' + err.message, 'error');
            }
        }
    }

    async stop() {
        console.log('[DEBUG stop()] Entered stop method.');
        if (!this.isRecording) {
            console.log('[DEBUG stop()] Exiting: isRecording is false.');
            return;
        }

        console.log('[DEBUG stop()] Clearing samplingInterval.');
        clearInterval(this.samplingInterval);
        this.samplingInterval = null; // Good practice to nullify

        // let lastSendResult = null; // 'lastSendResult' might not be meaningful in the same way
        if (this.frameBuffer.length > 0) {
            console.log(`[DEBUG stop()] Frame buffer has ${this.frameBuffer.length} frames. Sending in background.`);
            // Call sendFrames without await and attach error handling to the promise
            this.sendFrames(this.frameBuffer)
                .then(result => {
                    console.log('[DEBUG stop()] Background sendFrames completed. Result:', result);
                })
                .catch(err => {
                    console.error("[DEBUG stop()] Error during background sendFrames:", err);
                });
            this.frameBuffer = []; // Clear framebuffer immediately
            console.log('[DEBUG stop()] Frame buffer cleared locally.');
        } else {
            console.log('[DEBUG stop()] Frame buffer is empty. No frames to send.');
        }

        console.log('[DEBUG stop()] About to stop mediaStream tracks. Current mediaStream:', this.mediaStream);
        if (this.mediaStream) {
            const tracks = this.mediaStream.getTracks();
            console.log(`[DEBUG stop()] Found ${tracks.length} tracks.`);
            tracks.forEach((track, index) => {
                console.log(`[DEBUG stop()] Stopping track ${index}:`, track);
                track.stop();
                console.log(`[DEBUG stop()] Track ${index} stopped.`);
            });
            this.mediaStream = null;
            console.log('[DEBUG stop()] mediaStream nulled.');
        } else {
            console.log('[DEBUG stop()] mediaStream is null or undefined.');
        }

        console.log('[DEBUG stop()] About to clear videoElement. Current videoElement:', this.videoElement);
        if (this.videoElement) {
            this.videoElement.srcObject = null;
            this.videoElement = null;
            console.log('[DEBUG stop()] videoElement cleared and nulled.');
        } else {
            console.log('[DEBUG stop()] videoElement is null or undefined.');
        }

        console.log('[DEBUG stop()] Calling stopSupportCheck().');
        stopSupportCheck();

        console.log('[DEBUG stop()] Setting isRecording to false.');
        this.isRecording = false;

        if (this.config.pythonUrl === '/record_frame' && recordBtn) {
            console.log('[DEBUG stop()] Updating recordBtn UI.');
            recordBtn.textContent = '録画を開始';
            recordBtn.className = 'record-btn';
            const indicator = document.getElementById('recordingIndicator');
            if (indicator) {
                console.log('[DEBUG stop()] Removing recordingIndicator.');
                indicator.remove();
            }
        }

        console.log('[DEBUG stop()] Calling showStatus("録画を停止しました", "success").');
        this.showStatus('停止しました', 'success');
        console.log('[DEBUG stop()] Exiting stop method.');
        return lastSendResult;
    }

    async captureAndProcessFrame() {
        if (!this.isRecording || !this.videoElement || !this.ctx) return;
        try {
            // フレームキャプチャ
            this.ctx.drawImage(this.videoElement, 0, 0, this.canvas.width, this.canvas.height);
            // Base64エンコード（JPEG形式、品質0.7）
            const dataUrl = this.canvas.toDataURL('image/jpeg', 0.7);
            this.latestFrameForAINotify = dataUrl; // Store latest frame for AI notify
            this.frameBuffer.push(dataUrl);
            // バッファが閾値に達したら送信
            if (this.frameBuffer.length >= this.config.frameThreshold) {
                const tmp = this.frameBuffer;
                this.frameBuffer = [];
                await this.sendFrames(tmp);
            }
        } catch (err) {
            console.error("フレーム処理エラー:", err);
            this.showStatus('フレーム処理中にエラーが発生しました: ' + err.message, 'error');
        }
    }

    async sendFrames(frameDataArray) {
        try {
            const userRequestInput = document.getElementById('userRequestInput');
            const userRequest = userRequestInput ? userRequestInput.value : '';
            const requestData = {
                frames: frameDataArray,
                user_request: userRequest
            };
            const response = await fetch(this.config.pythonUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            // レスポンスから通知メッセージがあれば通知ログエリアに表示
            const data = await response.json();
            if (data.notification_message) {
                new Notification(data.notification_message);
                const notificationLogArea = document.getElementById('notificationLogArea');
                if (notificationLogArea) {
                    const logEntry = document.createElement('div');
                    logEntry.textContent = data.notification_message;
                    logEntry.style.padding = "4px 0";
                    logEntry.style.borderBottom = "1px solid #e0e0e0";
                    logEntry.style.fontSize = "0.95em";
                    notificationLogArea.prepend(logEntry);
                } else {
                    console.warn('要素 notificationLogArea が見つかりませんでした。');
                }
            }
        } catch (err) {
            console.error("Python処理エラー:", err);
            this.showStatus('Python処理中にエラーが発生しました: ' + err.message, 'error');
        }
    }

    showStatus(message, type) {
        if (!message) {
            statusMessage.classList.add('hidden');
            return;
        }
        statusMessage.textContent = message;
        statusMessage.className = 'status ' + type;
        statusMessage.classList.remove('hidden');
    }
}

const recorder = new Recorder({
    captureInterval: 500,
    frameThreshold: 60,
    pythonUrl: '/record_frame'
});

if (recordBtn) {
    recordBtn.addEventListener('click', async () => {
        if (!recorder.isRecording) {
            await recorder.start();
        } else {
            recorder.stop(); // This is already an async function, but not awaited here.
        }
        console.log('[DEBUG] recordBtn click handler finished.');
    });
}

// レポート生成ボタンのクリックイベントの追加
const makeReportBtn = document.getElementById('makeReportBtn');

// レポート生成ボタンのクリックイベント追加
if (makeReportBtn) {
    makeReportBtn.addEventListener('click', async () => {
        const statusSpan = document.getElementById('makeReportStatus');
        makeReportBtn.disabled = true;
        if (statusSpan) {
            statusSpan.textContent = '作成中...';
            statusSpan.style.color = '#4285f4';
        }
        try {
            const res = await fetch('/make_report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await res.json();
            if (data.status === 'success') {
                if (statusSpan) {
                    statusSpan.textContent = '作成完了';
                    statusSpan.style.color = '#34a853';
                }
            } else {
                if (statusSpan) {
                    statusSpan.textContent = '作成失敗';
                    statusSpan.style.color = '#ea4335';
                }
            }
        } catch (e) {
            if (statusSpan) {
                statusSpan.textContent = '作成失敗';
                statusSpan.style.color = '#ea4335';
            }
        } finally {
            makeReportBtn.disabled = false;
        }
    });
}
// Enable the "createProcedureBtn" and implement a similar recording logic for procedure creation
document.addEventListener('DOMContentLoaded', () => {
    const createProcedureBtn = document.getElementById('createProcedureBtn');
    const taskNameInput = document.getElementById('taskNameInput');

    if (createProcedureBtn && taskNameInput) {
        // Initially disable the button as taskNameInput will be empty
        createProcedureBtn.disabled = true;

        // Add event listener to the input field
        taskNameInput.addEventListener('input', () => {
            if (taskNameInput.value.trim() === '') {
                createProcedureBtn.disabled = true;
            } else {
                createProcedureBtn.disabled = false;
            }
        });
    }
    // The following 'if (createProcedureBtn)' block that unconditionally enabled the button
    // is no longer needed as the logic above now controls its state.

    class ProcedureRecorder extends Recorder {
        constructor(config) {
            super(config);
            this.mediaRecorder = null;
            this.recordedChunks = [];
            this.videoBlobURL = null;
        }

        async start() {
            try {
                this.showStatus('', '');
                this.mediaStream = await navigator.mediaDevices.getDisplayMedia({
                    video: { cursor: "always", displaySurface: "monitor" },
                    audio: false // Audio can be added later if needed
                });
                this.videoElement = document.createElement('video');
                this.videoElement.srcObject = this.mediaStream;

                await new Promise(resolve => {
                    this.videoElement.onloadedmetadata = () => {
                        this.videoElement.play();
                        // For video recording, we don't need to set canvas width/height based on video
                        // unless we were also doing frame grabs, which we are replacing.
                        resolve();
                    };
                });

                this.isRecording = true;
                // UI updates for procedure recorder
                const createProcedureBtn = document.getElementById('createProcedureBtn');
                if (createProcedureBtn) {
                    createProcedureBtn.textContent = '記録停止';
                    createProcedureBtn.className = 'stop-btn'; // Assuming similar styling
                }
                const procedureResult = document.getElementById('procedureResult');
                if (procedureResult) {
                    procedureResult.innerHTML = '録画中';
                    procedureResult.className = 'status info';
                    procedureResult.classList.remove('hidden');
                }

                // MediaRecorder setup
                const mimeType = 'video/webm; codecs=vp9';
                if (!MediaRecorder.isTypeSupported(mimeType)) {
                    console.warn(`[ProcedureRecorder] MIME type ${mimeType} not supported. Falling back to default.`);
                    // Potentially try 'video/webm' or let the browser decide by not specifying mimeType
                }

                this.mediaRecorder = new MediaRecorder(this.mediaStream, { mimeType: MediaRecorder.isTypeSupported(mimeType) ? mimeType : 'video/webm' });
                this.recordedChunks = [];

                this.mediaRecorder.ondataavailable = (event) => {
                    if (event.data && event.data.size > 0) {
                        this.recordedChunks.push(event.data);
                        console.log('[ProcedureRecorder] Data available, chunk size:', event.data.size, 'total chunks:', this.recordedChunks.length);
                    }
                };

                this.mediaRecorder.onstop = () => {
                    console.log('[ProcedureRecorder] MediaRecorder stopped. Total chunks:', this.recordedChunks.length);
                    // Logic for creating Blob and URL will be added in the next step
                    // For now, this indicates recording has stopped and data should be processed.
                };

                this.mediaRecorder.onerror = (event) => {
                    console.error('[ProcedureRecorder] MediaRecorder error:', event.error);
                    this.showStatus('録画エラー: ' + event.error.name, 'error');
                    // Potentially call this.stop() or handle the error more gracefully
                    if (this.isRecording) {
                        this.stop(); // Attempt to stop gracefully
                    }
                };

                this.mediaRecorder.start();
                console.log('[ProcedureRecorder] MediaRecorder started.');

                this.showStatus('ビデオ録画を開始しました', 'success'); // More specific status for video

                // Stop recording when the media stream ends (e.g., user stops screen sharing)
                this.mediaStream.getVideoTracks()[0].onended = () => {
                    if (this.isRecording) { // Ensure stop is only called if actively recording
                        this.stop();
                    }
                };

            } catch (err) {
                console.error("[ProcedureRecorder] Error starting recording:", err);
                if (err.name === 'NotAllowedError') {
                    this.showStatus('画面共有がキャンセルされました。', 'error');
                } else {
                    this.showStatus('録画開始エラー: ' + err.message, 'error');
                }
                this.isRecording = false; // Ensure recording state is false
                // Reset button states if start fails
                const createProcedureBtn = document.getElementById('createProcedureBtn');
                if (createProcedureBtn) {
                    createProcedureBtn.textContent = '記録開始';
                    createProcedureBtn.disabled = false;
                    createProcedureBtn.className = 'record-btn'; // Reset class on failure
                }
                const procedureResult = document.getElementById('procedureResult');
                if (procedureResult) {
                    procedureResult.classList.add('hidden');
                }
            }
        }

        async stop() {
            console.log('[ProcedureRecorder stop()] Entered stop method.');
            // Since ProcedureRecorder's start() doesn't set up samplingInterval,
            // we don't need to clear it here like in the parent Recorder.
            // clearInterval(this.samplingInterval);
            // this.samplingInterval = null;

            // Ensure createProcedureBtn is available for UI updates
            const createProcedureBtn = document.getElementById('createProcedureBtn');
            const procedureResult = document.getElementById('procedureResult');


            return new Promise(async (resolve, reject) => {
                if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
                    console.log('[ProcedureRecorder stop()] Stopping MediaRecorder.');

                    this.mediaRecorder.onstop = async () => {
                        console.log('[ProcedureRecorder onstop] MediaRecorder stopped. Total chunks:', this.recordedChunks.length);

                        if (this.recordedChunks.length === 0) {
                            console.warn('[ProcedureRecorder onstop] No video data recorded.');
                            this.showStatus('動画データがありません。', 'warning');
                            this.isRecording = false;
                            if (createProcedureBtn) {
                                 createProcedureBtn.textContent = '記録開始';
                                 createProcedureBtn.disabled = false;
                                 createProcedureBtn.className = 'record-btn'; // Reset class
                            }
                            if (procedureResult) {
                                procedureResult.innerHTML = '動画データなし';
                                procedureResult.className = 'status warning';
                                procedureResult.classList.remove('hidden');
                            }
                            resolve({ status: 'warning', message: 'No video data recorded.' });
                            return;
                        }

                        this.isRecording = false; // Set early, common path for subsequent operations

                        try {
                            // --- Start of Blob/URL creation ---
                            console.log('[ProcedureRecorder onstop] Inspecting recordedChunks before new Blob():', this.recordedChunks);
                            if (this.recordedChunks && Array.isArray(this.recordedChunks)) {
                                console.log('[ProcedureRecorder onstop] recordedChunks is an array. Length:', this.recordedChunks.length);
                                if (this.recordedChunks.length > 0) {
                                    console.log('[ProcedureRecorder onstop] Type of first chunk:', typeof this.recordedChunks[0], 'Is it a Blob?', this.recordedChunks[0] instanceof Blob);
                                    if (this.recordedChunks[0] instanceof Blob) {
                                        console.log('[ProcedureRecorder onstop] First chunk Blob size:', this.recordedChunks[0].size, 'type:', this.recordedChunks[0].type);
                                    }
                                }
                            } else {
                                console.warn('[ProcedureRecorder onstop] recordedChunks is not an array or is undefined/null.');
                            }
                            const videoBlob = new Blob(this.recordedChunks, { type: this.mediaRecorder.mimeType });
                            console.log('[ProcedureRecorder onstop] Created videoBlob. Is it a Blob?', videoBlob instanceof Blob, 'Value:', videoBlob);
                            if (videoBlob instanceof Blob) {
                                console.log('[ProcedureRecorder onstop] videoBlob details: size=', videoBlob.size, 'type=', videoBlob.type);
                            }
                            // Revoke previous blob URL if it exists, to free up resources
                            if (this.videoBlobURL) {
                                URL.revokeObjectURL(this.videoBlobURL);
                                this.videoBlobURL = null; // Clear it after revoking
                            }
                            this.videoBlobURL = URL.createObjectURL(videoBlob); // Store new URL, might be useful for local preview
                            console.log('[ProcedureRecorder onstop] Video Blob URL created (for potential preview):', this.videoBlobURL);
                            // --- End of Blob/URL creation ---

                            const userRequestInput = document.getElementById('procedureUserRequestInput');
                            const userRequest = userRequestInput ? userRequestInput.value : '';

                            const sendResult = await this.sendVideo(videoBlob, userRequest); // Pass videoBlob directly
                            console.log('[ProcedureRecorder onstop] sendVideo result:', sendResult);
                            resolve(sendResult);

                        } catch (error) { // Catches errors from Blob/URL creation OR sendVideo
                            console.error('[ProcedureRecorder onstop] Error during Blob/URL creation or sendVideo:', error);

                            // Update UI to reflect the error
                            if (procedureResult) {
                                procedureResult.innerHTML = 'ビデオ処理エラー: ' + error.message;
                                procedureResult.className = 'status error';
                                procedureResult.classList.remove('hidden');
                            }
                            this.showStatus('ビデオ処理エラー: ' + error.message, 'error'); // Main status update

                            reject(error); // Reject the main promise from stop()

                        } finally {
                            // This finally block will execute after try (even if resolved) or after catch.
                            // Ensure button is reset. isRecording is already false.
                             if (createProcedureBtn) {
                                 createProcedureBtn.textContent = '記録開始';
                                 createProcedureBtn.disabled = false;
                                 createProcedureBtn.className = 'record-btn'; // Reset class
                             }
                             // Other UI updates based on the overall outcome are typically handled
                             // by the click listener that awaits the stop() promise.
                             // The main UI update based on sendResult will be handled by the click listener
                             // using the resolved value of this promise.
                        }
                    };

                    this.mediaRecorder.onerror = (event) => { // Ensure onerror can reject the promise too
                        console.error('[ProcedureRecorder stop.onerror] MediaRecorder error during stop/onstop:', event.error);
                        this.isRecording = false;
                        if (createProcedureBtn) {
                            createProcedureBtn.textContent = '記録開始';
                            createProcedureBtn.disabled = false;
                            createProcedureBtn.className = 'record-btn'; // Reset class
                        }
                        if (procedureResult) {
                            procedureResult.innerHTML = '録画エラー';
                            procedureResult.className = 'status error';
                        }
                        reject(new Error('MediaRecorder error: ' + event.error.name));
                    };

                    this.mediaRecorder.stop();

                } else {
                    console.log('[ProcedureRecorder stop()] MediaRecorder not recording or not initialized.');
                    this.isRecording = false;
                     if (createProcedureBtn) {
                        createProcedureBtn.textContent = '記録開始';
                        createProcedureBtn.disabled = false;
                        createProcedureBtn.className = 'record-btn'; // Reset class
                    }
                    if (procedureResult && procedureResult.innerHTML === 'ビデオ処理中...') { // Clear if it was set
                        procedureResult.classList.add('hidden');
                    }
                    resolve({ status: 'no_recording', message: 'Not recording.' });
                }

                // Stop the media stream tracks (screen sharing)
                if (this.mediaStream) {
                    this.mediaStream.getTracks().forEach(track => track.stop());
                    this.mediaStream = null;
                    console.log('[ProcedureRecorder stop()] MediaStream tracks stopped.');
                }
                if (this.videoElement) {
                    this.videoElement.srcObject = null;
                    this.videoElement = null;
                    console.log('[ProcedureRecorder stop()] VideoElement cleaned up.');
                }

                // General status update, specific result messages handled by click listener
                // this.showStatus('ビデオ処理が完了しました。', 'info'); // Or based on actual outcome
            });
        }

    async sendVideo(videoBlob, userRequest) {
        const procedureResult = document.getElementById('procedureResult'); // For status updates
        try {
            const taskName = document.getElementById('taskNameInput').value || '';

            const formData = new FormData();
            formData.append('video_file', videoBlob, 'procedure_video.webm');
            formData.append('task_name', taskName);
            formData.append('user_request', userRequest);

            console.log('[ProcedureRecorder] Uploading video file to /upload_video with FormData.');
            // Optional: Log FormData entries for debugging
            // for (var pair of formData.entries()) {
            //    console.log(pair[0]+ ', ' + (pair[1] instanceof Blob ? 'Blob, size=' + pair[1].size : pair[1]));
            // }

            const response = await fetch('/upload_video', { // Changed endpoint
                method: 'POST',
                body: formData // No explicit Content-Type header here, browser sets it for FormData
            });

            const data = await response.json(); // Parse JSON response

            if (!response.ok) {
                let errorMsg = `HTTP error! status: ${response.status}`;
                errorMsg = data.message || errorMsg; // Use server message if available
                throw new Error(errorMsg);
            }

            if (data.status === 'success' && data.video_url) {
                // Update UI directly here or ensure the click listener does it.
                // For now, just log and return. The click listener will handle UI.
                console.log('[ProcedureRecorder] Video uploaded successfully:', data.video_url);
            } else if (data.status === 'error') {
                throw new Error(data.message || 'Unknown error during video upload.');
            }
            return data; // Return the JSON response

        } catch (err) {
            console.error("[ProcedureRecorder] sendVideo error:", err);
            if (procedureResult) {
                procedureResult.innerHTML = 'ビデオアップロードエラー: ' + err.message; // Updated error message
                procedureResult.className = 'status error';
                procedureResult.classList.remove('hidden');
            }
            throw err; // Re-throw the error for the caller (e.g., onstop handler) to handle
        }
    }
    }

    // Separate instance for procedure capturing
    const procedureRecorder = new ProcedureRecorder({
        // captureInterval and frameThreshold are not directly used by MediaRecorder
        // but might be relevant if there's fallback or mixed logic.
        // For now, their direct effect on MediaRecorder is minimal.
        captureInterval: 500,
        frameThreshold: 6000000
    });

    const procedureResult = document.getElementById('procedureResult');

    if (createProcedureBtn && procedureRecorder) {
        createProcedureBtn.addEventListener('click', async () => {
            if (!procedureRecorder.isRecording) {
                createProcedureBtn.disabled = true;
                // Initialize procedureResult message for starting phase
                if (procedureResult) {
                    procedureResult.innerHTML = '録画準備中...';
                    procedureResult.className = 'status info';
                    procedureResult.classList.remove('hidden');
                }

                try {
                    await procedureRecorder.start();

                    if (procedureRecorder.isRecording) {
                        // Button text ("記録停止") and procedureResult ("録画中") are set within start() on success.
                        // THE CRITICAL FIX: Re-enable the button so it can be clicked to stop.
                        createProcedureBtn.disabled = false;
                        console.log('[createProcedureBtn] Recording started successfully, button re-enabled for stopping.');
                    } else {
                        // This case means procedureRecorder.start() completed but isRecording is still false.
                        // This implies an internal failure in start() that was caught by start()'s own try/catch,
                        // which should have already reset the button text and re-enabled it.
                        // If for some reason the button wasn't re-enabled by start()'s catch block,
                        // ensure it's enabled here.
                        console.warn('[createProcedureBtn] procedureRecorder.start() likely failed internally (isRecording is false). Button state should be reset by start().');
                        if (createProcedureBtn.disabled) { // Double check if start() missed it
                           createProcedureBtn.disabled = false;
                           createProcedureBtn.textContent = '記録開始';
                        }
                        // procedureResult should also have been updated by start()'s catch block.
                    }
                } catch (error) {
                    // This catch in the listener is for errors if procedureRecorder.start() itself throws/rejects
                    // (i.e., not caught by its internal try/catch or if it re-throws).
                    console.error('[createProcedureBtn] Error awaiting procedureRecorder.start():', error);
                    // procedureRecorder.start() has its own comprehensive catch block that updates UI
                    // (button text, disabled status, procedureResult). So, this listener's catch
                    // might not need to do much more than log, unless start() fails very early.
                    // For safety, ensure the button is reset if not already.
                    if (createProcedureBtn) {
                        createProcedureBtn.textContent = '記録開始';
                        createProcedureBtn.disabled = false;
                    }
                    if (procedureResult) {
                        procedureResult.innerHTML = '録画開始エラー: ' + error.message;
                        procedureResult.className = 'status error';
                        procedureResult.classList.remove('hidden');
                    }
                }

                // Ensure statusMessage (main status) is not misleading
                const statusMessage = document.getElementById('statusMessage');
                if (statusMessage && statusMessage.textContent === '録画を開始しました' && procedureRecorder.isRecording) {
                    statusMessage.classList.add('hidden'); // Hide main status if procedure recorder is active
                } else if (statusMessage && statusMessage.textContent === 'ビデオ録画を開始しました' && !procedureRecorder.isRecording && recorder.isRecording) {
                    // This case should ideally not happen if procedure recorder failed and main recorder took over.
                    // However, this indicates a complex state. For now, let main status persist if it's specific.
                }


            } else {
                // This is the logic for STOPPING the procedure recorder
                if (procedureResult) {
                    procedureResult.innerHTML = '生成中...';
                    procedureResult.className = 'status info';
                    procedureResult.classList.remove('hidden');
                }
                createProcedureBtn.disabled = true;

                try {
                    const resultFromServer = await procedureRecorder.stop();
                    console.log('[createProcedureBtn] stop() result:', resultFromServer);

                    if (procedureResult) {
                        if (resultFromServer && resultFromServer.status === 'success' && resultFromServer.video_url) {
                            console.log('Video uploaded successfully. URL:', resultFromServer.video_url);
                            // procedureResult.innerHTML = 'アップロード成功'; // Commented out/Removed
                            // procedureResult.className = 'status success'; // Will be set by create_procedure call result

                            // Call /create_procedure
                            fetch('/create_procedure', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    task_name: document.getElementById('taskNameInput').value || '',
                                    user_request: document.getElementById('procedureUserRequestInput') ? document.getElementById('procedureUserRequestInput').value : '',
                                    video_url: resultFromServer.video_url
                                })
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.status === 'success') {
                                    procedureResult.innerHTML = '手順書作成成功';
                                    procedureResult.className = 'status success';
                                } else {
                                    procedureResult.innerHTML = '手順書作成失敗: ' + (data.message || '不明なエラー');
                                    procedureResult.className = 'status error';
                                }
                            })
                            .catch(error => {
                                console.error('Error calling /create_procedure:', error);
                                procedureResult.innerHTML = '手順書作成リクエストエラー: ' + error.message;
                                procedureResult.className = 'status error';
                            });

                        } else if (resultFromServer && resultFromServer.status === 'warning' && resultFromServer.message === 'No video data recorded.') {
                            // Already handled by onstop's UI update for this specific case.
                            // procedureResult.innerHTML = '動画データなし';
                            // procedureResult.className = 'status warning';
                        } else if (resultFromServer && resultFromServer.status === 'no_recording') {
                             procedureResult.innerHTML = '録画されていませんでした';
                             procedureResult.className = 'status info';
                        } else if (resultFromServer && resultFromServer.message) { // Check for message from server on error
                            procedureResult.innerHTML = `ビデオアップロード失敗: ${resultFromServer.message}`;
                            procedureResult.className = 'status error';
                        } else if (resultFromServer && resultFromServer.status === 'error') { // Generic error if no message
                            procedureResult.innerHTML = 'ビデオアップロード失敗: 不明なエラー';
                            procedureResult.className = 'status error';
                        }
                         else {
                            procedureResult.innerHTML = 'ビデオ処理完了 (結果不明)';
                            procedureResult.className = 'status warning';
                        }
                    }
                } catch (error) {
                    console.error('[createProcedureBtn] Error calling stop():', error);
                    if (procedureResult) {
                        procedureResult.innerHTML = `処理エラー: ${error.message || '不明なエラー'}`;
                        procedureResult.className = 'status error';
                    }
                } finally {
                    // Ensure button is reset if not already handled by stop()/onstop() for all paths
                    if (!procedureRecorder.isRecording) {
                         createProcedureBtn.textContent = '記録開始';
                         createProcedureBtn.disabled = false;
                         createProcedureBtn.className = 'record-btn'; // Reset class
                    }
                }

                const statusMessage = document.getElementById('statusMessage');
                // Clear main status message if it was showing a stop message from the generic recorder
                if (statusMessage && (statusMessage.textContent === '停止しました' || statusMessage.textContent === 'ビデオ録画を停止しました')) {
                    statusMessage.classList.add('hidden');
                }
            }
        });
    }
});

// AIサポートチェックボックスの処理
const aiSupportCheckbox = document.getElementById('aiSupportCheckbox');
let pollNotifySupportInterval = null;

function startSupportCheck() {
    // 既に開始されていたら何もしない、または条件を満たしていない場合は何もしない
    if (pollNotifySupportInterval || !aiSupportCheckbox || !aiSupportCheckbox.checked || !recorder.isRecording || Notification.permission !== 'granted') {
        return;
    }

    pollNotifySupportInterval = setInterval(async () => {
        const currentFrame = recorder.latestFrameForAINotify;

        if (currentFrame && currentFrame === recorder.lastFrameSentToAINotify) {
            // console.log("AI Support: Frame identical to last sent. Skipping API call.");
            return;
        }

        // Get logContext (as it might have changed even if frame is null)
        const notificationLogArea = document.getElementById('notificationLogArea');
        let logContext = "";
        if (notificationLogArea) {
            logContext = notificationLogArea.innerText || "";
        }

        try {
            // Update lastFrameSentToAINotify with the frame we are about to send,
            // but only if it's a non-null frame.
            if (currentFrame) {
                recorder.lastFrameSentToAINotify = currentFrame;
            }

            const resp = await fetch('/api/notify_support', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    frames: currentFrame ? [currentFrame] : [],
                    log_context: logContext
                })
            });
            if (!resp.ok) {
                console.error('notify_support API Error:', resp.status);
                return;
            }
            const data = await resp.json();
            // status: "success" の場合は通知メッセージがある
            if (data.status === 'success' && data.notification_message) {
                // 通知する
                new Notification(data.notification_message);
                const notificationLogArea = document.getElementById('notificationLogArea');
                if (notificationLogArea) {
                    const logEntry = document.createElement('div');
                    logEntry.textContent = data.notification_message;
                    logEntry.style.padding = "4px 0";
                    logEntry.style.borderBottom = "1px solid #e0e0e0";
                    logEntry.style.fontSize = "0.95em";
                    notificationLogArea.prepend(logEntry);
                }
            }
        } catch (err) {
            console.error('AIサポート通知チェック中にエラー:', err);
        }
    }, 3000);
}

function stopSupportCheck() {
    if (pollNotifySupportInterval) {
        clearInterval(pollNotifySupportInterval);
        pollNotifySupportInterval = null;
    }
}

if (aiSupportCheckbox) {
    aiSupportCheckbox.addEventListener('change', function () {
        if (this.checked) {
            console.log('AIサポートチェックボックスがONになりました。通知許可を要求します。');
            Notification.requestPermission().then(function (permission) {
                console.log('通知許可の状態:', permission);
                if (permission === 'granted') {
                    console.log('通知が許可されました。');
                    startSupportCheck();
                } else if (permission === 'denied') {
                    console.log('通知が拒否されました。');
                    // 必要であれば、ユーザーに再度許可を求めるUIを表示するなどの処理をここに追加できます。
                    // ただし、一度拒否されると、ブラウザの設定を変更しない限り再度ダイアログは表示されません。
                } else {
                    console.log('通知許可の選択が保留されました（ダイアログが閉じられたなど）。');
                }
            }).catch(function (err) {
                console.error('通知許可の要求中にエラーが発生しました:', err);
            });
        } else {
            console.log('AIサポートチェックボックスがOFFになりました。');
            stopSupportCheck();
        }
    });

    // This nested event listener for 'change' was redundant and problematic.
    // It's removed as the logic is now handled by the outer event listener and the DOMContentLoaded listener.

} else {
    console.warn('要素 aiSupportCheckbox が見つかりませんでした。');
}

// Note: The testNotificationBtn related code block that was here has been removed.
// ページ読み込み時にAIサポートチェックボックスがチェック済みの場合、通知許可を要求(ポーリングは録画開始時に判断)
document.addEventListener("DOMContentLoaded", () => {
    if (typeof aiSupportCheckbox !== 'undefined' && aiSupportCheckbox && aiSupportCheckbox.checked) {
        if (Notification.permission !== 'granted') {
            Notification.requestPermission().then((permission) => {
                if (permission === 'granted') {
                    console.log('通知が許可されました。');
                    // Polling will be started by recorder.start() if conditions are met
                } else {
                    console.log('通知は許可されませんでした:', permission);
                }
            });
        }
        // Do not start polling here; recorder.start() will handle it.
    }
});