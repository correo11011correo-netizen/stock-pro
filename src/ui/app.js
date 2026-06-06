/**
 * Stock & Scan Pro - Frontend Application
 * Maneja autenticación, multi-tenancy y comandos
 * ✅ VERSIÓN CON LOGS EXHAUSTIVOS PARA DEBUGGING
 * ✨ NUEVA: Autocompletado inteligente en búsqueda de ventas
 */

const API_BASE = '';

// 🔍 LOG HELPER - Centralizado para debugging
const Logger = {
    log(section, message, data = null) {
        const timestamp = new Date().toLocaleTimeString('es-ES', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
        const prefix = `[${timestamp}] 📱 Frontend [${section}]`;
        
        if (data) {
            console.log(`${prefix}: ${message}`, data);
        } else {
            console.log(`${prefix}: ${message}`);
        }
    },
    
    error(section, message, error = null) {
        const timestamp = new Date().toLocaleTimeString('es-ES', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
        const prefix = `[${timestamp}] ❌ Frontend [${section}]`;
        
        if (error) {
            console.error(`${prefix}: ${message}`, error);
        } else {
            console.error(`${prefix}: ${message}`);
        }
    },
    
    success(section, message, data = null) {
        const timestamp = new Date().toLocaleTimeString('es-ES', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
        const prefix = `[${timestamp}] ✅ Frontend [${section}]`;
        
        if (data) {
            console.log(`%c${prefix}: ${message}`, 'color: #10b981; font-weight: bold;', data);
        } else {
            console.log(`%c${prefix}: ${message}`, 'color: #10b981; font-weight: bold;');
        }
    },
    
    warn(section, message, data = null) {
        const timestamp = new Date().toLocaleTimeString('es-ES', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
        const prefix = `[${timestamp}] ⚠️ Frontend [${section}]`;
        
        if (data) {
            console.warn(`${prefix}: ${message}`, data);
        } else {
            console.warn(`${prefix}: ${message}`);
        }
    }
};

// Función de utilidad para evitar llamadas excesivas a la API
function debounce(func, wait = 300) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Toast Notification System
const Toast = {
    show(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toast-container') || this.createContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${this.getIcon(type)}</span>
                <span class="toast-message">${message}</span>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Auto remove
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },
    
    createContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        `;
        document.body.appendChild(container);
        return container;
    },
    
    getIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    },
    
    success(msg, duration) { this.show(msg, 'success', duration); },
    error(msg, duration) { this.show(msg, 'error', duration); },
    warning(msg, duration) { this.show(msg, 'warning', duration); },
    info(msg, duration) { this.show(msg, 'info', duration); }
};

// Agregar estilos de toast al documento
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    .toast {
        background: rgba(15, 23, 42, 0.95);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 12px;
        padding: 12px 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 300px;
        max-width: 400px;
        pointer-events: auto;
        opacity: 0;
        transform: translateX(400px);
        transition: all 0.3s ease;
        font-size: 0.9rem;
        color: #f1f5f9;
    }
    
    .toast.show {
        opacity: 1;
        transform: translateX(0);
    }
    
    .toast-content {
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
    }
    
    .toast-icon {
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    
    .toast-message {
        flex: 1;
        word-break: break-word;
    }
    
    .toast-success {
        border-color: rgba(16, 185, 129, 0.3);
        background: rgba(15, 23, 42, 0.95);
    }
    
    .toast-error {
        border-color: rgba(239, 68, 68, 0.3);
        background: rgba(15, 23, 42, 0.95);
    }
    
    .toast-warning {
        border-color: rgba(245, 158, 11, 0.3);
        background: rgba(15, 23, 42, 0.95);
    }
    
    .toast-info {
        border-color: rgba(99, 102, 241, 0.3);
        background: rgba(15, 23, 42, 0.95);
    }
    
    @media (max-width: 768px) {
        .toast {
            min-width: 280px;
            max-width: 90vw;
        }
    }
    
    /* 🆕 ESTILOS PARA AUTOCOMPLETADO */
    .search-results-dropdown {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: rgba(15, 23, 42, 0.95);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-top: none;
        border-radius: 0 0 12px 12px;
        max-height: 300px;
        overflow-y: auto;
        z-index: 1000;
        display: none;
    }
    
    .search-results-dropdown.active {
        display: block;
    }
    
    .search-result-item {
        padding: 12px 16px;
        cursor: pointer;
        border-bottom: 1px solid rgba(99, 102, 241, 0.1);
        transition: background 0.2s;
    }
    
    .search-result-item:hover {
        background: rgba(99, 102, 241, 0.1);
    }
    
    .search-result-item:last-child {
        border-bottom: none;
    }
    
    .search-result-code {
        font-weight: 600;
        color: var(--primary);
        font-size: 0.9rem;
    }
    
    .search-result-name {
        color: var(--text);
        margin-top: 2px;
    }
    
    .search-result-meta {
        font-size: 0.85rem;
        color: var(--text-muted);
        margin-top: 4px;
    }
`;
document.head.appendChild(toastStyles);

const app = {
    state: {
        currentView: localStorage.getItem('current_view') || 'view-login',
        token: localStorage.getItem('session_token'),
        user: JSON.parse(localStorage.getItem('user_data') || '{}'),
        role: localStorage.getItem('user_role') || 'empleado',
        isPro: false,
        theme: localStorage.getItem('theme') || 'dark',
        lang: localStorage.getItem('lang') || 'es',
        cart: [],
        translations: {},
        selectedProduct: null, // 🆕 Producto seleccionado en búsqueda
        selectedQuantity: 1    // 🆕 Cantidad seleccionada
    },

    async init() {
        Logger.log('INIT', '🚀 Stock Pro: Iniciando aplicación...');
        try {
            await this.loadConfig();
            await this.loadTranslations();
            this.applyTheme();
            this.applyTranslations();
            this.setupDebouncedHandlers();
            
            if (this.state.token && this.state.user.id) {
                Logger.log('INIT', '🔍 Validando sesión activa con el servidor...');
                const validation = await this.apiCall('auth.validate_session', { token: this.state.token });
                
                if (validation && validation.status === 'success') {
                    Logger.success('INIT', '✅ Sesión validada. Accediendo al panel.', this.state.user);
                    this.setupAuthenticatedUI();
                    this.loadStock();
                    const targetView = (this.state.currentView && this.state.currentView !== 'view-login') 
                        ? this.state.currentView 
                        : 'view-stock';
                    this.switchView(targetView);
                } else {
                    Logger.warn('INIT', '⚠️ Sesión inválida o expirada. Redirigiendo al Login.');
                    this.logout();
                }
            } else {
                Logger.log('INIT', '🔑 No hay sesión activa, redirigiendo al Login.');
                this.switchView('view-login');
            }
        } catch (e) {
            Logger.error('INIT', '❌ Error crítico durante la inicialización:', e);
            Toast.error("Error al cargar la aplicación. Por favor, recarga la página.");
            this.switchView('view-login');
        }
    },

    setupAuthenticatedUI() {
        Logger.log('AUTH', 'Configurando UI autenticada para rol:', this.state.role);
        if (this.state.role === 'OWNER') {
            const navPersonnel = document.getElementById('nav-personnel');
            if (navPersonnel) navPersonnel.classList.remove('hidden');
        }
        this.updateGlobalUI(false);
    },

    updateGlobalUI(isHidden) {
        const nav = document.getElementById('bottom-nav');
        if (!nav) return;
        
        Logger.log('UI', `Actualizando visibilidad del nav: ${isHidden ? 'HIDDEN' : 'VISIBLE'}`);
        if (isHidden) {
            nav.classList.add('hidden');
            nav.style.display = 'none';
        } else {
            nav.classList.remove('hidden');
            nav.style.display = 'flex';
        }
    },

    switchView(viewId) {
        Logger.log('NAVIGATION', `Cambiando a vista: ${viewId}`);
        this.state.currentView = viewId;
        localStorage.setItem('current_view', viewId);
        
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        const view = document.getElementById(viewId);
        if (view) view.classList.add('active');
        
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.getAttribute('data-view') === viewId);
        });

        const submenu = document.getElementById('submenu-popup');
        if (submenu) submenu.classList.remove('active');

        if (viewId === 'view-personnel') this.loadPersonnel();
        if (viewId === 'view-subscription') this.loadSubscription();
        if (viewId === 'view-alias') this.loadAliases();
        if (viewId === 'view-cash') this.loadCashStatus();
        if (viewId === 'view-reports') this.loadReports();

        const isAuthView = (viewId === 'view-login' || viewId === 'view-register');
        const nav = document.getElementById('bottom-nav');
        if (nav) {
            if (isAuthView) {
                nav.classList.add('hidden');
                nav.style.display = 'none';
            } else {
                nav.classList.remove('hidden');
                nav.style.display = 'flex';
            }
        }
    },

    toggleSubmenu() {
        Logger.log('SUBMENU', 'Toggle submenu');
        const submenu = document.getElementById('submenu-popup');
        if (submenu) {
            submenu.classList.toggle('active');
        }
    },

    async apiCall(command, params = {}) {
        Logger.log('API', `Llamando comando: ${command}`, params);
        
        try {
            const headers = { 'Content-Type': 'application/json' };
            if (this.state.token) {
                headers['Authorization'] = this.state.token;
            }

            const payload = {
                command,
                params,
                role: this.state.role,
                is_pro: this.state.isPro
            };
            
            Logger.log('API', `📤 Enviando payload al servidor`, payload);

            const response = await fetch(`${API_BASE}/`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(payload)
            });
            
            Logger.log('API', `📥 Response status: ${response.status}`);
            
            if (response.status === 401) {
                Logger.warn('API', '⚠️ Sesión expirada (401). Limpiando localStorage y redirigiendo.');
                Toast.error("Tu sesión ha expirado. Por favor, inicia sesión nuevamente.");
                localStorage.clear();
                this.state.token = null;
                this.state.user = {};
                this.state.role = 'empleado';
                this.switchView('view-login');
                return { status: "error", message: "Sesión expirada" };
            }

            if (!response.ok) {
                Logger.error('API', `Server error ${response.status}`);
                throw new Error(`Server responded with ${response.status}`);
            }

            const res = await response.json();
            Logger.success('API', `✅ Response recibido de ${command}`, res.payload || res);
            return res.payload || res;
        } catch (e) {
            Logger.error('API', `❌ Error en apiCall para ${command}:`, e);
            return { status: "error", message: `Error de conexión: ${e.message}` };
        }
    },

    // --- AUTH METHODS ---

    async login() {
        Logger.log('LOGIN', '🔐 Iniciando login...');
        const user = document.getElementById('login-user').value;
        const pass = document.getElementById('login-pass').value;
        
        Logger.log('LOGIN', `Usuario: ${user}, Password recibida: ${!!pass}`);
        
        if (!user || !pass) {
            Logger.warn('LOGIN', '⚠️ Credenciales incompletas');
            Toast.warning('Completa usuario y contraseña');
            return;
        }
        
        const res = await this.apiCall('auth.login', { username: user, password: pass });
        Logger.log('LOGIN', 'Respuesta del servidor:', res);
        
        if (res.status === 'success') {
            Logger.success('LOGIN', `✅ Login exitoso para ${user}`);
            this.state.token = res.token;
            this.state.user = res.user;
            this.state.role = res.user.role;
            
            localStorage.setItem('session_token', res.token);
            localStorage.setItem('user_data', JSON.stringify(res.user));
            localStorage.setItem('user_role', res.user.role);
            
            Toast.success(`¡Bienvenido ${user}!`);
            this.setupAuthenticatedUI();
            this.loadStock();
            this.switchView('view-stock');
        } else {
            Logger.error('LOGIN', `❌ Login fallido: ${res.message}`);
            Toast.error(res.message || 'Login fallido');
        }
    },

    async registerOwner() {
        Logger.log('REGISTER', '📝 Iniciando registro de propietario...');
        const biz = document.getElementById('reg-business').value;
        const user = document.getElementById('reg-user').value;
        const pass = document.getElementById('reg-pass').value;
        
        if (!biz || !user || !pass) {
            Logger.warn('REGISTER', '⚠️ Campos incompletos');
            Toast.warning('Completa todos los campos');
            return;
        }
        
        Logger.log('REGISTER', `Datos: business=${biz}, user=${user}`);
        const res = await this.apiCall('auth.register_owner', { 
            business_name: biz, 
            username: user, 
            password: pass 
        });
        
        if (res.status === 'success') {
            Logger.success('REGISTER', `✅ Negocio registrado: ${biz}`);
            Toast.success("Negocio registrado. Inicia sesión");
            this.switchView('view-login');
        } else {
            Logger.error('REGISTER', `❌ Registro fallido: ${res.message}`);
            Toast.error(res.message || 'Registro fallido');
        }
    },

    async logout() {
        Logger.log('LOGOUT', '🚪 Cerrando sesión...');
        localStorage.clear();
        this.state.token = null;
        this.state.user = {};
        this.state.role = 'empleado';
        Toast.info('Sesión cerrada');
        this.switchView('view-login');
    },

    togglePassword(inputId) {
        const input = document.getElementById(inputId);
        if (input) {
            input.type = input.type === 'password' ? 'text' : 'password';
        }
    },

    // --- PERSONNEL MANAGEMENT ---

    async inviteEmployee() {
        Logger.log('PERSONNEL', '➕ Invitando nuevo empleado...');
        const user = document.getElementById('emp-user')?.value.trim();
        const pass = document.getElementById('emp-pass')?.value;
        
        Logger.log('PERSONNEL', `Usuario: ${user}, Password: ${!!pass}`);
        
        if (!user || !pass) {
            Logger.warn('PERSONNEL', '⚠️ Datos incompletos');
            Toast.warning("Ingrese usuario y contraseña");
            return;
        }

        const res = await this.apiCall('user.invite_employee', { 
            username: user, 
            password: pass, 
            tenant_id: this.state.user.tenant_id 
        });
        
        Logger.log('PERSONNEL', 'Respuesta:', res);
        
        if (res.status === 'success') {
            Logger.success('PERSONNEL', `✅ Empleado agregado: ${user}`);
            Toast.success("Empleado agregado");
            document.getElementById('emp-user').value = '';
            document.getElementById('emp-pass').value = '';
            this.loadPersonnel();
        } else {
            Logger.error('PERSONNEL', `❌ Error: ${res.message}`);
            Toast.error(res.message);
        }
    },

    async setPermission(userId, permKey, granted) {
        Logger.log('PERMISSIONS', `Asignando permiso: ${permKey}=${granted} para usuario ${userId}`);
        const res = await this.apiCall('user.set_permission', { 
            tenant_id: this.state.user.tenant_id, 
            user_id: userId, 
            permission_key: permKey, 
            granted: granted 
        });
        if (res.status === 'success') {
            Logger.success('PERMISSIONS', '✅ Permiso actualizado');
            Toast.success('Permiso actualizado');
            this.loadPersonnel();
        } else {
            Logger.error('PERMISSIONS', `❌ Error: ${res.message}`);
            Toast.error(res.message);
        }
    },

    async revokeAccess(userId) {
        Logger.log('PERSONNEL', `Revocando acceso para usuario: ${userId}`);
        if (!confirm("¿Revocar acceso a este usuario?")) return;
        const res = await this.apiCall('user.revoke_access', { user_id: userId });
        if (res.status === 'success') {
            Logger.success('PERSONNEL', '✅ Acceso revocado');
            Toast.success('Acceso revocado');
            this.loadPersonnel();
        } else {
            Logger.error('PERSONNEL', `❌ Error: ${res.message}`);
            Toast.error(res.message);
        }
    },

    async loadPersonnel() {
        Logger.log('PERSONNEL', '📥 Cargando lista de personal...');
        const res = await this.apiCall('user.list', { tenant_id: this.state.user.tenant_id });
        const container = document.getElementById('personnel-table-body');
        if (!container) {
            Logger.warn('PERSONNEL', '⚠️ Contenedor no encontrado');
            return;
        }
        
        Logger.log('PERSONNEL', 'Respuesta:', res);
        container.innerHTML = '';
        
        if (res.status === 'success' && res.data) {
            Logger.log('PERSONNEL', `✅ ${res.data.length} empleados cargados`);
            res.data.forEach(u => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${u.username}</td>
                    <td><span class="badge badge-success">${u.role}</span></td>
                    <td>
                        <button class="btn btn-secondary" style="padding:4px 8px" onclick="app.promptPermission('${u.id}')">🔑</button>
                        <button class="btn btn-danger" style="padding:4px 8px" onclick="app.revokeAccess('${u.id}')">🗑️</button>
                    </td>
                `;
                container.appendChild(row);
            });
        } else {
            Logger.error('PERSONNEL', `❌ Error cargando personal: ${res.message}`);
        }
    },

    async promptPermission(userId) {
        Logger.log('PERMISSIONS', `Dialog de permiso para usuario: ${userId}`);
        const permKey = prompt("Llave del permiso:");
        if (!permKey) return;
        const granted = confirm(`¿Conceder ${permKey}?`);
        await this.setPermission(userId, permKey, granted);
    },

    // --- STOCK MANAGEMENT ---

    async loadStock() {
        Logger.log('STOCK', '📥 Cargando inventario...');
        const filter = document.getElementById('stock-search')?.value || '';
        const res = await this.apiCall('stock.list', { filter });
        const tbody = document.getElementById('stock-table-body');
        if (!tbody) {
            Logger.warn('STOCK', '⚠️ Tabla no encontrada');
            return;
        }
        
        Logger.log('STOCK', 'Respuesta:', res);
        tbody.innerHTML = '';
        
        if (res.status === 'success' && res.data) {
            Logger.log('STOCK', `✅ ${res.data.length} productos cargados`);
            res.data.forEach(p => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${p.code || p.codigo || '-'}</td>
                    <td>${p.name || p.nombre || '-'}</td>
                    <td>${p.category || p.categoria || '-'}</td>
                    <td>$${parseFloat(p.price || p.precio || 0).toFixed(2)}</td>
                    <td>${p.quantity || p.cantidad || 0}</td>
                    <td>
                        <button class="btn btn-secondary" style="padding:4px 8px" onclick="app.editProduct('${p.code || p.codigo}')">✏️</button>
                        <button class="btn btn-danger" style="padding:4px 8px" onclick="app.deleteProduct('${p.code || p.codigo}')">🗑️</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        } else {
            Logger.error('STOCK', `❌ Error: ${res.message}`);
        }
    },

    setupDebouncedHandlers() {
        Logger.log('SETUP', 'Configurando debounce handlers');
        this.debouncedLoadStock = debounce(() => this.loadStock());
        this.debouncedQuickSearch = debounce(() => this.performQuickSearch(), 400); // 🆕
    },

    showModal(id) {
        Logger.log('MODAL', `Abriendo modal: ${id}`);
        const modal = document.getElementById(id);
        if (modal) modal.classList.remove('hidden'); 
    },
    
    closeModal(id) {
        Logger.log('MODAL', `Cerrando modal: ${id}`);
        const modal = document.getElementById(id);
        if (modal) modal.classList.add('hidden'); 
    },

    async saveProduct() {
        Logger.log('STOCK', '💾 Guardando producto...');
        const params = {
            codigo: document.getElementById('p-code')?.value,
            nombre: document.getElementById('p-name')?.value,
            precio: parseFloat(document.getElementById('p-price')?.value || 0),
            cantidad: parseFloat(document.getElementById('p-qty')?.value || 0),
            categoria: document.getElementById('p-cat')?.value,
            es_peso: document.getElementById('p-weight')?.checked || false
        };
        Logger.log('STOCK', 'Parámetros:', params);
        
        const res = await this.apiCall('stock.add', params);
        if (res.status === 'success') {
            Logger.success('STOCK', '✅ Producto guardado');
            Toast.success('Producto guardado');
            this.closeModal('modal-product');
            this.loadStock();
        } else {
            Logger.error('STOCK', `❌ Error: ${res.message}`);
            Toast.error(res.message);
        }
    },

    async editProduct(codigo) {
        Logger.log('STOCK', `Editando producto: ${codigo}`);
        const res = await this.apiCall('stock.get', { codigo });
        if (res.status === 'success') {
            const p = res.data;
            document.getElementById('p-code').value = p.codigo || p.code;
            document.getElementById('p-name').value = p.nombre || p.name;
            document.getElementById('p-price').value = p.precio || p.price;
            document.getElementById('p-qty').value = p.cantidad || p.quantity;
            document.getElementById('p-cat').value = p.categoria || p.category;
            document.getElementById('p-weight').checked = p.es_peso || p.is_weight;
            this.showModal('modal-product');
        }
    },

    async deleteProduct(codigo) {
        Logger.log('STOCK', `Eliminando producto: ${codigo}`);
        if (confirm('¿Eliminar producto?')) {
            const res = await this.apiCall('stock.delete', { codigo });
            if (res.status === 'success') {
                Logger.success('STOCK', '✅ Producto eliminado');
                Toast.success('Producto eliminado');
                this.loadStock();
            } else {
                Logger.error('STOCK', `❌ Error: ${res.message}`);
                Toast.error(res.message);
            }
        }
    },

    // --- SALES MANAGEMENT (CON AUTOCOMPLETADO) ---

    async performQuickSearch() {
        Logger.log('SALES', '🔍 Ejecutando búsqueda rápida...');
        const searchInput = document.getElementById('sale-scan');
        const searchTerm = searchInput?.value.trim() || '';
        const dropdown = document.getElementById('quick-results');
        
        if (!searchTerm || searchTerm.length < 1) {
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
        products.forEach((product, idx) => {
            const item = document.createElement('div');
            item.className = 'search-result-item';
            item.innerHTML = `
                <div class="search-result-code">${product.codigo}</div>
                <div class="search-result-name">${product.nombre}</div>
                <div class="search-result-meta">💲 $${parseFloat(product.precio || 0).toFixed(2)} | 📦 ${product.cantidad || 0} en stock</div>
            `;
            item.onclick = () => this.selectProductFromSearch(product);
            dropdown.appendChild(item);
        });
        
        dropdown.classList.add('active');
    },

    selectProductFromSearch(product) {
        Logger.log('SALES', '✅ Producto seleccionado:', product);
        this.state.selectedProduct = product;
        this.state.selectedQuantity = 1;
        
        // Cargar UI de selección de cantidad
        this.showQuantitySelector(product);
    },

    showQuantitySelector(product) {
        Logger.log('SALES', '📦 Mostrando selector de cantidad');
        
        // Crear modal o usar elemento existente
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.6);
            backdrop-filter: blur(8px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
        `;
        
        modal.innerHTML = `
            <div class="card" style="width: 100%; max-width: 400px; animation: popIn 0.3s ease;">
                <h3 style="margin-top: 0; margin-bottom: 20px;">📦 ${product.nombre}</h3>
                <div style="margin-bottom: 20px; padding: 15px; background: rgba(99, 102, 241, 0.1); border-radius: 8px;">
                    <div style="font-size: 0.9rem; color: var(--text-muted);">Código: <strong>${product.codigo}</strong></div>
                    <div style="font-size: 0.9rem; color: var(--text-muted); margin-top: 5px;">Precio: <strong>$${parseFloat(product.precio).toFixed(2)}</strong></div>
                    <div style="font-size: 0.9rem; color: var(--text-muted); margin-top: 5px;">Disponibles: <strong>${product.cantidad}</strong></div>
                </div>
                <div class="form-group">
                    <label>Cantidad a agregar:</label>
                    <input type="number" id="qty-selector" class="input" value="1" min="1" max="${product.cantidad}" style="font-size: 1.2rem; text-align: center;">
                </div>
                <div style="display: flex; justify-content: flex-end; gap: 10px;">
                    <button class="btn btn-secondary" onclick="this.closest('[style*=fixed]').remove()">Cancelar</button>
                    <button class="btn btn-primary" onclick="app.confirmProductSelection(this)">Agregar al carrito</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        document.getElementById('qty-selector').focus();
    },

    async confirmProductSelection(button) {
        Logger.log('SALES', '✅ Confirmando selección de producto');
        const modal = button.closest('[style*=fixed]');
        const qtyInput = modal.querySelector('#qty-selector');
        const quantity = parseInt(qtyInput.value) || 1;
        
        if (this.state.selectedProduct) {
            const product = this.state.selectedProduct;
            if (quantity > product.cantidad) {
                Toast.warning(`Solo hay ${product.cantidad} productos disponibles`);
                return;
            }
            
            // Agregar al carrito CON la cantidad seleccionada
            const cartItem = {
                ...product,
                cantidad: quantity,
                quantity: quantity
            };
            
            this.state.cart.push(cartItem);
            Logger.success('SALES', '✅ Producto agregado al carrito', cartItem);
            Toast.success(`${product.nombre} x${quantity} agregado al carrito`);
            
            // Limpiar búsqueda y cerrar modal
            document.getElementById('sale-scan').value = '';
            document.getElementById('quick-results').classList.remove('active');
            modal.remove();
            
            // Actualizar carrito
            this.renderCart();
        }
    },

    renderCart() {
        Logger.log('SALES', 'Renderizando carrito...');
        const container = document.getElementById('cart-items');
        if (!container) {
            Logger.warn('SALES', '⚠️ Contenedor de carrito no encontrado');
            return;
        }
        
        container.innerHTML = '';
        let total = 0;
        
        this.state.cart.forEach((item, idx) => {
            const subtotal = (item.precio || item.price || 0) * (item.cantidad || item.quantity || 1);
            total += subtotal;
            const div = document.createElement('div');
            div.style.cssText = 'display:flex; justify-content:space-between; margin-bottom:8px; padding:8px; background:var(--background); border-radius:8px; font-size:0.9rem;';
            div.innerHTML = `
                <span>${item.nombre || item.name} x ${item.cantidad || item.quantity || 1}</span>
                <span>$${subtotal.toFixed(2)} <button onclick="app.removeFromCart(${idx})" style="border:none; background:none; cursor:pointer; color:var(--error)">🗑️</button></span>
            `;
            container.appendChild(div);
        });
        
        Logger.log('SALES', `Carrito: ${this.state.cart.length} items, Total: $${total.toFixed(2)}`);
        
        const totalEl = document.getElementById('cart-total');
        if (totalEl) totalEl.innerText = `$${total.toFixed(2)}`;
    },

    removeFromCart(idx) {
        Logger.log('SALES', `Removiendo item ${idx} del carrito`);
        this.state.cart.splice(idx, 1);
        this.renderCart();
        Toast.info('Producto removido');
    },

    openCheckout() {
        Logger.log('SALES', 'Abriendo checkout...');
        if (this.state.cart.length === 0) {
            Logger.warn('SALES', '⚠️ Carrito vacío');
            Toast.warning("Carrito vacío");
            return;
        }
        this.showModal('modal-checkout');
    },

    async confirmSale() {
        Logger.log('SALES', '💰 Confirmando venta...');
        const items = this.state.cart.map(item => ({
            codigo: item.codigo || item.code,
            cantidad: item.cantidad || item.quantity || 1
        }));
        
        let total = 0;
        this.state.cart.forEach(item => {
            total += (item.precio || item.price || 0) * (item.cantidad || item.quantity || 1);
        });

        Logger.log('SALES', `Items: ${items.length}, Total: $${total.toFixed(2)}`);
        
        const res = await this.apiCall('venta.cobrar', { 
            cliente: "General", 
            items: items, 
            metodo_pago: "Efectivo", 
            paga_con: total,
            alias: null 
        });
        
        Logger.log('SALES', 'Respuesta:', res);
        
        if (res.status === 'success') {
            Logger.success('SALES', '✅ Venta registrada');
            Toast.success('Venta registrada');
            this.state.cart = [];
            this.renderCart();
            this.closeModal('modal-checkout');
        } else {
            Logger.error('SALES', `❌ Error: ${res.message}`);
            Toast.error(res.message);
        }
    },

    // --- IMPORT MANAGEMENT ---

    async handleFileUpload(input) {
        Logger.log('IMPORT', '📤 Cargando archivo...');
        if (!input.files.length) {
            Logger.warn('IMPORT', '⚠️ No hay archivo seleccionado');
            return;
        }
        
        const file = input.files[0];
        Logger.log('IMPORT', `Archivo: ${file.name}, Tamaño: ${file.size} bytes`);
        
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: {
                    'Authorization': this.state.token
                },
                body: formData
            });

            const data = await response.json();
            Logger.log('IMPORT', 'Respuesta upload:', data);
            
            if (data.payload.status === 'success') {
                Logger.success('IMPORT', '✅ Archivo cargado');
                Toast.success('Archivo cargado');
                document.getElementById('btn-run-import').disabled = false;
            } else {
                Logger.error('IMPORT', `❌ Error: ${data.payload.message}`);
                Toast.error(data.payload.message);
            }
        } catch (e) {
            Logger.error('IMPORT', '❌ Error en upload:', e);
            Toast.error('Error en upload');
        }
    },

    async runImportPreview() {
        Logger.log('IMPORT', '🔍 Ejecutando preview de importación...');
        Toast.info('Función en desarrollo');
    },

    async commitImport() {
        Logger.log('IMPORT', '💾 Confirmando importación...');
        Toast.info('Función en desarrollo');
    },

    // --- ALIAS MANAGEMENT ---

    async addAlias() {
        Logger.log('ALIAS', '➕ Agregando nuevo alias...');
        const nombre = document.getElementById('alias-name')?.value;
        const limite = parseFloat(document.getElementById('alias-limit')?.value || 0);
        
        Logger.log('ALIAS', `Nombre: ${nombre}, Límite: $${limite}`);
        
        if (!nombre || limite <= 0) {
            Logger.warn('ALIAS', '⚠️ Datos inválidos');
            Toast.warning("Ingrese nombre y límite válidos");
            return;
        }

        const res = await this.apiCall('alias.add', { nombre, limite });
        Logger.log('ALIAS', 'Respuesta:', res);
        
        if (res.status === 'success') {
            Logger.success('ALIAS', '✅ Alias agregado');
            Toast.success("Alias agregado");
            document.getElementById('alias-name').value = '';
            document.getElementById('alias-limit').value = '';
            this.loadAliases();
        } else {
            Logger.error('ALIAS', `❌ Error: ${res.message}`);
            Toast.error(res.message);
        }
    },

    async loadAliases() {
        Logger.log('ALIAS', '📥 Cargando lista de alias...');
        const res = await this.apiCall('alias.list', {});
        const container = document.getElementById('alias-table-body');
        if (!container) {
            Logger.warn('ALIAS', '⚠️ Tabla no encontrada');
            return;
        }
        
        Logger.log('ALIAS', 'Respuesta:', res);
        container.innerHTML = '';
        
        if (res.status === 'success' && res.data) {
            Logger.log('ALIAS', `✅ ${res.data.length} alias cargados`);
            res.data.forEach(a => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${a.nombre}</td>
                    <td>$${parseFloat(a.limite || 0).toFixed(2)}</td>
                    <td>$${parseFloat(a.acumulado || 0).toFixed(2)}</td>
                    <td>
                        <button class="btn btn-danger" style="padding:4px 8px" onclick="app.deleteAlias('${a.id}')">🗑️</button>
                    </td>
                `;
                container.appendChild(row);
            });
        } else {
            Logger.error('ALIAS', `❌ Error cargando alias: ${res.message}`);
        }
    },

    async deleteAlias(aliasId) {
        Logger.log('ALIAS', `🗑️ Eliminando alias: ${aliasId}`);
        if (confirm('¿Eliminar alias?')) {
            const res = await this.apiCall('alias.delete', { alias_id: aliasId });
            Logger.log('ALIAS', 'Respuesta:', res);
            
            if (res.status === 'success') {
                Logger.success('ALIAS', '✅ Alias eliminado');
                Toast.success('Alias eliminado');
                this.loadAliases();
            } else {
                Logger.error('ALIAS', `❌ Error: ${res.message}`);
                Toast.error(res.message);
            }
        }
    },

    // --- SUBSCRIPTION MANAGEMENT ---

    async loadSubscription() {
        Logger.log('SUBSCRIPTION', '📥 Cargando información de suscripción...');
        const container = document.getElementById('current-plan');
        if (container && this.state.user) {
            container.innerHTML = `
                <strong>Plan:</strong> ${this.state.user.plan || 'FREE'}<br>
                <strong>Créditos:</strong> ${this.state.user.credits || 0}<br>
                <strong>Tenant:</strong> ${this.state.user.tenant_id || '-'}
            `;
            Logger.log('SUBSCRIPTION', 'Plan:', this.state.user.plan);
        }
    },

    async updatePlan(plan, credits) {
        Logger.log('SUBSCRIPTION', `Actualizando plan a ${plan} con +${credits} créditos`);
        const res = await this.apiCall('sys.subscription.update', { 
            tenant_id: this.state.user.tenant_id, 
            plan: plan, 
            credits: credits 
        });
        if (res.status === 'success') {
            Logger.success('SUBSCRIPTION', `✅ Plan actualizado`);
            Toast.success(`Plan actualizado a ${plan}`);
            await this.loadSubscription();
        } else {
            Logger.error('SUBSCRIPTION', `❌ Error: ${res.message}`);
            Toast.error(res.message);
        }
    },

    // --- CASH MANAGEMENT ---

    async loadCashStatus() {
        Logger.log('CASH', '📥 Cargando estado de caja...');
        const res = await this.apiCall('caja.status', {});
        const container = document.getElementById('cash-status');
        if (!container) {
            Logger.warn('CASH', '⚠️ Contenedor no encontrado');
            return;
        }
        
        Logger.log('CASH', 'Respuesta:', res);
        
        if (res.status === 'success' && res.data) {
            const d = res.data;
            const totalEsperado = (d.ventas_efectivo || 0) + (d.ventas_digital || 0);
            container.innerHTML = `
                <strong>Estado:</strong> ${d.id ? '🟢 Abierta' : '🔴 Cerrada'}<br>
                <strong>Ventas Efectivo:</strong> $${parseFloat(d.ventas_efectivo || 0).toFixed(2)}<br>
                <strong>Ventas Digital:</strong> $${parseFloat(d.ventas_digital || 0).toFixed(2)}<br>
                <strong>Total Esperado:</strong> $${totalEsperado.toFixed(2)}
            `;
            Logger.log('CASH', `Estado: Abierta=${d.abierta}, Total=$${totalEsperado.toFixed(2)}`);
        } else {
            container.innerHTML = 'No hay caja abierta actualmente.';
            Logger.log('CASH', 'Sin caja abierta');
        }
    },

    async openCash() {
        Logger.log('CASH', '🟢 Abriendo caja...');
        const monto_inicial = parseFloat(document.getElementById('cash-amount')?.value || 0);
        Logger.log('CASH', `Monto inicial: $${monto_inicial}`);
        
        const res = await this.apiCall('caja.abrir', { monto_inicial });
        Logger.log('CASH', 'Respuesta:', res);
        
        if (res.status === 'success') {
            Logger.success('CASH', '✅ Caja abierta');
            Toast.success('Caja abierta');
            this.loadCashStatus();
        } else {
            Logger.error('CASH', `❌ Error: ${res.message}`);
            Toast.error(res.message);
        }
    },

    async closeCash() {
        Logger.log('CASH', '🔴 Cerrando caja...');
        const monto_real = parseFloat(document.getElementById('cash-amount')?.value || 0);
        Logger.log('CASH', `Monto real: $${monto_real}`);
        
        const res = await this.apiCall('caja.cerrar', { monto_real });
        Logger.log('CASH', 'Respuesta:', res);
        
        if (res.status === 'success') {
            Logger.success('CASH', '✅ Caja cerrada');
            Toast.success('Caja cerrada');
            this.loadCashStatus();
        } else {
            Logger.error('CASH', `❌ Error: ${res.message}`);
            Toast.error(res.message);
        }
    },

    // --- REPORTS ---

    async loadReports() {
        Logger.log('REPORTS', '📊 Cargando reportes...');
        const [resResumen, resAlertas] = await Promise.all([
            this.apiCall('reporte.resumen', {}),
            this.apiCall('reporte.alertas', {})
        ]);

        Logger.log('REPORTS', 'Respuestas:', { resumen: resResumen, alertas: resAlertas });

        const summaryEl = document.getElementById('report-summary');
        if (summaryEl && resResumen.status === 'success') {
            const d = resResumen.data;
            summaryEl.innerHTML = `
                <strong>Total Facturado:</strong> $${parseFloat(d.total_facturado || 0).toFixed(2)}<br>
                <strong>Ganancia Est. (30%):</strong> $${parseFloat(d.ganancia_estimada || 0).toFixed(2)}
            `;
            Logger.log('REPORTS', `Facturación: $${d.total_facturado}`);
        }

        const alertsEl = document.getElementById('report-alerts');
        if (alertsEl && resAlertas.status === 'success') {
            alertsEl.innerHTML = '';
            if (resAlertas.data.length === 0) {
                alertsEl.innerHTML = '<p style="color: var(--text-muted)">No hay alertas de stock.</p>';
                Logger.log('REPORTS', 'Sin alertas de stock');
            } else {
                Logger.log('REPORTS', `${resAlertas.data.length} alertas de stock`);
                resAlertas.data.forEach(p => {
                    const div = document.createElement('div');
                    div.style.cssText = 'padding:10px; margin-bottom:10px; background:rgba(239, 68, 68, 0.1); border-left: 4px solid var(--error); border-radius:4px; font-size:0.9rem;';
                    div.innerHTML = `<strong>${p.nombre}</strong>: Solo quedan ${p.cantidad} unidades.`;
                    alertsEl.appendChild(div);
                });
            }
        }
    },

    async exportCSV() {
        Logger.log('EXPORT', '📄 Exportando a CSV...');
        const res = await this.apiCall('sys.export_csv', {});
        Logger.log('EXPORT', 'Respuesta:', res);
        
        if (res.status === 'success') {
            Logger.success('EXPORT', '✅ Exportación completada');
            Toast.success('Exportación completada');
        } else {
            Logger.error('EXPORT', `❌ Error: ${res.message}`);
            Toast.error(res.message);
        }
    },

    // --- UTILITIES ---

    async loadConfig() {
        Logger.log('CONFIG', 'Cargando configuración...');
        // Mock implementation
        return Promise.resolve();
    },

    async loadTranslations() {
        Logger.log('TRANSLATIONS', 'Cargando traducciones...');
        // Mock implementation
        return Promise.resolve();
    },

    applyTheme() {
        Logger.log('THEME', `Aplicando tema: ${this.state.theme}`);
        // Mock implementation
    },

    applyTranslations() {
        Logger.log('TRANSLATIONS', `Aplicando traducciones: ${this.state.lang}`);
        // Mock implementation
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

    // 🆕 MÉTODO AUXILIAR: Handler del input en búsqueda de ventas
    handleSaleSearchInput() {
        Logger.log('SALES', '⌨️ Input en búsqueda de ventas detectado');
        this.debouncedQuickSearch();
    }
};

// Inicializar app cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    Logger.log('BOOTSTRAP', '🔧 DOM ready. Iniciando app...');
    app.init();
});
