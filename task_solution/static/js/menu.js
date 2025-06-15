console.log("menu.js loaded");
// menu.js
// サイドメニューの切り替え機能をまとめるファイル

window.addEventListener('DOMContentLoaded', function () {
    const menuRecording = document.getElementById('menuRecording');
    const menuProcedure = document.getElementById('menuProcedure');
    const menuReportList = document.getElementById('menuReportList');
    const menuProcedureList = document.getElementById('menuProcedureList');
    const panelRecording = document.getElementById('panelRecording');
    const panelProcedure = document.getElementById('panelProcedure');
    const panelReportList = document.getElementById('panelReportList');
    const panelReportDetail = document.getElementById('panelReportDetail');

    function hideAllPanels() {
        panelRecording.classList.add('hidden');
        panelProcedure.classList.add('hidden');
        panelReportList.classList.add('hidden');
        panelReportDetail.classList.add('hidden');
        document.getElementById('panelProcedureList').classList.add('hidden');
        document.getElementById('panelProcedureDetail').classList.add('hidden');
        menuRecording.classList.remove('active');
        menuProcedure.classList.remove('active');
        menuReportList.classList.remove('active');
        menuProcedureList.classList.remove('active');
    }

    menuRecording.addEventListener('click', () => {
        hideAllPanels();
        menuRecording.classList.add('active');
        panelRecording.classList.remove('hidden');
    });

    menuProcedure.addEventListener('click', () => {
        hideAllPanels();
        menuProcedure.classList.add('active');
        panelProcedure.classList.remove('hidden');
    });

    menuReportList.addEventListener('click', () => {
        console.log("Clicked 'レポート一覧' menu. Checking if loadReportList is defined.");
        hideAllPanels();
        menuReportList.classList.add('active');
        panelReportList.classList.remove('hidden');
        console.log("typeof window.loadReportList:", typeof window.loadReportList);
        console.log("window object snapshot:", window);
        if (typeof window.loadReportList === 'function') {
            console.log("Calling window.loadReportList(1)...");
            window.loadReportList(1);
        } else {
            console.warn("window.loadReportList is not defined or not a function.");
        }
    });
    menuProcedureList.addEventListener('click', () => {
        hideAllPanels();
        menuProcedureList.classList.add('active');
        document.getElementById('panelProcedureList').classList.remove('hidden');
        if (typeof window.loadProcedureList === 'function') {
            window.loadProcedureList(1);
        }
    });
});