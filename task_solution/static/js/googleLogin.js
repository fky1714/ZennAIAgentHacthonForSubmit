// googleLogin.js
// Googleログインボタンの描画およびコールバック処理

function initializeGoogleSignIn() {
    if (window.google && window.google.accounts && window.google.accounts.id) {
        google.accounts.id.initialize({
            client_id: '449349434961-h0kjj9f7j4u8n6qdi6a914a5jqadu9hs.apps.googleusercontent.com',
            callback: handleGoogleSignIn
        });
        google.accounts.id.renderButton(
            document.getElementById("googleSignInBtn"),
            { theme: "outline", size: "large" }
        );
        document.getElementById("googleSignInBtn").style.display = "block";
        console.log('Google Sign-In initialized successfully');
    } else {
        // Google GIS がまだ読み込まれていない場合、100ms後に再試行
        setTimeout(initializeGoogleSignIn, 100);
    }
}

// DOMContentLoaded または window.onload で初期化開始
window.addEventListener('DOMContentLoaded', initializeGoogleSignIn);

// Google Identity Servicesのコールバック
function handleGoogleSignIn(response) {
    if (!response.credential || response.credential.trim() === "") {
        document.getElementById("googleSignInBtn").style.display = "block";
        return;
    }
    const id_token = response.credential;
    fetch("/google_login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: id_token })
    })
        .then(res => res.json())
        .then(data => {
            const loginStatus = document.getElementById('loginStatus');
            loginStatus.classList.remove('hidden');
            if (data.status === "success") {
                loginStatus.textContent = data.email;
                document.getElementById("googleSignInBtn").style.display = "none";
            } else {
                loginStatus.textContent = "ログイン失敗...";
                document.getElementById("googleSignInBtn").style.display = "none";
                console.error("ログイン失敗:", data);
            }
        })
        .catch(err => {
            console.error("ログイン通信エラー:", err);
        });
}

function handleGoogleLogout() {
    const loginStatus = document.getElementById('loginStatus');
    loginStatus.textContent = '';
    loginStatus.classList.add('hidden');
    const btn = document.getElementById("googleSignInBtn");
    btn.textContent = "Sign in with Google";
    btn.onclick = null;
    if (window.google && window.google.accounts && window.google.accounts.id) {
        google.accounts.id.renderButton(
            document.getElementById("googleSignInBtn"),
            { theme: "outline", size: "large" }
        );
    }
}

// windowスコープにアタッチしてHTMLから呼び出せるように
window.handleGoogleSignIn = handleGoogleSignIn;