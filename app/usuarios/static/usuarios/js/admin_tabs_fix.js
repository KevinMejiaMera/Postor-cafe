// 📁 app/usuarios/static/usuarios/js/admin_tabs_fix.js

(function () {
    console.log("🚀 Jazzmin Hard Refresh Script: CARGADO");

    function hardReload(hash) {
        console.log("🔄 Ejecutando refresco automático para pestaña:", hash);
        window.location.hash = hash;
        window.location.reload();
    }

    // Usamos mousedown para interceptar ANTES que el JS de Jazzmin
    document.addEventListener('mousedown', function (e) {
        const link = e.target.closest('a.nav-link');
        if (link && link.getAttribute('href') && link.getAttribute('href').startsWith('#')) {
            const hash = link.getAttribute('href');
            // Un pequeño delay para dejar al navegador procesar el clic y luego refrescar
            setTimeout(() => hardReload(hash), 10);
        }
    }, true);
})();
