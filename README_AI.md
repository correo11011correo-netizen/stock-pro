# 🤖 AI Agent Collaboration Guide: Stock Pro

Welcome, AI Agent. This document serves as your technical map and operational manual for collaborating on the **Stock Pro** project. Stock Pro is a Multi-Tenant SaaS for inventory and sales management with a high focus on security, scalability, and offline-first capabilities.

## 🗺️ 1. Project Architecture Overview

Stock Pro follows a strict **Command-Dispatcher Pattern** to decouple the interface from the business logic.

### ⚙️ Core Components
- **`src/commands/dispatcher.py`**: The Central Brain. ALL actions must go through the `CommandDispatcher`. It handles:
    - Command Routing.
    - **PBAC** (Permission-Based Access Control) validation.
    - **Tier/Licensing** validation (`is_pro` check).
    - God Mode (MASTER role) bypass.
- **`src/core/`**: The Service Layer. Contains the actual business logic.
    - `auth_service.py`: Identity, session management, and tenant resolution.
    - `stock_service.py`: Core inventory logic.
    - `sales_service.py`: Order processing and cash box management.
    - `database.py`: Multi-tenant DB manager (Schema-per-tenant).
    - `global_db.py`: Manager for the `public` schema (tenants, users, sessions).
- **`src/hal/`**: Hardware Abstraction Layer (for barcode scanners/printers).
- **`src/ui/`**: Interface implementations.

## 🛡️ 2. The Security & Access Model

### 🔑 Role Hierarchy
`MASTER` (Global Admin) $ightarrow$ `OWNER` (Tenant Admin) $ightarrow$ `EMPLOYEE` (Staff) $ightarrow$ `FREE` (Basic).

### 🔓 Permission System (PBAC)
Permissions are granular. A user must have a specific `permission_key` (e.g., `perm_stock_write`) to execute sensitive commands.
- **Validation Logic**: Located in `CommandDispatcher.execute()`.
- **Owner Access**: Users with the `OWNER` role bypass granular permission checks within their own tenant.

### 💎 Licensing Tiers
- **FREE**: Access to basic functions.
- **PRO**: Access to advanced reports and exports.
- **Implementation**: Controlled by the `es_pro` boolean in the `commands_map` within the dispatcher.

## 🗄️ 3. Multi-Tenancy Strategy

Stock Pro uses **Schema Isolation** in PostgreSQL:
1. **Global Database (`public` schema)**: Stores the `tenants` table.
2. **Tenant Database (`schema_XXXX` schema)**: Each business gets its own isolated schema containing `products`, `sales`, `audit`, etc.
3. **Context Switching**: The `DatabaseManager` executes `SET search_path TO schema_name, public` upon every connection to ensure data isolation.

## 🛠️ 4. Development Workflow for AI Agents

When adding a new feature or fixing a bug, follow this exact sequence:

### Step A: Logic Implementation
Implement the functionality in the relevant service in `src/core/` (e.g., `stock_service.py`). Ensure the method is clean and follows existing naming conventions.

### Step B: Command Registration
1. Open `src/commands/dispatcher.py`.
2. Define a handler method `_handle_your_command(self, params)`.
3. Add the command to the `commands_map`:
   `"your.command": (self._handle_your_command, "required_role", is_pro_boolean, "perm_key")`

### Step C: Interface Exposure
Expose the command via the API or CLI interface.

### Step D: Validation
- Verify that a `FREE` user cannot access a `PRO` feature.
- Verify that an `EMPLOYEE` without the `perm_key` is blocked.
- Verify that a `MASTER` user can access everything.

## 🚀 5. Key Technical Mandates
- **No Direct Service Calls**: Never call `StockService` directly from the UI. Always use the `CommandDispatcher`.
- **Atomic Updates**: When modifying database schemas, ensure the `DatabaseManager._init_db()` method is updated to maintain consistency for new tenants.
- **Timezone Awareness**: Use UTC for all timestamps to maintain compatibility with cloud environments (e.g., Railway).
- **Logging**: Use the internal `logging` system with prefixes like `AUDIT-DEBUG` for critical actions.

## 📚 6. Quick Reference Table

| Goal | File to Modify | Action |
| :--- | :--- | :--- |
| Add New Feature | `src/core/*.py` $ightarrow$ `dispatcher.py` | Implement logic $ightarrow$ Register command |
| Change Permissions | `src/commands/dispatcher.py` | Update `commands_map` tuple |
| Modify DB Schema | `src/core/database.py` | Update `_init_db()` SQL |
| Manage Users/Auth | `src/core/auth_service.py` | Modify session or user logic |
| Debug Internals | `src/commands/dispatcher.py` | Use `debug.call` command |
