const app = {
    user: null,
    cart: [],          // [{ codigo, nombre, precio, cantidad, subtotal }]
    _searchDebounce: null,

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

        if (tab === 'ventas') {
            this.loadBestsellers();
        }
    },

    // ── Stock tab search (unchanged) ──────────────────────────────────────
    async searchStock() {
        const query = document.getElementById('stock-search').value.toLowerCase();
        const products = await LocalDB.getAllProducts();
        const filtered = products.filter(p =>
            p.nombre.toLowerCase().includes(query) ||
            p.codigo.toLowerCase().includes(query)
        );

        const listEl = document.getElementById('stock-list');
        listEl.innerHTML = filtered.map(p => `
            <div class="product-item">
                <span>${p.nombre}</span>
                <span>${p.precio}</span>
            </div>
        `).join('');
    },

    // ── Ventas: autocompletado con debounce ───────────────────────────────
    onVentasSearchInput() {
        clearTimeout(this._searchDebounce);
        this._searchDebounce = setTimeout(() => this._runVentasSearch(), 250);
    },

    async _runVentasSearch() {
        const query = document.getElementById('ventas-search').value.trim().toLowerCase();
        const dropdown = document.getElementById('ventas-autocomplete');

        if (query.length === 0) {
            dropdown.classList.add('hidden');
            dropdown.innerHTML = '';
            document.getElementById('ventas-results-section').classList.add('hidden');
            document.getElementById('bestsellers-section').classList.remove('hidden');
            return;
        }

        const products = await LocalDB.getAllProducts();
        const filtered = products
            .filter(p =>
                p.nombre.toLowerCase().includes(query) ||
                p.codigo.toLowerCase().includes(query)
            )
            .slice(0, 10);

        // Autocompletado dropdown
        if (filtered.length > 0) {
            dropdown.innerHTML = filtered.map(p => `
                <div class="autocomplete-item" onclick="app.selectVentasProduct('${p.codigo}')">
                    <span class="ac-codigo">${p.codigo}</span>
                    <span class="ac-nombre">${p.nombre}</span>
                    <span class="ac-precio">${parseFloat(p.precio).toFixed(2)}</span>
                </div>
            `).join('');
            dropdown.classList.remove('hidden');
        } else {
            dropdown.innerHTML = '<div class="autocomplete-empty">Sin resultados</div>';
            dropdown.classList.remove('hidden');
        }

        // Lista de resultados debajo
        this._renderVentasResults(filtered);
    },

    async searchVentas() {
        clearTimeout(this._searchDebounce);
        await this._runVentasSearch();
    },

    _renderVentasResults(products) {
        const section = document.getElementById('ventas-results-section');
        const listEl  = document.getElementById('ventas-stock-list');
        const bestsellersSection = document.getElementById('bestsellers-section');

        if (products.length === 0) {
            listEl.innerHTML = '<p class="empty-msg">No se encontraron productos.</p>';
        } else {
            listEl.innerHTML = products.map(p => `
                <div class="product-item" onclick="app.addToCart('${p.codigo}')">
                    <div class="product-info">
                        <span class="product-name">${p.nombre}</span>
                        <span class="product-code">${p.codigo}</span>
                    </div>
                    <div class="product-right">
                        <span class="product-price">${parseFloat(p.precio).toFixed(2)}</span>
                        <button class="btn-add-quick" onclick="event.stopPropagation(); app.addToCart('${p.codigo}')">＋</button>
                    </div>
                </div>
            `).join('');
        }

        section.classList.remove('hidden');
        bestsellersSection.classList.add('hidden');
    },

    selectVentasProduct(codigo) {
        // Cerrar dropdown y agregar al carrito
        document.getElementById('ventas-autocomplete').classList.add('hidden');
        document.getElementById('ventas-search').value = '';
        document.getElementById('ventas-results-section').classList.add('hidden');
        document.getElementById('bestsellers-section').classList.remove('hidden');
        this.addToCart(codigo);
    },

    // ── Bestsellers ───────────────────────────────────────────────────────
    async loadBestsellers() {
        const listEl = document.getElementById('bestsellers-list');
        listEl.innerHTML = '<p class="empty-msg loading-msg">Cargando...</p>';

        let bestsellers = [];

        // Intentar obtener desde API
        try {
            const token = sessionStorage.getItem('admin_token') || '';
            const res = await fetch('/api/sales/bestsellers', {
                headers: { 'Authorization': token }
            });
            if (res.ok) {
                const data = await res.json();
                bestsellers = (data.payload || data || []).slice(0, 10);
            }
        } catch (_) { /* offline: usar cola local */ }

        // Fallback: calcular desde sync_queue local
        if (bestsellers.length === 0) {
            const queue = await LocalDB.getQueue();
            const counts = {};
            queue.forEach(entry => {
                if (entry.action === 'venta.nueva' && entry.data && entry.data.items) {
                    entry.data.items.forEach(item => {
                        if (!counts[item.codigo]) {
                            counts[item.codigo] = { codigo: item.codigo, nombre: item.nombre || item.codigo, total: 0 };
                        }
                        counts[item.codigo].total += item.cantidad || 1;
                    });
                }
            });
            bestsellers = Object.values(counts)
                .sort((a, b) => b.total - a.total)
                .slice(0, 10);
        }

        if (bestsellers.length === 0) {
            // Sin historial: mostrar todos los productos (hasta 10)
            const products = await LocalDB.getAllProducts();
            listEl.innerHTML = products.slice(0, 10).map(p => `
                <div class="product-item" onclick="app.addToCart('${p.codigo}')">
                    <div class="product-info">
                        <span class="product-name">${p.nombre}</span>
                        <span class="product-code">${p.codigo}</span>
                    </div>
                    <div class="product-right">
                        <span class="product-price">${parseFloat(p.precio).toFixed(2)}</span>
                        <button class="btn-add-quick" onclick="event.stopPropagation(); app.addToCart('${p.codigo}')">＋</button>
                    </div>
                </div>
            `).join('') || '<p class="empty-msg">Sin productos en stock local.</p>';
            return;
        }

        // Enriquecer con datos de precio desde LocalDB si vienen de la cola local
        const allProducts = await LocalDB.getAllProducts();
        const prodMap = {};
        allProducts.forEach(p => { prodMap[p.codigo] = p; });

        listEl.innerHTML = bestsellers.map(b => {
            const prod = prodMap[b.codigo] || {};
            const nombre = b.nombre || prod.nombre || b.codigo;
            const precio = b.precio || prod.precio || 0;
            const vendidos = b.total || b.cantidad_vendida || '';
            return `
                <div class="product-item bestseller-item" onclick="app.addToCart('${b.codigo}')">
                    <div class="product-info">
                        <span class="product-name">${nombre}</span>
                        <span class="product-code">${b.codigo}${vendidos ? ` · ${vendidos} vendidos` : ''}</span>
                    </div>
                    <div class="product-right">
                        <span class="product-price">${parseFloat(precio).toFixed(2)}</span>
                        <button class="btn-add-quick" onclick="event.stopPropagation(); app.addToCart('${b.codigo}')">＋</button>
                    </div>
                </div>
            `;
        }).join('');
    },

    // ── Carrito ───────────────────────────────────────────────────────────
    async addToCart(codigo) {
        const products = await LocalDB.getAllProducts();
        const prod = products.find(p => p.codigo === codigo);
        if (!prod) return;

        const existing = this.cart.find(i => i.codigo === codigo);
        if (existing) {
            existing.cantidad += 1;
            existing.subtotal = parseFloat((existing.precio * existing.cantidad).toFixed(2));
        } else {
            this.cart.push({
                codigo:   prod.codigo,
                nombre:   prod.nombre,
                precio:   parseFloat(prod.precio),
                cantidad: 1,
                subtotal: parseFloat(prod.precio)
            });
        }

        this.updateCartUI();
    },

    incrementQuantity(codigo) {
        const item = this.cart.find(i => i.codigo === codigo);
        if (!item) return;
        item.cantidad += 1;
        item.subtotal = parseFloat((item.precio * item.cantidad).toFixed(2));
        this.updateCartUI();
    },

    decrementQuantity(codigo) {
        const item = this.cart.find(i => i.codigo === codigo);
        if (!item) return;
        item.cantidad -= 1;
        if (item.cantidad <= 0) {
            this.cart = this.cart.filter(i => i.codigo !== codigo);
        } else {
            item.subtotal = parseFloat((item.precio * item.cantidad).toFixed(2));
        }
        this.updateCartUI();
    },

    removeFromCart(codigo) {
        this.cart = this.cart.filter(i => i.codigo !== codigo);
        this.updateCartUI();
    },

    updateCartUI() {
        const listEl = document.getElementById('cart-list');

        if (this.cart.length === 0) {
            listEl.innerHTML = '<p class="empty-msg">El carrito está vacío.</p>';
            document.getElementById('cart-total').textContent = '0.00';
            return;
        }

        listEl.innerHTML = this.cart.map(item => `
            <div class="cart-item">
                <div class="cart-item-info">
                    <span class="cart-item-name">${item.nombre}</span>
                    <span class="cart-item-unit">${item.precio.toFixed(2)} c/u</span>
                </div>
                <div class="cart-item-controls">
                    <button class="qty-btn" onclick="app.decrementQuantity('${item.codigo}')">−</button>
                    <span class="qty-value">${item.cantidad}</span>
                    <button class="qty-btn" onclick="app.incrementQuantity('${item.codigo}')">＋</button>
                    <span class="cart-item-subtotal">${item.subtotal.toFixed(2)}</span>
                    <button class="btn-remove" onclick="app.removeFromCart('${item.codigo}')">✕</button>
                </div>
            </div>
        `).join('');

        const total = this.cart.reduce((sum, item) => sum + item.subtotal, 0);
        document.getElementById('cart-total').textContent = total.toFixed(2);
    },

    async processSale() {
        if (this.cart.length === 0) return;

        const saleData = {
            items: this.cart.map(i => ({
                codigo:   i.codigo,
                nombre:   i.nombre,
                precio:   i.precio,
                cantidad: i.cantidad,
                subtotal: i.subtotal
            })),
            total:     this.cart.reduce((sum, i) => sum + i.subtotal, 0),
            timestamp: Date.now(),
            user_id:   this.user.id
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
