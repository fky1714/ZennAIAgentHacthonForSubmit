(function () {
    // procedure.js
    // 手順書一覧・詳細・編集・削除・ページングのロジック

    let procedureCurrentPage = 1;
    let procedurePageSize = 10;
    let currentProcedure = null;
    let procedureIsEditing = false;
    let procedureIsDirty = false;
    let originalProcedure = null;

    // 手順書一覧取得・描画
    async function loadProcedureList(page = 1) {
        console.log("loadProcedureList called with page=" + page); // Original console.log can remain or be updated

        let newPage = parseInt(page, 10);
        if (isNaN(newPage) || newPage < 1) {
            // console.warn(`Invalid page value '${page}' received. Defaulting to 1.`); // Removed
            newPage = 1;
        }
        procedureCurrentPage = newPage;
        // Ensure procedureCurrentPage is used in the fetch URL
        // console.log("Sanitized procedureCurrentPage:", procedureCurrentPage); // For debugging

        try {
            const res = await fetch(`/api/procedures?page=${procedureCurrentPage}&page_size=${procedurePageSize}`);
            console.log("Response status for /api/procedures:", res.status);
            const data = await res.json();
            console.log("/api/procedures response JSON:", data);
            if (data.status !== "success") {
                console.log("API returned not success status:", data);
                return;
            }
            const procedures = data.procedures;
            const container = document.getElementById("procedureListContainer");
            container.innerHTML = "";
            if (procedures.length === 0) {
                container.innerHTML = "<p>手順書がありません</p>";
                document.getElementById("procedurePageInfo").textContent = `ページ ${procedureCurrentPage}`;
                document.getElementById("prevProcedurePageBtn").disabled = true;
                document.getElementById("nextProcedurePageBtn").disabled = true;
                return;
            }
            const ul = document.createElement("ul");
            procedures.forEach(procedure => {
                const li = document.createElement("li");
                // FirestoreServiceの返却仕様に合わせて
                li.textContent = procedure.task_name ? procedure.task_name : "";
                li.style.cursor = "pointer";
                li.onclick = () => showProcedureDetail(procedure.task_name);
                ul.appendChild(li);
            });
            container.appendChild(ul);
            document.getElementById("procedurePageInfo").textContent = `ページ ${procedureCurrentPage}`;

            // ページングボタン制御
            const prevBtn = document.getElementById("prevProcedurePageBtn");
            const nextBtn = document.getElementById("nextProcedurePageBtn");
            // 1ページしか存在しない場合は両方無効
            if (procedureCurrentPage === 1 && procedures.length < procedurePageSize) {
                prevBtn.disabled = true;
                nextBtn.disabled = true;
            } else {
                prevBtn.disabled = procedureCurrentPage === 1;
                // Corrected line:
                nextBtn.disabled = procedures.length < procedurePageSize;
            }
        } catch (e) {
            console.error("Error calling /api/procedures:", e);
            return;
        }
    }
    window.loadProcedureList = loadProcedureList;

    // 手順書詳細取得・表示
    async function showProcedureDetail(procedureId) {
        console.log("[showProcedureDetail] Fetching procedure with ID (task_name):", procedureId);
        const res = await fetch(`/api/procedures/${procedureId}`);
        const data = await res.json();
        console.log("[showProcedureDetail] Received data:", data);
        if (data.status !== "success") {
            alert("手順書取得に失敗しました");
            return;
        }
        window.currentProcedure = data.procedure;
        console.log("[showProcedureDetail] Set window.currentProcedure to:", window.currentProcedure);
        window.originalProcedure = { ...window.currentProcedure };
        window.procedureIsEditing = false;
        window.procedureIsDirty = false;
        switchToDetailPanel();
        renderProcedureDetail();
    }

    // 詳細パネル表示
    function switchToDetailPanel() {
        document.getElementById("panelProcedureList").classList.add("hidden");
        document.getElementById("panelProcedureDetail").classList.remove("hidden");
        // レポート系パネルも必ず非表示
        const reportList = document.getElementById("panelReportList");
        const reportDetail = document.getElementById("panelReportDetail");
        if (reportList) reportList.classList.add("hidden");
        if (reportDetail) reportDetail.classList.add("hidden");
    }

    // 一覧パネル表示
    function switchToListPanel() {
        document.getElementById("panelProcedureDetail").classList.add("hidden");
        document.getElementById("panelProcedureList").classList.remove("hidden");
        // レポート系パネルも必ず非表示
        const reportList = document.getElementById("panelReportList");
        const reportDetail = document.getElementById("panelReportDetail");
        if (reportList) reportList.classList.add("hidden");
        if (reportDetail) reportDetail.classList.add("hidden");
        loadProcedureList(procedureCurrentPage);
    }

    // 詳細画面描画
    function renderProcedureDetail() {
        const titleElem = document.getElementById("procedureTitle");
        titleElem.textContent = window.currentProcedure ? window.currentProcedure.task_name : "";

        // ボタン表示切り替え
        const editBtn = document.getElementById("editProcedureBtn");
        const previewBtn = document.getElementById("previewProcedureBtn");
        if (window.procedureIsEditing) {
            editBtn.style.display = "none";
            previewBtn.style.display = "";
        } else {
            editBtn.style.display = "";
            previewBtn.style.display = "none";
        }
        // Saveボタンの有効/無効制御
        const saveBtn = document.getElementById("saveProcedureBtn");
        saveBtn.disabled = !window.procedureIsDirty;

        // タイトル編集可否
        titleElem.contentEditable = window.procedureIsEditing ? "true" : "false";
        titleElem.style.borderBottom = window.procedureIsEditing ? "1px dashed #888" : "none";
        titleElem.oninput = window.procedureIsEditing
            ? () => {
                window.procedureIsDirty = true;
                window.currentProcedure.task_name = titleElem.textContent;
                // Saveボタンを有効化
                document.getElementById("saveProcedureBtn").disabled = false;
            }
            : null;

        const contentElem = document.getElementById("procedureContent");
        const contentView = document.getElementById("procedureContentView");
        if (!window.currentProcedure) {
            contentElem.style.display = "";
            contentElem.value = "";
            contentView.style.display = "none";
            return;
        }

        if (window.procedureIsEditing) {
            contentElem.style.display = "";
            contentView.style.display = "none";
            contentElem.value = window.currentProcedure.content;
            contentElem.oninput = () => {
                window.procedureIsDirty = true;
                window.currentProcedure.content = contentElem.value;
                saveBtn.disabled = false;
            };
        } else {
            contentElem.style.display = "none";
            contentView.style.display = "";
            contentView.innerHTML = marked.parse(window.currentProcedure.content || "");
        }
    }

    // 保存
    async function saveProcedure() {
        if (!window.currentProcedure) return;
        const res = await fetch(`/api/procedures/${encodeURIComponent(window.currentProcedure.task_name)}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: window.currentProcedure.task_name,
                content: window.currentProcedure.content
            })
        });
        const data = await res.json();
        if (data.status === "success") {
            alert("保存しました");
            window.procedureIsEditing = false;
            window.currentProcedure = { ...window.currentProcedure, ...data.content };
            window.originalProcedure = { ...window.currentProcedure };
            renderProcedureDetail();
        } else {
            alert("保存に失敗しました");
        }
    }

    // 削除
    async function deleteProcedure() {
        console.log("[deleteProcedure] Entered. window.currentProcedure:", JSON.stringify(window.currentProcedure, null, 2)); // Pretty print JSON
        if (window.currentProcedure) {
            console.log("[deleteProcedure] window.currentProcedure.task_name:", window.currentProcedure.task_name);
            console.log("[deleteProcedure] typeof window.currentProcedure.task_name:", typeof window.currentProcedure.task_name);
        } else {
            console.log("[deleteProcedure] window.currentProcedure is null or undefined at function start.");
        }

        // console.log("[deleteProcedure] Current procedure object:", window.currentProcedure); // This is now covered by the JSON.stringify above
        if (!window.currentProcedure) {
            console.error("[deleteProcedure] No current procedure to delete (checked after initial logs).");
            return;
        }
        if (!confirm("本当に削除しますか？")) return;

        // Log which ID is being used
        const idForDelete = window.currentProcedure.id; // Logged for historical/debugging context if needed
        const taskNameForDelete = window.currentProcedure.task_name; // This is the identifier now used for deletion.

        try {
            if (!taskNameForDelete || typeof taskNameForDelete !== 'string' || taskNameForDelete.trim() === "") {
                console.error("[deleteProcedure] Invalid task_name (checked before encoding):", taskNameForDelete);
                alert("手順の識別に失敗しました。削除できません。");
                return;
            }
            const encodedTaskName = encodeURIComponent(taskNameForDelete);
            const fetchUrl = `/api/procedures/${encodedTaskName}`;

            const res = await fetch(fetchUrl, { method: "DELETE" });
            const responseText = await res.text();
            let data;
            try {
                data = JSON.parse(responseText);
            } catch (e) {
                console.error("[deleteProcedure] Failed to parse server response as JSON:", e);
                alert("削除中にサーバーから予期せぬ応答がありました。詳細はコンソールを確認してください。");
                return;
            }

            console.log("[deleteProcedure] Parsed server response data:", data);
            if (data.status === "success") {
                alert("削除しました");
                switchToListPanel();
            } else {
                alert(`削除に失敗しました: ${data.message || 'サーバーエラー'}`);
                console.error("[deleteProcedure] Deletion failed, server response data:", data);
            }
        } catch (error) {
            // This outer catch handles network errors or issues before res.text()
            alert("削除中に通信エラーが発生しました。");
            console.error("[deleteProcedure] Network or fetch setup error:", error);
        }
    }

    // 戻る
    function backToList() {
        if (window.procedureIsEditing && !confirm("編集内容が破棄されます。よろしいですか？")) return;
        switchToListPanel();
    }

    // ページング
    document.addEventListener("DOMContentLoaded", () => {
        document.getElementById("prevProcedurePageBtn").onclick = () => {
            let parsedPage = parseInt(procedureCurrentPage, 10);
            if (isNaN(parsedPage)) {
                // console.error("[DEBUG] CRITICAL: procedureCurrentPage was NaN AT THE START of 'Previous' click handler! Defaulting to page 1 for safety before -1."); // REMOVE
                parsedPage = 1;
            }
            let pageToLoad;
            if (parsedPage > 1) {
                pageToLoad = parsedPage - 1;
            } else {
                pageToLoad = 1;
            }
            loadProcedureList(pageToLoad);
        };
        document.getElementById("nextProcedurePageBtn").onclick = () => {
            let parsedPage = parseInt(procedureCurrentPage, 10);
            if (isNaN(parsedPage)) {
                // console.error("[DEBUG] CRITICAL: procedureCurrentPage was NaN AT THE START of 'Next' click handler! Defaulting to page 1 for safety before +1."); // REMOVE
                parsedPage = 1;
            }
            let pageToLoad = parsedPage + 1;
            loadProcedureList(pageToLoad);
        };
        document.getElementById("saveProcedureBtn").onclick = saveProcedure;
        document.getElementById("deleteProcedureBtn").onclick = deleteProcedure;
        document.getElementById("backToProcedureListBtn").onclick = backToList;
        // Edit/Previewボタン
        document.getElementById("editProcedureBtn").onclick = () => {
            window.procedureIsEditing = true;
            renderProcedureDetail();
        };
        document.getElementById("previewProcedureBtn").onclick = () => {
            window.procedureIsEditing = false;
            renderProcedureDetail();
        };
        loadProcedureList();

        // Ellipsis menu for procedure detail
        const procedureEllipsisBtn = document.querySelector('#panelProcedureDetail .ellipsis-button');
        if (procedureEllipsisBtn) {
            procedureEllipsisBtn.addEventListener('click', function (event) {
                event.stopPropagation();
                const dropdown = event.currentTarget.closest('.actions-menu').querySelector('.actions-dropdown');
                if (dropdown) {
                    dropdown.classList.toggle('show-dropdown');
                }
            });
        }
    });

    // Global click listener to close dropdowns
    document.addEventListener('click', function (event) {
        const openDropdowns = document.querySelectorAll('.actions-dropdown.show-dropdown');
        openDropdowns.forEach(dropdown => {
            const menu = dropdown.closest('.actions-menu');
            // If the click is outside the menu containing this dropdown
            if (menu && !menu.contains(event.target)) {
                dropdown.classList.remove('show-dropdown');
            }
        });
    });

    // 必要な関数だけwindowにexport
    window.loadProcedureList = loadProcedureList;
    window.showProcedureDetail = showProcedureDetail;
    // 他に外部から呼ばれる関数があればここでexport
})();