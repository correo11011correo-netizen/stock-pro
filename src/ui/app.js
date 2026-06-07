const Logger = {
    log: (tag, msg) => console.log(`[${tag}] ${msg}`),
    warn: (tag, msg) => console.warn(`[${tag}] ${msg}`),
    error: (tag, msg) => console.error(`[${tag}] ${msg}`),
    success: (tag, msg) => console.log(`%c[${tag}] ${msg}`, 'color: #10b981; font-weight: bold;'),
};

const Toast = {
    show: (msg, type = 'info') => {
        console.log(`🔔 TOAST [${type}]: ${msg}`);
        alert(msg);
    },
    success: (msg) => Toast.show(msg, 'success'),
    error: (msg) => Toast.show(msg, 'error'),
    warning: (msg) => Toast.show(msg, 'warning'),
};

const app = {
    state: {
        user: null,
        token: null,
        role: null,
        business: null,
        lang: localStorage.getItem('lang') || 'es',
        theme: localStorage.getItem('theme') || 'dark',
        cart: [],
        selectedProduct: null,
        selectedQuantity: 1,
    },

    // ─────────────────────────────────────────────────────────────
    // INICIALIZACIÓN
    // ─────────────────────────────────────────────────────────────
    async init() {
        Logger.log('APP', '🚀 Inicializando aplicación...');
        this.checkSession();
        this.debouncedQuickSearch = this.debounce(() => this.performQuickSearch(), 400);
        this.renderCart();
    },

    checkSession() {
        const token = localStorage.getItem('token');
        if (token) {
            this.state.token = token;
            this.state.user = localStorage.getItem('user');
            this.state.role = localStorage.getItem('role');
            this.state.business = localStorage.getItem('business');
            this.updateAuthUI(true);
            this.switchView('view-stock');
        } else {
            this.state.token = null;
            this.updateAuthUI(false);
            this.switchView('view-login');
        }
    },

    updateAuthUI(isAuthenticated) {
        const nav = document.getElementById('bottom-nav');
        const submenu = document.getElementById('submenu-popup');
        if (nav) {
            isAuthenticated ? nav.classList.remove('hidden') : nav.classList.add('hidden');
        }
        if (submenu) {
            isAuthenticated ? submenu.classList.remove('hidden') : submenu.classList.add('hidden');
        }
        Logger.log('UI', `AuthUI updated: ${isAuthenticated ? 'Authenticated' : 'Guest'}`);
    },

    // ─────────────────────────────────────────────────────────────
    // AUTENTICACIÓN
    // ─────────────────────────────────────────────────────────────
    async login() {
        const user = document.getElementById('login-user').value.trim();
        const pass = document.getElementById('login-pass').value;

        if (!user || !pass) {
            Toast.error('Usuario y contraseña requeridos');
            return;
        }

        Logger.log('AUTH', `🔐 Intentando login: ${user}`);
        const res = await this.apiCall('auth.login', { user, pass });

        if (res.status === 'success') {
            this.state.user = user;
            this.state.token = res.token;
            this.state.role = res.role;
            this.state.business = res.business;

            localStorage.setItem('token', res.token);
            localStorage.setItem('user', user);
            localStorage.setItem('role', res.role);
            localStorage.setItem('business', res.business);

            this.updateAuthUI(true);
            Logger.success('AUTH', `✅ Login exitoso: ${user}`);
            Toast.success(`¡Bienvenido ${user}!`);
            this.switchView('view-stock');
        } else {
            Toast.error(res.message || 'Error en login');
        }
    },

    async registerOwner() {
        const business = document.getElementById('reg-business').value.trim();
        const user = document.getElementById('reg-user').value.trim();
        const pass = document.getElementById('reg-pass').value;

        if (!business || !user || !pass) {
            Toast.error('Todos los campos son requeridos');
            return;
        }

        Logger.log('AUTH', `📝 Registrando negocio: ${business}`);
        const res = await this.apiCall('auth.register_owner', { business_name: business, username: user, password: pass });

        if (res.status === 'success') {
            Toast.success('Cuenta creada exitosamente');
            this.switchView('view-login');
        } else {
            Toast.error(res.message || 'Error en registro');
        }
    },

    logout() {
        if (confirm('¿Cerrar sesión?')) {
            localStorage.clear();
            this.state = {
                user: null,
                token: null,
                role: null,
                business: null,
                lang: 'es',
                theme: 'dark',
                cart: [],
            };
            this.updateAuthUI(false);
            this.switchView('view-login');
            Logger.success('AUTH', '👋 Sesión cerrada');
        }
    },

    // ─────────────────────────────────────────────────────────────
    // API CALLS
    // ─────────────────────────────────────────────────────────────
    async apiCall(command, data = {}) {
        try {
            const payload = {
                command,
                token: this.state.token,
                ...data
            };

            const res = await fetch('/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const json = await res.json();
            return json.payload || json;
        } catch (err) {
            Logger.error('API', `❌ Error: ${err.message}`);
            return { status: 'error', message: err.message };
        }
    },

    // ─────────────────────────────────────────────────────────────
    // VISTA - NAVEGACIÓN
    // ─────────────────────────────────────────────────────────────
    switchView(viewId) {
        // Bloquear acceso a vistas protegidas si no hay token
        const publicViews = ['view-login', 'view-register'];
        if (!this.state.token && !publicViews.includes(viewId)) {
            Logger.warn('AUTH', `Acceso denegado a ${viewId}. Redirigiendo al login.`);
            viewId = 'view-login';
        }

        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(viewId)?.classList.add('active');

        document.querySelectorAll('.nav-item').forEach(item => {
            const view = item.getAttribute('data-view');
            if (view === viewId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        Logger.log('UI', `📱 Cambiando a vista: ${viewId}`);
    },

    toggleSubmenu() {
        const popup = document.getElementById('submenu-popup');
        popup?.classList.toggle('active');
    },

    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            modal.style.display = 'flex';
        }
    },

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            modal.style.display = 'none';
        }
    },

    // ─────────────────────────────────────────────────────────────
    // UTILITY FUNCTIONS
    // ─────────────────────────────────────────────────────────────
    debounce(fn, delay) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn.apply(this, args), delay);
        };
    },

    togglePassword(inputId) {
        const input = document.getElementById(inputId);
        if (input) {
            input.type = input.type === 'password' ? 'text' : 'password';
        }
    },

    // ─────────────────────────────────────────────────────────────
    // STOCK MANAGEMENT
    // ─────────────────────────────────────────────────────────────
    async loadStock() {
        Logger.log('STOCK', '📦 Cargando stock...');
        const searchTerm = document.getElementById('stock-search')?.value.trim() || '';
        const res = await this.apiCall('stock.list', { search: searchTerm });

        if (res.status === 'success' && res.data) {
            this.renderStockTable(res.data);
        }
    },

    renderStockTable(products) {
        const tbody = document.getElementById('stock-table-body');
        if (!tbody) return;

        tbody.innerHTML = products.map((p, idx) => `
            <tr>
                <td><strong>${p.codigo}</strong></td>
                <td>${p.nombre}</td>
                <td>${p.categoria || '-'}</td>
                <td>$${parseFloat(p.precio || 0).toFixed(2)}</td>
                <td>${p.cantidad}</td>
                <td>
                    <button class="btn btn-secondary" onclick="app.editProduct(${idx})">✏️ Editar</button>
                    <button class="btn btn-danger" onclick="app.deleteProduct(${p.codigo})">🗑️ Eliminar</button>
                </td>
            </tr>
        `).join('');
    },

    async saveProduct() {
        const code = document.getElementById('p-code').value.trim();
        const name = document.getElementById('p-name').value.trim();
        const price = parseFloat(document.getElementById('p-price').value) || 0;
        const qty = parseInt(document.getElementById('p-qty').value) || 0;
        const cat = document.getElementById('p-cat').value.trim();
        const isWeight = document.getElementById('p-weight').checked;

        if (!code || !name || price <= 0 || qty < 0) {
            Toast.error('Completa los campos correctamente');
            return;
        }

        Logger.log('STOCK', `💾 Guardando producto: ${code}`);
        const res = await this.apiCall('stock.add', {
            codigo: code,
            nombre: name,
            precio: price,
            cantidad: qty,
            categoria: cat,
            es_peso: isWeight ? 1 : 0
        });

        if (res.status === 'success') {
            Toast.success('Producto guardado');
            this.closeModal('modal-product');
            this.loadStock();
        } else {
            Toast.error(res.message || 'Error al guardar');
        }
    },

    editProduct(idx) {
        Logger.log('STOCK', '✏️ Editando producto');
    },

    async deleteProduct(productCode) {
        if (!confirm('¿Eliminar producto?')) return;
        Logger.log('STOCK', `🗑️ Eliminando: ${productCode}`);
    },

    // ─────────────────────────────────────────────────────────────
    // SALES MANAGEMENT - 🆕 AUTOCOMPLETADO + CARRITO MEJORADO
    // ─────────────────────────────────────────────────────────────
    async performQuickSearch() {
        Logger.log('SALES', '🔍 Ejecutando búsqueda rápida...');
        const searchInput = document.getElementById('sale-scan');
        const searchTerm = searchInput?.value.trim() || '';
        const dropdown = document.getElementById('quick-results');
        
        // 🆕 Buscar solo a partir de 2 caracteres
        if (!searchTerm || searchTerm.length < 2) {
            if (dropdown) dropdown.classList.remove('active');
            return;
        }
        
        const res = await this.apiCall('venta.search', { search: searchTerm, limit: 8 });
        Logger.log('SALES', 'Resultados búsqueda:', res);
        
        if (res.status === 'success' && res.data && res.data.length > 0) {
            this.renderSearchResults(res.data);
        } else {
            if (dropdown) {
                dropdown.innerHTML = '<div style="padding: 12px 16px; color: var(--text-muted); text-align: center;">No se encontraron productos</div>';
                dropdown.classList.add('active');
            }
        }
    },

    renderSearchResults(products) {
        const dropdown = document.getElementById('quick-results');
        if (!dropdown) {
            Logger.warn('SALES', '⚠️ Dropdown de búsqueda no encontrado');
            return;
        }
        
        dropdown.innerHTML = '';
        products.forEach((product) => {
            const item = document.createElement('div');
            item.className = 'search-result-item';
            item.innerHTML = `
                <div class="search-result-code">${product.codigo}</div>
                <div class="search-result-name">${product.nombre}</div>
                <div class="search-result-meta">💲 $${parseFloat(product.precio || 0).toFixed(2)} | 📦 ${product.cantidad || 0} en stock</div>
            `;
            // 🆕 Click agrega automáticamente con qty=1 (SIN modal)
            item.onclick = () => this.addProductToCart(product, 1);
            dropdown.appendChild(item);
        });
        
        dropdown.classList.add('active');
    },

    // 🆕 NUEVO: Agregar producto directo al carrito con cantidad
    addProductToCart(product, quantity = 1) {
        Logger.log('SALES', `✅ Agregando ${quantity}x ${product.nombre} al carrito`);
        
        // Verificar cantidad disponible
        if (quantity > product.cantidad) {
            Toast.warning(`Solo hay ${product.cantidad} productos disponibles`);
            return;
        }

        // Buscar si ya existe en carrito
        const existingItem = this.state.cart.find(item => item.codigo === product.codigo);
        
        if (existingItem) {
            // Si existe, incrementar cantidad
            const newQty = existingItem.cantidad + quantity;
            if (newQty <= product.cantidad) {
                existingItem.cantidad = newQty;
                existingItem.quantity = newQty;
            } else {
                Toast.warning(`Solo hay ${product.cantidad} productos disponibles`);
                return;
            }
        } else {
            // Si no existe, agregar nuevo
            const cartItem = {
                ...product,
                cantidad: quantity,
                quantity: quantity
            };
            this.state.cart.push(cartItem);
        }

        Toast.success(`${product.nombre} x${quantity} agregado al carrito`);
        
        // Limpiar búsqueda
        document.getElementById('sale-scan').value = '';
        document.getElementById('quick-results').classList.remove('active');
        
        this.renderCart();
    },

    renderCart() {
        const cartContainer = document.getElementById('cart-items');
        const cartTotal = document.getElementById('cart-total');
        
        if (!cartContainer) return;

        if (this.state.cart.length === 0) {
            cartContainer.innerHTML = '<p style="color: var(--text-muted); text-align: center;">Carrito vacío</p>';
            if (cartTotal) cartTotal.textContent = '$0.00';
            return;
        }

        let total = 0;
        cartContainer.innerHTML = this.state.cart.map((item, idx) => {
            const subtotal = item.precio * item.cantidad;
            total += subtotal;
            
            return `
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px;
                    background: rgba(255,255,255,0.05);
                    border-radius: 8px;
                    margin-bottom: 8px;
                    border-left: 3px solid var(--primary);
                ">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: var(--text);">${item.nombre}</div>
                        <div style="font-size: 0.85rem; color: var(--text-muted);">
                            💲${parseFloat(item.precio).toFixed(2)} × ${item.cantidad} = $${subtotal.toFixed(2)}
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <!-- 🆕 BOTÓN MENOS -->
                        <button class="btn btn-secondary" onclick="app.decreaseQuantity(${idx})" style="width: 36px; height: 36px; padding: 0; font-size: 1.2rem;">−</button>
                        
                        <!-- 🆕 CANTIDAD -->
                        <span style="min-width: 30px; text-align: center; font-weight: 600;">${item.cantidad}</span>
                        
                        <!-- 🆕 BOTÓN MÁS -->
                        <button class="btn btn-secondary" onclick="app.increaseQuantity(${idx})" style="width: 36px; height: 36px; padding: 0; font-size: 1.2rem;">+</button>
                        
                        <!-- 🆕 BOTÓN ELIMINAR -->
                        <button class="btn btn-danger" onclick="app.removeFromCart(${idx})" style="width: 36px; height: 36px; padding: 0; font-size: 1.2rem;">🗑️</button>
                    </div>
                </div>
            `;
        }).join('');

        if (cartTotal) {
            cartTotal.textContent = `$${total.toFixed(2)}`;
        }
    },

    // 🆕 INCREMENTAR CANTIDAD
    increaseQuantity(idx) {
        const item = this.state.cart[idx];
        if (!item) return;
        
        if (item.cantidad < item.cantidad_disponible) {
            item.cantidad++;
            item.quantity++;
            Logger.log('SALES', `➕ Incrementado: ${item.nombre} x${item.cantidad}`);
            this.renderCart();
        } else {
            Toast.warning(`Stock máximo: ${item.cantidad_disponible}`);
        }
    },

    // 🆕 DECREMENTAR CANTIDAD
    decreaseQuantity(idx) {
        const item = this.state.cart[idx];
        if (!item) return;
        
        if (item.cantidad > 1) {
            item.cantidad--;
            item.quantity--;
            Logger.log('SALES', `➖ Decrementado: ${item.nombre} x${item.cantidad}`);
            this.renderCart();
        } else {
            this.removeFromCart(idx);
        }
    },

    // 🆕 ELIMINAR DEL CARRITO
    removeFromCart(idx) {
        const item = this.state.cart[idx];
        Logger.log('SALES', `🗑️ Removido del carrito: ${item.nombre}`);
        this.state.cart.splice(idx, 1);
        Toast.success(`${item.nombre} eliminado del carrito`);
        this.renderCart();
    },

    openCheckout() {
        if (this.state.cart.length === 0) {
            Toast.error('El carrito está vacío');
            return;
        }
        this.showModal('modal-checkout');
    },

    async confirmSale() {
        if (this.state.cart.length === 0) {
            Toast.error('Carrito vacío');
            return;
        }

        Logger.log('SALES', '💰 Procesando venta...');
        const items = this.state.cart.map(item => ({
            codigo: item.codigo,
            cantidad: item.cantidad,
            precio: item.precio
        }));

        const res = await this.apiCall('venta.cobrar', {
            items: items,
            metodo: 'Efectivo'
        });

        if (res.status === 'success') {
            Toast.success(`✅ Venta #${res.venta_id} completada`);
            this.state.cart = [];
            this.renderCart();
            this.closeModal('modal-checkout');
            document.getElementById('sale-scan').value = '';
        } else {
            Toast.error(res.message || 'Error al procesar venta');
        }
    },

    handleSaleSearchInput() {
        Logger.log('SALES', '⌨️ Input en búsqueda de ventas detectado');
        this.debouncedQuickSearch();
    },

    // ─────────────────────────────────────────────────────────────
    // IMPORT MANAGEMENT - 🆕 SISTEMA ASISTIDO
    // ─────────────────────────────────────────────────────────────
    async handleFileUpload(input) {
        const file = input.files[0];
        if (!file) return;

        Logger.log('IMPORT', `📁 Subiendo archivo: ${file.name}`);
        const logDiv = document.getElementById('import-log');
        const btnPreview = document.getElementById('btn-run-import');
        const statusDiv = document.getElementById('import-status');
        
        logDiv.innerHTML = `Subiendo archivo ${file.name} al servidor...`;
        statusDiv.textContent = 'Subiendo...';
        statusDiv.style.color = 'var(--warning)';
        btnPreview.disabled = true;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const json = await res.json();

            if (json.status === 'success') {
                this.state.currentImportFile = json.path;
                Logger.success('IMPORT', `Archivo subido exitosamente: ${json.path}`);
                logDiv.innerHTML = `✅ Archivo subido: ${file.name}<br>Listo para examinar.`;
                statusDiv.textContent = 'Archivo cargado';
                statusDiv.style.color = 'var(--primary)';
                btnPreview.disabled = false;
            } else {
                throw new Error(json.message || 'Error desconocido al subir archivo');
            }
        } catch (err) {
            Logger.error('IMPORT', `❌ Error en upload: ${err.message}`);
            logDiv.innerHTML = `❌ Error al subir archivo: ${err.message}`;
            statusDiv.textContent = 'Error de subida';
            statusDiv.style.color = 'var(--error)';
            Toast.error(`Error al subir archivo: ${err.message}`);
        }
    },

    async runImportPreview() {
        const filePath = this.state.currentImportFile;
        const mappingId = document.getElementById('import-mapping')?.value.trim();
        
        if (!filePath) {
            Toast.error('Primero selecciona un archivo');
            return;
        }

        Logger.log('IMPORT', `🔍 Solicitando previsualización: ${filePath}`);
        const logDiv = document.getElementById('import-log');
        logDiv.innerHTML += `<br>Solicitando previsualización...`;
        
        const res = await this.apiCall('stock.import.preview', { 
            file_path: filePath,
            mapping_id: mappingId || null
        });

        if (res.status === 'needs_mapping') {
            Logger.warn('IMPORT', 'Mapeo requerido por el usuario');
            logDiv.innerHTML += `<br>⚠️ Mapeo manual requerido.`;
            this.renderMappingTable(res.headers);
        } else if (res.status === 'success') {
            Logger.success('IMPORT', 'Previsualización generada');
            logDiv.innerHTML += `<br>✅ Datos mapeados correctamente.`;
            this.renderImportPreview(res.data, res.mapping_used);
        } else {
            Logger.error('IMPORT', `Error: ${res.message}`);
            logDiv.innerHTML += `<br>❌ Error: ${res.message}`;
            Toast.error(res.message);
        }
    },

    renderMappingTable(headers) {
        const container = document.getElementById('import-mapping-container');
        const tbody = document.getElementById('mapping-table-body');
        const previewContainer = document.getElementById('import-preview-container');
        
        container.classList.remove('hidden');
        previewContainer.classList.add('hidden');
        tbody.innerHTML = '';

        const systemFields = [
            { id: 'codigo', label: 'Código / SKU' },
            { id: 'nombre', label: 'Nombre / Descripción' },
            { id: 'precio', label: 'Precio de Venta' },
            { id: 'cantidad', label: 'Cantidad / Stock' },
            { id: 'categoria', label: 'Categoría' },
            { id: 'es_peso', label: '¿Es pesado? (Kg)' },
        ];

        headers.forEach(header => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${header}</strong></td>
                <td>
                    <select class="input mapping-select" data-column="${header}">
                        <option value="">-- Ignorar --</option>
                        ${systemFields.map(f => `<option value="${f.id}">${f.label}</option>`).join('')}
                    </select>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },

    async saveImportProfile() {
        const profileName = document.getElementById('import-profile-name')?.value.trim();
        if (!profileName) {
            Toast.error('Por favor, asigna un nombre al perfil');
            return;
        }

        const mapping = this.getCurrentMapping();
        if (Object.keys(mapping).length === 0) {
            Toast.error('No hay mapeo definido para guardar');
            return;
        }

        Logger.log('IMPORT', `💾 Guardando perfil: ${profileName}`);
        const res = await this.apiCall('stock.import.save_profile', {
            mapping_id: profileName,
            mapping: mapping
        });

        if (res.status === 'success') {
            Toast.success(`Perfil '${profileName}' guardado`);
        } else {
            Toast.error(res.message);
        }
    },

    getCurrentMapping() {
        const mapping = {};
        document.querySelectorAll('.mapping-select').forEach(select => {
            if (select.value) {
                mapping[select.value] = select.getAttribute('data-column');
            }
        });
        return mapping;
    },

    renderImportPreview(data, mappingUsed) {
        const container = document.getElementById('import-preview-container');
        const mappingContainer = document.getElementById('import-mapping-container');
        const tbody = document.getElementById('import-preview-body');
        
        container.classList.remove('hidden');
        mappingContainer.classList.add('hidden');
        tbody.innerHTML = '';

        data.forEach(item => {
            const mapped = item.mapped;
            const hasError = item.error;
            
            const tr = document.createElement('tr');
            if (hasError) tr.style.color = 'var(--error)';
            
            tr.innerHTML = `
                <td>${item.row}</td>
                <td><input type="text" class="input edit-field" data-row="${item.row}" data-field="codigo" value="${mapped.codigo || ''}"></td>
                <td><input type="text" class="input edit-field" data-row="${item.row}" data-field="nombre" value="${mapped.nombre || ''}"></td>
                <td><input type="number" class="input edit-field" data-row="${item.row}" data-field="precio" value="${mapped.precio || 0}"></td>
                <td><input type="number" class="input edit-field" data-row="${item.row}" data-field="cantidad" value="${mapped.cantidad || 0}"></td>
                <td><input type="text" class="input edit-field" data-row="${item.row}" data-field="categoria" value="${mapped.categoria || ''}"></td>
                <td><input type="checkbox" class="edit-field" data-row="${item.row}" data-field="es_peso" ${mapped.es_peso ? 'checked' : ''}></td>
            `;
            tbody.appendChild(tr);
        });
    },

    async commitImport() {
        const rows = [];
        const tbody = document.getElementById('import-preview-body');
        
        // Recolectar datos editados de la tabla
        const rowElements = tbody.querySelectorAll('tr');
        rowElements.forEach(tr => {
            const rowIdx = tr.querySelector('[data-row]').getAttribute('data-row');
            const mapped = {};
            tr.querySelectorAll('.edit-field').forEach(field => {
                const f = field.getAttribute('data-field');
                const val = field.type === 'checkbox' ? field.checked : field.value;
                mapped[f] = val;
            });
            rows.push({ row: rowIdx, mapped: mapped });
        });

        Logger.log('IMPORT', `💾 Confirmando importación de ${rows.length} items`);
        const res = await this.apiCall('stock.import.commit', { data_list: rows });

        if (res.status === 'success') {
            Toast.success(res.message);
            this.cancelImport();
            this.loadStock();
        } else {
            Toast.error(res.message);
        }
    },

    cancelImport() {
        document.getElementById('import-preview-container').classList.add('hidden');
        document.getElementById('import-mapping-container').classList.add('hidden');
        document.getElementById('import-file-input').value = '';
        document.getElementById('btn-run-import').disabled = true;
        document.getElementById('import-status').textContent = '';
        document.getElementById('import-log').innerHTML = 'Esperando selección de archivo...';
        this.state.currentImportFile = null;
        Logger.log('IMPORT', 'Importación cancelada');
    },

    // ─────────────────────────────────────────────────────────────
    // ALIAS MANAGEMENT
    // ─────────────────────────────────────────────────────────────
    async addAlias() {
        const name = document.getElementById('alias-name')?.value.trim();
        const limit = parseFloat(document.getElementById('alias-limit')?.value) || 0;

        if (!name || limit < 0) {
            Toast.error('Datos inválidos');
            return;
        }

        Logger.log('ALIAS', `➕ Agregando alias: ${name}`);
        const res = await this.apiCall('alias.add', { nombre: name, limite: limit });

        if (res.status === 'success') {
            Toast.success('Alias creado');
            this.loadAliases();
        }
    },

    async loadAliases() {
        Logger.log('ALIAS', '📋 Cargando alias...');
    },

    async deleteAlias(aliasId) {
        Logger.log('ALIAS', `🗑️ Eliminando alias: ${aliasId}`);
    },

    // ─────────────────────────────────────────────────────────────
    // SUBSCRIPTION & REPORTS
    // ─────────────────────────────────────────────────────────────
    async loadSubscription() {
        Logger.log('SUBSCRIPTION', '💳 Cargando suscripción...');
    },

    async loadReports() {
        Logger.log('REPORTS', '📊 Cargando reportes...');
    },

    async exportCSV() {
        Logger.log('EXPORT', '📄 Exportando a CSV...');
    },

    // ─────────────────────────────────────────────────────────────
    // CASH MANAGEMENT
    // ─────────────────────────────────────────────────────────────
    async openCash() {
        Logger.log('CASH', '💰 Abriendo caja...');
        const amount = parseFloat(document.getElementById('cash-amount')?.value) || 0;
        if (amount <= 0) {
            Toast.error('Monto inválido');
            return;
        }
        const res = await this.apiCall('caja.abrir', { monto_inicial: amount });
        if (res.status === 'success') {
            Toast.success('Caja abierta');
        }
    },

    async closeCash() {
        Logger.log('CASH', '🔒 Cerrando caja...');
        const amount = parseFloat(document.getElementById('cash-amount')?.value) || 0;
        if (amount <= 0) {
            Toast.error('Monto inválido');
            return;
        }
        const res = await this.apiCall('caja.cerrar', { monto_final: amount });
        if (res.status === 'success') {
            Toast.success('Caja cerrada');
        }
    },

    // ─────────────────────────────────────────────────────────────
    // SETTINGS
    // ─────────────────────────────────────────────────────────────
    applyTranslations() {
        Logger.log('TRANSLATIONS', `Aplicando traducciones: ${this.state.lang}`);
    },

    setTheme(theme) {
        Logger.log('THEME', `Cambiando tema a: ${theme}`);
        this.state.theme = theme;
        localStorage.setItem('theme', theme);
    },

    setLang(lang) {
        Logger.log('LANG', `Cambiando idioma a: ${lang}`);
        this.state.lang = lang;
        localStorage.setItem('lang', lang);
    },

    // ─────────────────────────────────────────────────────────────
    // PERSONNEL MANAGEMENT
    // ─────────────────────────────────────────────────────────────
    async inviteEmployee() {
        Logger.log('PERSONNEL', '👥 Invitando empleado...');
    },
};

// Inicializar app cuando cargue el DOM
document.addEventListener('DOMContentLoaded', () => app.init());
