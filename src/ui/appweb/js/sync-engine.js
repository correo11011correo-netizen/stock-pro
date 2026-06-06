const SyncEngine = {
    async sync() {
        console.log("Sincronizando con el servidor...");
        const statusEl = document.getElementById('sync-status');
        
        try {
            // 1. Enviar cambios locales al servidor (PUSH)
            const queue = await LocalDB.getQueue();
            if (queue.length > 0) {
                statusEl.textContent = "Subiendo cambios...";
                statusEl.className = "status-syncing";
                
                const response = await fetch('/api/sync/push', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Authorization': sessionStorage.getItem('admin_token') || ''
                    },
                    body: JSON.stringify({ events: queue })
                });
                
                if (response.ok) {
                    await LocalDB.clearQueue();
                }
            }

            // 2. Traer actualizaciones del servidor (PULL)
            statusEl.textContent = "Actualizando Stock...";
            const pullRes = await fetch('/api/sync/pull', {
                headers: { 'Authorization': sessionStorage.getItem('admin_token') || '' }
            });
            
            if (pullRes.ok) {
                const data = await pullRes.json();
                if (data.products) {
                    for (const prod of data.products) {
                        await LocalDB.saveProduct(prod);
                    }
                }
            }

            statusEl.textContent = "Online";
            statusEl.className = "status-online";
        } catch (e) {
            console.error("Error de sincronización:", e);
            statusEl.textContent = "Offline";
            statusEl.className = "status-offline";
        }
    }
};
