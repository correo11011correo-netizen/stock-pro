const app = {
    user: null,
    cart: [],

    async handleLogin() {
        const u = document.getElementById('login-user').value;
        const p = document.getElementById('login-pass').value;
        
        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    command: 'auth.login', 
                    username: u, 
                    password: p 
                })
            });
            const data = await res.json();

            if (data.payload && data.payload.status === 'success') {
                this.user = data.payload.user;
                sessionStorage.setItem('admin_token', data.payload.token);
                await LocalDB.setSession(this.user);
                this.setupUI();
                this.showScreen('screen-main');
                await SyncEngine.sync(); 
            } else {
                const msg = data.payload ? data.payload.message : (data.message || "Error de autenticación");
                document.getElementById('login-error').textContent = msg;
            }
        } catch (e) {

            document.getElementById('login-error').textContent = "Error de conexión. Inicie sesión online primero.";
        }
    },

    setupUI() {
        document.getElementById('user-role-badge').textContent = this.user.role;
        document.getElementById('user-name-display').textContent = this.user.username;
        
        // Lógica de RAM: Solo habilitar Admin si es Dueño o Admin
        if (this.user.role === 'OWNER' || this.user.role === 'admin' || this.user.role === 'MASTER') {
            document.getElementById('btn-admin-tab').classList.remove('hidden');
        }
    },

    showScreen(id) {
        document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
        document.getElementById(id).classList.remove('hidden');
    },

    showTab(tab) {
        document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(`tab-${tab}`).classList.remove('hidden');
        event.currentTarget.classList.add('active');
    },

    async searchStock() {
        const query = document.getElementById('stock-search').value.toLowerCase();
        const products = await LocalDB.getAllProducts();
        const filtered = products.filter(p => 
            p.nombre.toLowerCase().includes(query) || 
            p.codigo.toLowerCase().includes(query)
        );
        
        const listEl = document.getElementById('stock-list');
        listEl.innerHTML = filtered.map(p => `
            <div class="product-item" onclick="app.addToCart('${p.codigo}')">
                <span>${p.nombre}</span>
                <span>$${p.precio}</span>
            </div>
        `).join('');
    },

    async addToCart(codigo) {
        const products = await LocalDB.getAllProducts();
        const prod = products.find(p => p.codigo === codigo);
        if (prod) {
            this.cart.push(prod);
            this.updateCartUI();
        }
    },

    updateCartUI() {
        const listEl = document.getElementById('cart-list');
        listEl.innerHTML = this.cart.map((item, idx) => `
            <div class="cart-item product-item">
                <span>${item.nombre}</span>
                <div style="display:flex; gap:1rem; align-items:center;">
                    <span>$${item.precio}</span>
                    <button onclick="app.removeFromCart(${idx})" style="background:none; border:none; color:#ef4444; cursor:pointer;">✕</button>
                </div>
            </div>
        `).join('');
        
        const total = this.cart.reduce((sum, item) => sum + parseFloat(item.precio), 0);
        document.getElementById('cart-total').textContent = total.toFixed(2);
    },

    removeFromCart(idx) {
        this.cart.splice(idx, 1);
        this.updateCartUI();
    },

    async processSale() {
        if (this.cart.length === 0) return;

        const saleData = {
            items: this.cart.map(i => ({ codigo: i.codigo, cantidad: 1, subtotal: i.precio })),
            timestamp: Date.now(),
            user_id: this.user.id
        };

        try {
            // Intento de envío inmediato
            const res = await fetch('/api/sync/push', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': sessionStorage.getItem('admin_token') || ''
                },
                body: JSON.stringify({ events: [{ action: 'venta.nueva', data: saleData }] })
            });

            if (res.ok) {
                alert("Venta sincronizada en tiempo real");
            } else {
                throw new Error("Servidor no disponible");
            }
        } catch (e) {
            // Guardado local si falla la conexión
            await LocalDB.addToQueue('venta.nueva', saleData);
            alert("Modo Offline: Venta guardada. Se sincronizará al recuperar internet.");
        }

        this.cart = [];
        this.updateCartUI();
    },

    async syncNow() {
        await SyncEngine.sync();
    },

    logout() {
        sessionStorage.clear();
        location.reload();
    },

    adminAction(action) {
        alert(`Abriendo módulo de ${action}... (Requiere conexión online)`);
        // Aquí se redirigiría al panel web completo o se llamaría a la API
    }
};
