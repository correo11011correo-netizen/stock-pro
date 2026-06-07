# Unified Licensing & Tier System: WhatsApp Hub Ecosystem

## 1. Overview
This document defines the licensing architecture for the WhatsApp Hub ecosystem (including Stock Pro, WhatsApp Hub, and the Payment Gateway). The goal is to create a seamless transition between Free and Pro tiers, managed centrally by the Payment Gateway.

## 2. Tier Definitions

### 🟢 FREE Tier (Basic)
Designed for small businesses to start.
- **Stock Pro Features**:
    - Basic product management (Add/Edit/Delete).
    - Simple sales recording.
    - Limited number of employees.
    - No advanced reports.
- **WhatsApp Hub Features**:
    - Basic bot automation.
    - Limited monthly messages.
- **Licensing**: Permanent, no payment required.

### 🔵 PRO Tier (Professional)
Designed for growing businesses requiring analytics and scale.
- **Stock Pro Features**:
    - **Everything in FREE**.
    - Advanced Reports (`reporte.resumen`, `reporte.top`, `reporte.alertas`).
    - CSV Inventory Export (`sys.export_csv`).
    - High-volume import tools.
    - Priority support.
- **WhatsApp Hub Features**:
    - Advanced automation flows.
    - Unlimited monthly messages.
- **Licensing**: Monthly/Yearly subscription managed via Payment Gateway.

### 🟣 ENTERPRISE Tier (Custom)
Designed for large organizations.
- **Everything in PRO**.
- Custom integration hooks.
- Dedicated account manager.
- White-label options.
- **Licensing**: Custom contract.

---

## 3. Technical Integration: Payment Gateway $ightarrow$ Stock Pro

### 3.1. Activation Flow
1. **Payment**: Client pays for a "PRO Plan" via the Payment Gateway.
2. **Notification**: Payment Gateway updates the payment status to `approved`.
3. **Provisioning**: The Payment Gateway calls the Stock Pro `sys.subscription.update` command.
4. **Activation**: Stock Pro updates the `tenants` table in the global database, setting `plan = 'PRO'`.

### 3.2. Permission Enforcement (Command Dispatcher)
Stock Pro's `CommandDispatcher` already implements `es_pro` validation. The logic is as follows:

```python
# In src/commands/dispatcher.py
if is_pro_feature and not is_pro:
    return {"status": "error", "message": "Esta función es exclusiva de la versión PRO."}
```

To integrate with the Payment Gateway, the `is_pro` flag must be fetched from the global `tenants` table during session validation.

---

## 4. Feature Mapping Matrix

| Feature | Free | Pro | Enterprise | Command Key (Stock Pro) |
| :--- | :---: | :---: | :---: | :--- |
| Product List/Search | ✅ | ✅ | ✅ | `stock.list`, `stock.search` |
| Basic Sales | ✅ | ✅ | ✅ | `venta.nueva`, `venta.cobrar` |
| Employee Management| ✅ (Lim) | ✅ | ✅ | `user.invite_employee` |
| Summary Reports | ❌ | ✅ | ✅ | `reporte.resumen` |
| Top Products | ❌ | ✅ | ✅ | `reporte.top` |
| Stock Alerts | ❌ | ✅ | ✅ | `reporte.alertas` |
| CSV Export | ❌ | ✅ | ✅ | `sys.export_csv` |
| Custom API Hooks | ❌ | ❌ | ✅ | N/A |

---

## 5. Deployment Plan for Payment Integration

### Phase 1: Global Tenant Table
Ensure the `tenants` table in the Global DB has the following columns:
- `tenant_id` (PK)
- `plan` (`FREE`, `PRO`, `ENTERPRISE`)
- `subscription_end_date` (Timestamp)
- `payment_gateway_id` (FK to Payment Gateway Client ID)

### Phase 2: Sync Endpoint
Implement a secure endpoint in Stock Pro that allows the Payment Gateway to update a tenant's plan:
- **Endpoint**: `POST /api/admin/update-plan`
- **Payload**: `{ "tenant_id": "...", "plan": "PRO", "expiry": "..." }`
- **Security**: Use a shared `SECRET_TOKEN` between the two platforms.

### Phase 3: Session-Based Validation
Update `auth_service.validate_session` in Stock Pro to include the `is_pro` flag in the session data, so the `CommandDispatcher` can use it without querying the DB on every command.
