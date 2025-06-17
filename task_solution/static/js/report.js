(function () {
    // 日付をyyyy-mm-dd形式に変換する関数
    function formatDateToYMD(dateStr) {
        if (!dateStr) return "";
        const d = new Date(dateStr);
        if (isNaN(d)) return dateStr;
        // JST（日本時間）に変換
        const jst = new Date(d.getTime() + 9 * 60 * 60 * 1000);
        const yyyy = jst.getFullYear();
        const mm = String(jst.getMonth() + 1).padStart(2, '0');
        const dd = String(jst.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    }
    // report.js loaded

    let reportCurrentPage = 1;
    let reportPageSize = 10;
    let currentReport = null;
    let reportIsEditing = false;
    let reportIsDirty = false;
    let originalReport = null;

    // レポート一覧取得・描画
    async function loadReportList(page = 1) {
        console.log("loadReportList called with page=", page);

        let newPage = parseInt(page, 10);
        if (isNaN(newPage) || newPage < 1) {
            console.warn(`Invalid page value '${page}' received for report list. Defaulting to 1.`);
            newPage = 1;
        }
        reportCurrentPage = newPage;
        // console.log("Sanitized reportCurrentPage:", reportCurrentPage); // For debugging

        try {
            const res = await fetch(`/api/reports?page=${reportCurrentPage}&page_size=${reportPageSize}`);
            console.log("Response status for /api/reports:", res.status);
            const data = await res.json();
            console.log("/api/reports response JSON:", data);
            if (data.status !== "success") {
                console.warn("API returned not success status:", data);
                return;
            }
            const reports = data.reports;
            const container = document.getElementById("reportListContainer");
            container.innerHTML = "";
            if (reports.length === 0) {
                container.innerHTML = "<p>レポートがありません</p>";
                document.getElementById("pageInfo").textContent = `ページ ${reportCurrentPage}`;
                document.getElementById("prevPageBtn").disabled = true;
                document.getElementById("nextPageBtn").disabled = true;
                return;
            }
            const ul = document.createElement("ul");
            reports.forEach(report => {
                const li = document.createElement("li");
                li.textContent = `${report.title ? report.title.substring(0, 40) : ""}`;
                li.style.cursor = "pointer";
                li.onclick = () => showReportDetail(report.id);
                ul.appendChild(li);
            });
            container.appendChild(ul);
            document.getElementById("pageInfo").textContent = `ページ ${reportCurrentPage}`;

            // ページングボタン制御
            const prevBtn = document.getElementById("prevPageBtn");
            const nextBtn = document.getElementById("nextPageBtn");
            // 1ページしか存在しない場合は両方無効
            if (reportCurrentPage === 1 && reports.length < reportPageSize) {
                prevBtn.disabled = true;
                nextBtn.disabled = true;
            } else {
                prevBtn.disabled = reportCurrentPage === 1;
                nextBtn.disabled = reports.length < reportPageSize;
            }
        } catch (err) {
            console.error("Error calling /api/reports:", err);
            return;
        }
    }

    // レポート詳細取得・表示
    async function showReportDetail(reportId) {
        const res = await fetch(`/api/reports/${reportId}`);
        const data = await res.json();
        if (data.status !== "success") {
            alert("レポート取得に失敗しました");
            return;
        }
        currentReport = data.report;
        originalReport = { ...currentReport };
        reportIsEditing = false;
        reportIsDirty = false;
        switchToDetailPanel();
        renderReportDetail();
    }

    // 詳細パネル表示
    function switchToDetailPanel() {
        document.getElementById("panelReportList").classList.add("hidden");
        document.getElementById("panelReportDetail").classList.remove("hidden");
        // 手順書系パネルも必ず非表示
        const procList = document.getElementById("panelProcedureList");
        const procDetail = document.getElementById("panelProcedureDetail");
        if (procList) procList.classList.add("hidden");
        if (procDetail) procDetail.classList.add("hidden");
    }

    // 一覧パネル表示
    function switchToListPanel() {
        document.getElementById("panelReportDetail").classList.add("hidden");
        document.getElementById("panelReportList").classList.remove("hidden");
        // 手順書系パネルも必ず非表示
        const procList = document.getElementById("panelProcedureList");
        const procDetail = document.getElementById("panelProcedureDetail");
        if (procList) procList.classList.add("hidden");
        if (procDetail) procDetail.classList.add("hidden");
        loadReportList(reportCurrentPage);
    }

    // 詳細画面描画
    function renderReportDetail() {
        const titleElem = document.getElementById("reportTitle");
        titleElem.textContent = currentReport ? currentReport.title : "";

        // ボタン表示切り替え
        const editBtn = document.getElementById("editReportBtn");
        const previewBtn = document.getElementById("previewReportBtn");
        if (reportIsEditing) {
            editBtn.style.display = "none";
            previewBtn.style.display = "";
        } else {
            editBtn.style.display = "";
            previewBtn.style.display = "none";
        }
        // Saveボタンの有効/無効制御
        const saveBtn = document.getElementById("saveReportBtn");
        saveBtn.disabled = !reportIsDirty;

        // タイトル編集可否
        titleElem.contentEditable = reportIsEditing ? "true" : "false";
        titleElem.style.borderBottom = reportIsEditing ? "1px dashed #888" : "none";
        titleElem.oninput = reportIsEditing
            ? () => {
                reportIsDirty = true;
                currentReport.title = titleElem.textContent;
                // Saveボタンを有効化
                document.getElementById("saveReportBtn").disabled = false;
            }
            : null;

        const contentElem = document.getElementById("reportContent");
        const contentView = document.getElementById("reportContentView");

        if (!currentReport) {
            contentElem.style.display = "";
            contentElem.value = "";
            contentView.style.display = "none";
            return;
        }
        if (reportIsEditing) {
            contentElem.style.display = "";
            contentView.style.display = "none";
            contentElem.value = currentReport.content;
            contentElem.oninput = () => {
                reportIsDirty = true;
                currentReport.content = contentElem.value;
                saveBtn.disabled = false;
            };
        } else {
            contentElem.style.display = "none";
            contentView.style.display = "";
            contentView.innerHTML = marked.parse(currentReport.content || "", { breaks: true });
        }
    }

    // 保存
    async function saveReport() {
        if (!currentReport) return;
        const res = await fetch(`/api/reports/${currentReport.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: currentReport.title,
                content: currentReport.content
            })
        });
        const data = await res.json();
        if (data.status === "success") {
            alert("保存しました");
            reportIsEditing = false;
            currentReport = data.content;
            originalReport = { ...currentReport };
            renderReportDetail();
        } else {
            alert("保存に失敗しました");
        }
    }

    // 削除
    async function deleteReport() {
        if (!currentReport) return;
        if (!confirm("本当に削除しますか？")) return;
        const res = await fetch(`/api/reports/${currentReport.id}`, { method: "DELETE" });
        const data = await res.json();
        if (data.status === "success") {
            alert("削除しました");
            switchToListPanel();
        } else {
            alert("削除に失敗しました");
        }
    }

    // 戻る
    function backToList() {
        if (reportIsEditing && !confirm("編集内容が破棄されます。よろしいですか？")) return;
        switchToListPanel();
    }

    // ページング
    document.addEventListener("DOMContentLoaded", () => {
        document.getElementById("prevPageBtn").onclick = () => {
            if (reportCurrentPage > 1) loadReportList(reportCurrentPage - 1);
        };
        document.getElementById("nextPageBtn").onclick = () => {
            loadReportList(reportCurrentPage + 1);
        };
        document.getElementById("saveReportBtn").onclick = saveReport;
        document.getElementById("deleteReportBtn").onclick = deleteReport;
        document.getElementById("backToReportListBtn").onclick = backToList;
        // Edit/Previewボタン
        document.getElementById("editReportBtn").onclick = () => {
            reportIsEditing = true;
            renderReportDetail();
        };
        document.getElementById("previewReportBtn").onclick = () => {
            reportIsEditing = false;
            renderReportDetail();
        };
        loadReportList();

        // Ellipsis menu for report detail
        const reportEllipsisBtn = document.querySelector('#panelReportDetail .ellipsis-button');
        if (reportEllipsisBtn) {
            reportEllipsisBtn.addEventListener('click', function (event) {
                event.stopPropagation();
                const dropdown = event.currentTarget.closest('.actions-menu').querySelector('.actions-dropdown');
                if (dropdown) {
                    dropdown.classList.toggle('show-dropdown');
                }
            });
        }
    });

    // Global click listener to close dropdowns (can be defined in one common place ideally)
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
    window.loadReportList = loadReportList;
    window.showReportDetail = showReportDetail;
})();