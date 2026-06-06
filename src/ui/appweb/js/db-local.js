const LocalDB = {
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open("StockProLocal", 2); // Version 2
            request.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains("products")) {
                    db.createObjectStore("products", { keyPath: "codigo" });
                }
                if (!db.objectStoreNames.contains("sync_queue")) {
                    db.createObjectStore("sync_queue", { autoIncrement: true });
                }
                if (!db.objectStoreNames.contains("session")) {
                    db.createObjectStore("session");
                }
            };
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject("Error abriendo IndexedDB");
        });
    },

    async saveProduct(product) {
        const db = await this.init();
        const tx = db.transaction("products", "readwrite");
        tx.objectStore("products").put(product);
    },

    async getAllProducts() {
        const db = await this.init();
        return new Promise((resolve) => {
            const tx = db.transaction("products", "readonly");
            const request = tx.objectStore("products").getAll();
            request.onsuccess = () => resolve(request.result);
        });
    },

    async addToQueue(action, data) {
        const db = await this.init();
        const tx = db.transaction("sync_queue", "readwrite");
        tx.objectStore("sync_queue").add({ 
            action, 
            data, 
            timestamp: Date.now(),
            synced: false 
        });
    },

    async getQueue() {
        const db = await this.init();
        return new Promise((resolve) => {
            const tx = db.transaction("sync_queue", "readonly");
            const request = tx.objectStore("sync_queue").getAll();
            request.onsuccess = () => resolve(request.result);
        });
    },

    async clearQueue() {
        const db = await this.init();
        const tx = db.transaction("sync_queue", "readwrite");
        tx.objectStore("sync_queue").clear();
    },

    async setSession(data) {
        const db = await this.init();
        const tx = db.transaction("session", "readwrite");
        tx.objectStore("session").put(data, "current_user");
    },

    async getSession() {
        const db = await this.init();
        return new Promise((resolve) => {
            const tx = db.transaction("session", "readonly");
            const request = tx.objectStore("session").get("current_user");
            request.onsuccess = () => resolve(request.result);
        });
    }
};
