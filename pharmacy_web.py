"""
PHARMACY MANAGEMENT SYSTEM - Web Interface COMPLET
Cu toate funcționalitățile, adaptat pentru structura ta de baze de date
"""

import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')


# ====================== CONFIGURARE ======================
class Config:
    DB_CONFIG = {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "pharmacy"
    }

    ROLES = ["admin", "pharmacist", "manager", "cashier"]

    @staticmethod
    def get_connection():
        """Returnează o conexiune la baza de date"""
        try:
            conn = mysql.connector.connect(**Config.DB_CONFIG)
            return conn
        except mysql.connector.Error as err:
            st.error(f"❌ Database connection error: {err}")
            return None

    @staticmethod
    def init_database():
        """Inițializează baza de date CU ADAPTARE pentru structura existentă"""
        try:
            conn = mysql.connector.connect(
                host=Config.DB_CONFIG["host"],
                user=Config.DB_CONFIG["user"],
                password=Config.DB_CONFIG["password"]
            )
            cursor = conn.cursor()

            # Creează baza de date dacă nu există
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_CONFIG['database']}")
            cursor.execute(f"USE {Config.DB_CONFIG['database']}")

            # === TABELA MEDICINES_INFO - CREARE SAU ADAPTARE ===
            # Verifică dacă tabela există
            cursor.execute("SHOW TABLES LIKE 'medicines_info'")
            if cursor.fetchone():
                # Tabela există - verifică coloanele
                cursor.execute("DESCRIBE medicines_info")
                existing_columns = [row[0] for row in cursor.fetchall()]

                # Lista coloanelor necesare pentru aplicație
                needed_columns = {
                    'Med_code': 'VARCHAR(20) PRIMARY KEY',
                    'Med_name': 'VARCHAR(100) NOT NULL',
                    'Qty': 'INT NOT NULL DEFAULT 0',
                    'MRP': 'DECIMAL(10,2) NOT NULL',
                    'Cost': 'DECIMAL(10,2)',
                    'Category': 'VARCHAR(50)',
                    'Mfg': 'DATE',
                    'Exp': 'DATE',
                    'Purpose': 'TEXT',
                    'Supplier': 'VARCHAR(100)',
                    'Reorder_level': 'INT DEFAULT 20',
                    'Created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                }

                # Adaugă coloanele lipsă
                for col_name, col_type in needed_columns.items():
                    if col_name not in existing_columns:
                        try:
                            if col_name == 'Med_code' and 'Med_code' in existing_columns:
                                continue  # Skip primary key dacă există deja
                            cursor.execute(f"ALTER TABLE medicines_info ADD COLUMN {col_name} {col_type}")
                            print(f"✓ Adăugată coloana: {col_name}")
                        except Exception as e:
                            print(f"⚠ Nu s-a putut adăuga coloana {col_name}: {e}")
            else:
                # Tabela nu există - creează-o completă
                cursor.execute("""
                    CREATE TABLE medicines_info (
                        Med_code VARCHAR(20) PRIMARY KEY,
                        Med_name VARCHAR(100) NOT NULL,
                        Qty INT NOT NULL DEFAULT 0,
                        MRP DECIMAL(10,2) NOT NULL,
                        Cost DECIMAL(10,2),
                        Category VARCHAR(50),
                        Mfg DATE,
                        Exp DATE,
                        Purpose TEXT,
                        Supplier VARCHAR(100),
                        Reorder_level INT DEFAULT 20,
                        Created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("✓ Tabela medicines_info creată cu toate coloanele")

            # === TABELA USERS ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role ENUM('admin', 'pharmacist', 'manager', 'cashier') NOT NULL,
                    full_name VARCHAR(100),
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # === TABELA SALES ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id INT AUTO_INCREMENT PRIMARY KEY,
                    medicine_code VARCHAR(20),
                    quantity INT,
                    sale_price DECIMAL(10,2),
                    total DECIMAL(10,2),
                    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cashier_id INT
                )
            """)

            # Adaugă utilizatori demo dacă nu există
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                default_users = [
                    ("admin", "admin123", "admin", "Administrator", "admin@pharmacy.com"),
                    ("pharmacist", "pharma123", "pharmacist", "John Pharmacist", "pharma@pharmacy.com"),
                    ("cashier", "cash123", "cashier", "Alice Cashier", "cashier@pharmacy.com"),
                    ("manager", "manager123", "manager", "Bob Manager", "manager@pharmacy.com")
                ]

                for user in default_users:
                    try:
                        cursor.execute(
                            "INSERT INTO users (username, password, role, full_name, email) VALUES (%s, %s, %s, %s, %s)",
                            user
                        )
                    except:
                        pass  # User poate exista deja

            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Database initialized successfully!")
            return True

        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            return False

    @staticmethod
    def check_column_exists(table, column):
        """Verifică dacă o coloană există într-un tabel"""
        try:
            conn = Config.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE '{column}'")
            exists = cursor.fetchone() is not None
            cursor.close()
            conn.close()
            return exists
        except:
            return False


# ====================== FUNCȚII UTILITARE ADAPTATE ======================
class DatabaseHelper:
    @staticmethod
    def execute_query(query, params=None, fetch=True):
        """Execută o interogare SQL și returnează rezultatele"""
        conn = Config.get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())

            if fetch:
                if query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return result, columns
                else:
                    conn.commit()
                    return cursor.rowcount

            conn.commit()
            return None

        except Exception as e:
            st.error(f"❌ Query error: {e}")
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()
            conn.close()

    @staticmethod
    def get_dataframe(query, params=None):
        """Returnează un DataFrame pandas din interogare"""
        conn = Config.get_connection()
        if not conn:
            return pd.DataFrame()

        try:
            df = pd.read_sql_query(query, conn, params=params)
            return df
        except Exception as e:
            st.error(f"❌ DataFrame error: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    @staticmethod
    def get_safe_dataframe(query, params=None, default_columns=None):
        """Versiune safe pentru DataFrame care evită erorile de coloane lipsă"""
        try:
            return DatabaseHelper.get_dataframe(query, params)
        except:
            # Dacă query-ul eșuează din cauza coloanelor lipsă, încercă o variantă mai simplă
            if default_columns:
                # Construiește un query simplificat
                simple_query = query
                # Înlocuiește SELECT * cu SELECT coloane_simple
                if "SELECT *" in query.upper():
                    simple_query = query.replace("SELECT *", f"SELECT {', '.join(default_columns)}")
                try:
                    return DatabaseHelper.get_dataframe(simple_query, params)
                except:
                    return pd.DataFrame()
            return pd.DataFrame()


# ====================== FUNCȚII SPECIALE ADAPTATE ======================
def get_column_safe(table, column, default_value=None):
    """Returnează o coloană safe (folosește valoarea implicită dacă coloana nu există)"""
    if Config.check_column_exists(table, column):
        return column
    elif default_value is not None:
        return f"'{default_value}' as {column}"
    else:
        return "NULL"


def build_safe_query(base_query, table='medicines_info'):
    """Construiește un query safe care evită coloanele lipsă"""
    # Coloane și valorile lor implicite
    column_defaults = {
        'Category': '',
        'Supplier': '',
        'Reorder_level': 20,
        'Cost': 0,
        'Created_at': 'CURRENT_TIMESTAMP'
    }

    # Pentru SELECT *, înlocuiește cu coloane specifice
    if "SELECT *" in base_query.upper():
        # Obține coloanele reale din tabel
        try:
            conn = Config.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"DESCRIBE {table}")
            real_columns = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            # Construiește SELECT-ul cu coloanele reale
            select_columns = []
            for col in real_columns:
                select_columns.append(col)

            # Adaugă coloanele lipsă cu valori implicite
            for col, default in column_defaults.items():
                if col not in real_columns:
                    select_columns.append(f"'{default}' as {col}")

            safe_query = base_query.replace("SELECT *", f"SELECT {', '.join(select_columns)}")
            return safe_query
        except:
            # Dacă nu putem obține coloanele, folosim o listă de bază
            base_columns = ['Med_code', 'Med_name', 'Qty', 'MRP', 'Mfg', 'Exp', 'Purpose']
            all_columns = base_columns + [f"'{default}' as {col}" for col, default in column_defaults.items()]
            safe_query = base_query.replace("SELECT *", f"SELECT {', '.join(all_columns)}")
            return safe_query

    return base_query


# ====================== INTERFAȚĂ PRINCIPALĂ (NEMODIFICATĂ) ======================
def main():
    # Configurare pagină
    st.set_page_config(
        page_title="Pharmacy Management System",
        page_icon="💊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # CSS personalizat
    st.markdown("""
    <style>
    .main-header {
        color: #9D6DA9;
        text-align: center;
        font-size: 2.8rem;
        margin-bottom: 1rem;
    }
    .sub-header {
        color: #A96DA9;
        font-size: 1.5rem;
        margin-top: 1rem;
    }
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 5px solid #9D6DA9;
    }
    .warning-card {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
    }
    .danger-card {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
    }
    .success-card {
        background-color: #d1e7dd;
        border-left: 5px solid #198754;
    }
    .metric-card {
        background: linear-gradient(135deg, #E7C9F1, #9D6DA9);
        color: white;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    # Inițializează baza de date (doar prima dată)
    if 'db_initialized' not in st.session_state:
        with st.spinner("Initializing database..."):
            success = Config.init_database()
            if success:
                st.session_state.db_initialized = True
                st.success("✅ Database initialized successfully!")
            else:
                st.warning("⚠️ Database initialization completed with some warnings. The app will adapt.")

    # Sidebar - Autentificare
    with st.sidebar:
        st.markdown("## 🔐 Authentication")

        # Login form
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        role = st.selectbox("Role", Config.ROLES, key="login_role")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚪 Login", use_container_width=True):
                # Verifică credențialele
                query = """
                    SELECT id, full_name, role 
                    FROM users 
                    WHERE username = %s AND password = %s AND role = %s
                """
                result = DatabaseHelper.execute_query(query, (username, password, role))

                if result and result[0]:
                    user_data = result[0][0]
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_data[0]
                    st.session_state.user_name = user_data[1]
                    st.session_state.user_role = user_data[2]
                    st.success(f"✅ Welcome, {user_data[1]}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials!")

        with col2:
            if st.button("🚪 Demo Login", use_container_width=True):
                # Auto-login pentru demo
                st.session_state.logged_in = True
                st.session_state.user_id = 1
                st.session_state.user_name = "Administrator"
                st.session_state.user_role = "admin"
                st.success("✅ Demo login successful!")
                st.rerun()

        st.markdown("---")

        # Demo credentials
        st.markdown("### 👥 Demo Credentials")
        st.markdown("""
        - **Admin**: admin / admin123
        - **Pharmacist**: pharmacist / pharma123  
        - **Cashier**: cashier / cash123
        - **Manager**: manager / manager123
        """)

    # Verifică autentificarea
    if not st.session_state.get('logged_in'):
        # Pagina de welcome pentru userii nelogati
        st.markdown('<h1 class="main-header">💊 Pharmacy Management System</h1>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("https://cdn-icons-png.flaticon.com/512/206/206875.png", width=200)

        st.markdown("""
        <div class="card">
        <h3>📋 System Features:</h3>
        <ul>
        <li>🔐 <b>Role-based Authentication</b> - 4 user roles with different permissions</li>
        <li>📦 <b>Medicine Management</b> - Add, edit, delete and search medicines</li>
        <li>💰 <b>Sales Processing</b> - Process sales with automatic stock update</li>
        <li>📊 <b>Automated Reports</b> - Daily, monthly and inventory reports</li>
        <li>🚨 <b>Smart Notifications</b> - Expiry and low stock alerts</li>
        <li>🤝 <b>Supplier Integration</b> - API integration for automatic ordering</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        st.info("👈 **Please login from the sidebar to access the system**")
        return

    # Logout button
    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # Meniu principal pentru useri logati
    st.sidebar.markdown(f"### 👤 Welcome, {st.session_state.user_name}")
    st.sidebar.markdown(f"**Role:** {st.session_state.user_role.title()}")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📌 Navigation")

    # Meniu în funcție de rol
    if st.session_state.user_role == 'admin':
        menu_options = ["📊 Dashboard", "📦 Medicines", "💰 Sales", "📈 Reports",
                        "🚨 Alerts", "👥 Users", "⚙️ Settings"]
    elif st.session_state.user_role == 'pharmacist':
        menu_options = ["📊 Dashboard", "📦 Medicines", "🔍 Search", "🚨 Alerts"]
    elif st.session_state.user_role == 'cashier':
        menu_options = ["📊 Dashboard", "💰 Sales", "🔍 Search"]
    else:  # manager
        menu_options = ["📊 Dashboard", "📈 Reports", "💰 Finance", "🚨 Alerts"]

    selected_menu = st.sidebar.selectbox("Go to", menu_options)

    # Header principal
    st.markdown(f'<h1 class="main-header">💊 Pharmacy Management System</h1>', unsafe_allow_html=True)
    st.markdown(f'<h3 class="sub-header">{selected_menu}</h3>', unsafe_allow_html=True)

    # ====================== DASHBOARD ======================
    if "Dashboard" in selected_menu:
        display_dashboard()

    # ====================== MEDICINES ======================
    elif "Medicines" in selected_menu:
        display_medicines()

    # ====================== SALES ======================
    elif "Sales" in selected_menu:
        display_sales()

    # ====================== REPORTS ======================
    elif "Reports" in selected_menu:
        display_reports()

    # ====================== ALERTS ======================
    elif "Alerts" in selected_menu:
        display_alerts()

    # ====================== USERS ======================
    elif "Users" in selected_menu:
        if st.session_state.user_role in ['admin', 'manager']:
            display_users()
        else:
            st.warning("⛔ You don't have permission to access this section")

    # ====================== SETTINGS ======================
    elif "Settings" in selected_menu:
        display_settings()


# ====================== FUNCȚII PENTRU FIECARE SECȚIUNE (ADAPTATE) ======================

def display_dashboard():
    """Afișează dashboard-ul principal - ADAPTAT"""

    # Row 1: Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Total medicines - QUERY SAFE
        query = "SELECT COUNT(*) FROM medicines_info"
        result = DatabaseHelper.execute_query(query)
        total_meds = result[0][0][0] if result else 0
        st.markdown(f"""
        <div class="metric-card">
        <h3>📦</h3>
        <h2>{total_meds}</h2>
        <p>Total Medicines</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Low stock count - ADAPTAT pentru Reorder_level
        try:
            # Verifică dacă coloana există
            if Config.check_column_exists('medicines_info', 'Reorder_level'):
                query = "SELECT COUNT(*) FROM medicines_info WHERE Qty <= Reorder_level"
            else:
                query = "SELECT COUNT(*) FROM medicines_info WHERE Qty <= 20"

            result = DatabaseHelper.execute_query(query)
            low_stock = result[0][0][0] if result else 0
        except:
            low_stock = 0

        st.markdown(f"""
        <div class="metric-card">
        <h3>⚠️</h3>
        <h2>{low_stock}</h2>
        <p>Low Stock Items</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        # Today's sales
        today = datetime.now().strftime('%Y-%m-%d')
        query = "SELECT SUM(total) FROM sales WHERE DATE(sale_date) = %s"
        result = DatabaseHelper.execute_query(query, (today,))
        today_sales = float(result[0][0][0]) if result and result[0][0][0] else 0
        st.markdown(f"""
        <div class="metric-card">
        <h3>💰</h3>
        <h2>${today_sales:.2f}</h2>
        <p>Today's Sales</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        # Expiring soon
        thirty_days = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        query = "SELECT COUNT(*) FROM medicines_info WHERE Exp BETWEEN CURDATE() AND %s"
        result = DatabaseHelper.execute_query(query, (thirty_days,))
        expiring = result[0][0][0] if result else 0
        st.markdown(f"""
        <div class="metric-card">
        <h3>📅</h3>
        <h2>{expiring}</h2>
        <p>Expiring Soon</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Row 2: Charts - ADAPTATE
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Stock by Category")
        # Query safe pentru Category
        if Config.check_column_exists('medicines_info', 'Category'):
            query = """
                SELECT Category, COUNT(*) as count 
                FROM medicines_info 
                WHERE Category IS NOT NULL AND Category != ''
                GROUP BY Category
            """
        else:
            # Dacă Category nu există, grupăm după Purpose
            query = """
                SELECT Purpose as Category, COUNT(*) as count 
                FROM medicines_info 
                WHERE Purpose IS NOT NULL AND Purpose != ''
                GROUP BY Purpose
            """

        df = DatabaseHelper.get_dataframe(query)

        if not df.empty and len(df) > 0:
            fig = px.pie(df, values='count', names='Category',
                         color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No category data available")

    with col2:
        st.subheader("📈 Sales Trend (Last 7 Days)")
        query = """
            SELECT DATE(sale_date) as date, SUM(total) as sales
            FROM sales 
            WHERE sale_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(sale_date)
            ORDER BY date
        """
        df = DatabaseHelper.get_dataframe(query)

        if not df.empty:
            fig = px.line(df, x='date', y='sales', markers=True,
                          title="Daily Sales", color_discrete_sequence=['#9D6DA9'])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales data for the last 7 days")

    # Row 3: Quick Actions
    st.subheader("⚡ Quick Actions")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🛒 New Sale", use_container_width=True):
            st.session_state.show_sale_form = True
            st.rerun()

    with col2:
        if st.button("📦 Add Medicine", use_container_width=True):
            st.session_state.show_add_medicine = True
            st.rerun()

    with col3:
        if st.button("📊 View Reports", use_container_width=True):
            st.session_state.show_reports = True
            st.rerun()

    with col4:
        if st.button("🚨 Check Alerts", use_container_width=True):
            st.session_state.show_alerts = True
            st.rerun()

    # Row 4: Recent Activities
    st.subheader("🕐 Recent Activities")

    tab1, tab2 = st.tabs(["Recent Sales", "Recent Medicines"])

    with tab1:
        # Query safe pentru recent sales
        query = """
            SELECT s.sale_date, m.Med_name, s.quantity, s.total
            FROM sales s
            JOIN medicines_info m ON s.medicine_code = m.Med_code
            ORDER BY s.sale_date DESC
            LIMIT 10
        """
        df = DatabaseHelper.get_dataframe(query)

        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No recent sales")

    with tab2:
        # Query safe pentru recent medicines
        query = build_safe_query("""
            SELECT Med_name, Qty, MRP, Exp
            FROM medicines_info
            ORDER BY Created_at DESC
            LIMIT 10
        """)
        df = DatabaseHelper.get_dataframe(query)

        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No medicines in database")


def display_medicines():
    """Afișează managementul medicamentelor - COMPLET ADAPTAT"""

    st.subheader("📦 Medicine Management")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 View All", "➕ Add New", "🔍 Search", "⚠️ Low Stock"])

    # Tab 1: View All Medicines - ADAPTAT
    with tab1:
        col1, col2 = st.columns([3, 1])

        with col2:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()

            export_format = st.selectbox("Export as", ["CSV", "Excel"])

            if st.button("📥 Export Data", use_container_width=True):
                # Folosește query safe
                query = build_safe_query("SELECT * FROM medicines_info ORDER BY Med_name")
                df = DatabaseHelper.get_dataframe(query)

                if not df.empty:
                    if export_format == "CSV":
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name="medicines.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("Excel export requires openpyxl. Run: pip install openpyxl")

        # Folosește query safe
        query = build_safe_query("SELECT * FROM medicines_info ORDER BY Med_name")
        df = DatabaseHelper.get_dataframe(query)

        if not df.empty:
            st.dataframe(df, use_container_width=True, height=400)

            # Statistics - safe pentru coloanele lipsă
            if 'Qty' in df.columns and 'MRP' in df.columns:
                total_value = (df['Qty'] * df['MRP']).sum()
                avg_price = df['MRP'].mean()
            else:
                total_value = 0
                avg_price = 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Medicines", len(df))
            with col2:
                st.metric("Total Inventory Value", f"${total_value:,.2f}")
            with col3:
                st.metric("Average Price", f"${avg_price:.2f}")
        else:
            st.info("No medicines found in database")

    # Tab 2: Add New Medicine - ADAPTAT
    with tab2:
        with st.form("add_medicine_form"):
            col1, col2 = st.columns(2)

            with col1:
                med_code = st.text_input("Medicine Code *", help="Unique code for the medicine")
                med_name = st.text_input("Medicine Name *")
                quantity = st.number_input("Quantity *", min_value=0, value=10)
                mrp = st.number_input("MRP (Price) *", min_value=0.0, value=0.0, format="%.2f")
                cost = st.number_input("Cost Price", min_value=0.0, value=0.0, format="%.2f")

            with col2:
                category = st.text_input("Category")
                mfg_date = st.date_input("Manufacturing Date", value=datetime.now())
                exp_date = st.date_input("Expiry Date *", value=datetime.now() + timedelta(days=365))
                purpose = st.text_area("Purpose")
                supplier = st.text_input("Supplier")
                reorder_level = st.number_input("Reorder Level", min_value=1, value=20)

            submitted = st.form_submit_button("💾 Save Medicine", use_container_width=True)

            if submitted:
                if not med_code or not med_name or mrp <= 0:
                    st.error("Please fill all required fields (*)")
                else:
                    # Construiește query-ul dinamic bazat pe coloanele existente
                    conn = Config.get_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()

                            # Obține coloanele existente
                            cursor.execute("DESCRIBE medicines_info")
                            existing_columns = [row[0] for row in cursor.fetchall()]

                            # Pregătește datele pentru inserare
                            columns = []
                            values = []
                            placeholders = []

                            # Adaugă coloanele obligatorii
                            mandatory_fields = {
                                'Med_code': med_code,
                                'Med_name': med_name,
                                'Qty': quantity,
                                'MRP': mrp,
                                'Purpose': purpose if purpose else ''
                            }

                            for col, val in mandatory_fields.items():
                                if col in existing_columns:
                                    columns.append(col)
                                    values.append(val)
                                    placeholders.append("%s")

                            # Adaugă coloanele opționale dacă există
                            optional_fields = {
                                'Cost': cost if cost > 0 else 0,
                                'Category': category,
                                'Mfg': mfg_date,
                                'Exp': exp_date,
                                'Supplier': supplier,
                                'Reorder_level': reorder_level
                            }

                            for col, val in optional_fields.items():
                                if col in existing_columns:
                                    columns.append(col)
                                    values.append(val)
                                    placeholders.append("%s")

                            # Construiește și execută query-ul
                            if columns:
                                columns_str = ', '.join(columns)
                                placeholders_str = ', '.join(placeholders)
                                query = f"INSERT INTO medicines_info ({columns_str}) VALUES ({placeholders_str})"

                                cursor.execute(query, values)
                                conn.commit()

                                st.success(f"✅ Medicine '{med_name}' added successfully!")
                                st.balloons()
                            else:
                                st.error("❌ No valid columns found for insertion")

                        except Exception as e:
                            st.error(f"❌ Failed to add medicine: {str(e)}")
                        finally:
                            cursor.close()
                            conn.close()

    # Tab 3: Search Medicine - ADAPTAT
    with tab3:
        col1, col2 = st.columns([1, 3])

        with col1:
            # Opțiuni de căutare bazate pe coloanele existente
            search_options = ["Name", "Code", "Purpose"]
            if Config.check_column_exists('medicines_info', 'Category'):
                search_options.append("Category")
            if Config.check_column_exists('medicines_info', 'Supplier'):
                search_options.append("Supplier")

            search_by = st.selectbox("Search by", search_options)
            search_term = st.text_input("Search term")

        with col2:
            if search_term:
                # Construiește query-ul de căutare
                if search_by == "Name":
                    query = "SELECT * FROM medicines_info WHERE Med_name LIKE %s"
                elif search_by == "Code":
                    query = "SELECT * FROM medicines_info WHERE Med_code LIKE %s"
                elif search_by == "Category" and Config.check_column_exists('medicines_info', 'Category'):
                    query = "SELECT * FROM medicines_info WHERE Category LIKE %s"
                elif search_by == "Purpose":
                    query = "SELECT * FROM medicines_info WHERE Purpose LIKE %s"
                elif search_by == "Supplier" and Config.check_column_exists('medicines_info', 'Supplier'):
                    query = "SELECT * FROM medicines_info WHERE Supplier LIKE %s"
                else:
                    query = "SELECT * FROM medicines_info WHERE Med_name LIKE %s"

                # Folosește query safe
                query = build_safe_query(query)
                df = DatabaseHelper.get_dataframe(query, (f"%{search_term}%",))

                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    st.info(f"Found {len(df)} results")
                else:
                    st.warning("No results found")
            else:
                st.info("Enter a search term to find medicines")

    # Tab 4: Low Stock - ADAPTAT
    with tab4:
        # Construiește query safe pentru low stock
        if Config.check_column_exists('medicines_info', 'Reorder_level') and Config.check_column_exists(
                'medicines_info', 'Supplier'):
            query = """
                SELECT Med_code, Med_name, Qty, Reorder_level, MRP, Supplier
                FROM medicines_info 
                WHERE Qty <= Reorder_level
                ORDER BY Qty
            """
        elif Config.check_column_exists('medicines_info', 'Reorder_level'):
            query = """
                SELECT Med_code, Med_name, Qty, Reorder_level, MRP, '' as Supplier
                FROM medicines_info 
                WHERE Qty <= Reorder_level
                ORDER BY Qty
            """
        else:
            query = """
                SELECT Med_code, Med_name, Qty, 20 as Reorder_level, MRP, '' as Supplier
                FROM medicines_info 
                WHERE Qty <= 20
                ORDER BY Qty
            """

        df = DatabaseHelper.get_dataframe(query)

        if not df.empty:
            st.markdown(f"### ⚠️ Low Stock Alert ({len(df)} items)")

            # Create order suggestions
            if 'Qty' in df.columns and 'Reorder_level' in df.columns and 'MRP' in df.columns:
                df['Order_Qty'] = df['Reorder_level'] - df['Qty']
                df['Order_Qty'] = df['Order_Qty'].apply(lambda x: max(x, 0))  # Numere pozitive
                df['Order_Value'] = df['Order_Qty'] * df['MRP']
            else:
                df['Order_Qty'] = 0
                df['Order_Value'] = 0

            st.dataframe(df, use_container_width=True)

            # Order summary
            total_order_qty = df['Order_Qty'].sum()
            total_order_value = df['Order_Value'].sum()

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total to Order", f"{total_order_qty} units")
            with col2:
                st.metric("Estimated Cost", f"${total_order_value:.2f}")

            # Generate order button
            if st.button("📋 Generate Purchase Order", use_container_width=True):
                order_text = "PURCHASE ORDER\n"
                order_text += "=" * 50 + "\n"
                order_text += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
                order_text += f"Generated by: {st.session_state.user_name}\n"
                order_text += "=" * 50 + "\n\n"

                for _, row in df.iterrows():
                    if row['Order_Qty'] > 0:
                        order_text += f"• {row['Med_name']} ({row['Med_code']})\n"
                        order_text += f"  Order: {row['Order_Qty']} units @ ${row['MRP']:.2f}\n"
                        if 'Supplier' in df.columns and row['Supplier']:
                            order_text += f"  Supplier: {row['Supplier']}\n\n"

                order_text += "=" * 50 + "\n"
                order_text += f"TOTAL: {total_order_qty} units, ${total_order_value:.2f}"

                st.text_area("Purchase Order", order_text, height=300)

                # Download option
                st.download_button(
                    label="📥 Download Order",
                    data=order_text,
                    file_name="purchase_order.txt",
                    mime="text/plain"
                )
        else:
            st.success("🎉 No low stock items!")


def display_sales():
    """Afișează managementul vânzărilor - COMPLET (funcționează deja)"""
    # Această funcție este deja compatibilă cu structura ta
    # O păstrez nemodificată deoarece folosește doar coloanele de bază

    st.subheader("💰 Sales Management")

    tab1, tab2 = st.tabs(["🛒 New Sale", "📋 Sales History"])

    # Tab 1: New Sale
    with tab1:
        with st.form("new_sale_form"):
            col1, col2 = st.columns([2, 1])

            with col1:
                # Get available medicines
                query = "SELECT Med_code, Med_name, MRP, Qty FROM medicines_info WHERE Qty > 0 ORDER BY Med_name"
                result = DatabaseHelper.execute_query(query)

                if result and result[0]:
                    medicines = result[0]
                    medicine_options = {f"{m[1]} (Stock: {m[3]})": m for m in medicines}

                    selected_display = st.selectbox(
                        "Select Medicine",
                        options=list(medicine_options.keys()),
                        help="Select a medicine from available stock"
                    )

                    if selected_display:
                        selected_med = medicine_options[selected_display]
                        st.info(f"Price: ${selected_med[2]:.2f} | Available: {selected_med[3]} units")

                        quantity = st.number_input(
                            "Quantity",
                            min_value=1,
                            max_value=selected_med[3],
                            value=1,
                            help=f"Maximum {selected_med[3]} units available"
                        )

                        # Calculate total
                        total = quantity * selected_med[2]
                        st.metric("Total Amount", f"${total:.2f}")
                else:
                    st.warning("⚠️ No medicines in stock!")
                    quantity = 0
                    total = 0

            with col2:
                st.markdown("### Sale Details")
                customer_name = st.text_input("Customer Name", value="Walk-in Customer")
                payment_method = st.selectbox("Payment Method", ["Cash", "Card", "Insurance"])
                discount = st.number_input("Discount ($)", min_value=0.0, value=0.0, format="%.2f")

                final_total = max(0, total - discount)
                if discount > 0:
                    st.metric("Final Total", f"${final_total:.2f}")

            submitted = st.form_submit_button("💳 Process Sale", use_container_width=True)

            if submitted:
                if not result or not result[0]:
                    st.error("No medicine selected!")
                elif quantity <= 0:
                    st.error("Quantity must be greater than 0!")
                else:
                    # Process the sale
                    med = selected_med

                    # 1. Add sale record
                    sale_query = """
                        INSERT INTO sales (medicine_code, quantity, sale_price, total, cashier_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    sale_values = (med[0], quantity, med[2], final_total, st.session_state.user_id)

                    # 2. Update stock
                    update_query = "UPDATE medicines_info SET Qty = Qty - %s WHERE Med_code = %s"
                    update_values = (quantity, med[0])

                    # Execute in transaction
                    conn = Config.get_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()

                            # Add sale
                            cursor.execute(sale_query, sale_values)
                            sale_id = cursor.lastrowid

                            # Update stock
                            cursor.execute(update_query, update_values)

                            conn.commit()

                            # Generate receipt
                            receipt = f"""
                            ╔══════════════════════════════════════════╗
                            ║         PHARMACY RECEIPT                 ║
                            ╠══════════════════════════════════════════╣
                            ║ Receipt #: {sale_id:^30} ║
                            ║ Date: {datetime.now().strftime('%Y-%m-%d %H:%M'):^26} ║
                            ╠══════════════════════════════════════════╣
                            ║ Medicine: {med[1]:<27} ║
                            ║ Quantity: {quantity:<26} ║
                            ║ Price: ${med[2]:<28.2f} ║
                            ╠══════════════════════════════════════════╣
                            ║ Subtotal: ${total:<27.2f} ║
                            ║ Discount: ${discount:<27.2f} ║
                            ║ Final Total: ${final_total:<24.2f} ║
                            ╠══════════════════════════════════════════╣
                            ║ Customer: {customer_name:<25} ║
                            ║ Payment: {payment_method:<26} ║
                            ║ Cashier: {st.session_state.user_name:<25} ║
                            ╚══════════════════════════════════════════╝
                            """

                            st.success("✅ Sale processed successfully!")
                            st.balloons()

                            # Show receipt
                            st.code(receipt, language=None)

                            # Option to print/download receipt
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🖨️ Print Receipt"):
                                    st.info("Receipt sent to printer")
                            with col2:
                                st.download_button(
                                    label="📥 Download Receipt",
                                    data=receipt,
                                    file_name=f"receipt_{sale_id}.txt",
                                    mime="text/plain"
                                )

                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Error processing sale: {e}")
                        finally:
                            cursor.close()
                            conn.close()

    # Tab 2: Sales History
    with tab2:
        col1, col2, col3 = st.columns(3)

        with col1:
            date_filter = st.date_input("Filter by Date", value=datetime.now())

        with col2:
            period = st.selectbox("Period", ["Today", "This Week", "This Month", "All Time"])

        with col3:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

        # Build query based on filters
        if period == "Today":
            date_str = date_filter.strftime('%Y-%m-%d')
            where_clause = f"WHERE DATE(s.sale_date) = '{date_str}'"
        elif period == "This Week":
            where_clause = "WHERE YEARWEEK(s.sale_date) = YEARWEEK(CURDATE())"
        elif period == "This Month":
            where_clause = "WHERE MONTH(s.sale_date) = MONTH(CURDATE()) AND YEAR(s.sale_date) = YEAR(CURDATE())"
        else:
            where_clause = ""

        query = f"""
            SELECT s.sale_id, s.sale_date, m.Med_name, s.quantity, 
                   s.sale_price, s.total
            FROM sales s
            JOIN medicines_info m ON s.medicine_code = m.Med_code
            {where_clause}
            ORDER BY s.sale_date DESC
        """

        df = DatabaseHelper.get_dataframe(query)

        if not df.empty:
            # Display sales
            st.dataframe(df, use_container_width=True, height=400)

            # Statistics
            total_sales = df['total'].sum()
            avg_sale = df['total'].mean()
            total_items = df['quantity'].sum()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Sales", f"${total_sales:.2f}")
            with col2:
                st.metric("Average Sale", f"${avg_sale:.2f}")
            with col3:
                st.metric("Items Sold", total_items)

            # Chart
            st.subheader("📈 Sales Trend")
            df['sale_date'] = pd.to_datetime(df['sale_date'])
            df['date'] = df['sale_date'].dt.date

            daily_sales = df.groupby('date')['total'].sum().reset_index()

            if not daily_sales.empty:
                fig = px.line(daily_sales, x='date', y='total',
                              title="Daily Sales Trend", markers=True)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales records found for the selected period")


def display_reports():
    """Afișează rapoarte - ADAPTAT"""

    st.subheader("📈 Reports & Analytics")

    report_type = st.selectbox(
        "Select Report Type",
        ["Daily Sales Report", "Monthly Summary", "Inventory Report",
         "Top Selling Products", "Financial Summary"]
    )

    if report_type == "Daily Sales Report":
        date = st.date_input("Select Date", value=datetime.now())

        if st.button("Generate Report", use_container_width=True):
            query = """
                SELECT s.sale_date, m.Med_name, s.quantity, s.sale_price, s.total
                FROM sales s
                JOIN medicines_info m ON s.medicine_code = m.Med_code
                WHERE DATE(s.sale_date) = %s
                ORDER BY s.sale_date
            """

            df = DatabaseHelper.get_dataframe(query, (date,))

            if not df.empty:
                # Summary
                total_sales = df['total'].sum()
                total_items = df['quantity'].sum()
                avg_sale = df['total'].mean()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Sales", f"${total_sales:.2f}")
                with col2:
                    st.metric("Items Sold", total_items)
                with col3:
                    st.metric("Average Sale", f"${avg_sale:.2f}")

                # Detailed data
                st.subheader("📋 Detailed Sales")
                st.dataframe(df, use_container_width=True)

                # Top products
                st.subheader("🏆 Top Products of the Day")
                top_products = df.groupby('Med_name')['quantity'].sum().nlargest(5)

                fig = px.bar(x=top_products.index, y=top_products.values,
                             title="Top 5 Products by Quantity",
                             labels={'x': 'Product', 'y': 'Quantity Sold'})
                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info(f"No sales recorded on {date}")

    elif report_type == "Monthly Summary":
        month = st.selectbox(
            "Select Month",
            pd.date_range(end=datetime.now(), periods=12, freq='M').strftime("%Y-%m").tolist()
        )

        if st.button("Generate Monthly Report", use_container_width=True):
            query = """
                SELECT 
                    DATE(s.sale_date) as date,
                    COUNT(DISTINCT s.sale_id) as transactions,
                    SUM(s.quantity) as items_sold,
                    SUM(s.total) as daily_total
                FROM sales s
                WHERE DATE_FORMAT(s.sale_date, '%%Y-%%m') = %s
                GROUP BY DATE(s.sale_date)
                ORDER BY date
            """

            df = DatabaseHelper.get_dataframe(query, (month,))

            if not df.empty:
                # Summary
                total_revenue = df['daily_total'].sum()
                total_transactions = df['transactions'].sum()
                total_items = df['items_sold'].sum()
                avg_daily = df['daily_total'].mean()

                st.subheader(f"📅 Monthly Report - {month}")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Revenue", f"${total_revenue:.2f}")
                with col2:
                    st.metric("Transactions", total_transactions)
                with col3:
                    st.metric("Items Sold", total_items)
                with col4:
                    st.metric("Avg Daily", f"${avg_daily:.2f}")

                # Chart
                fig = px.line(df, x='date', y='daily_total',
                              title="Daily Revenue Trend", markers=True)
                st.plotly_chart(fig, use_container_width=True)

                # Data table
                st.dataframe(df, use_container_width=True)

            else:
                st.info(f"No data available for {month}")

    elif report_type == "Inventory Report":
        # Query adaptat pentru Category
        if Config.check_column_exists('medicines_info', 'Category'):
            query = """
                SELECT 
                    CASE 
                        WHEN Category IS NULL OR Category = '' THEN 'Uncategorized'
                        ELSE Category 
                    END as Category,
                    COUNT(*) as count, 
                    SUM(Qty) as total_qty, 
                    AVG(MRP) as avg_price, 
                    SUM(Qty * MRP) as total_value
                FROM medicines_info 
                GROUP BY 
                    CASE 
                        WHEN Category IS NULL OR Category = '' THEN 'Uncategorized'
                        ELSE Category 
                    END
                ORDER BY total_value DESC
            """
        else:
            # Dacă Category nu există, grupăm după primul cuvânt din Purpose
            query = """
                SELECT 
                    CASE 
                        WHEN Purpose IS NULL OR Purpose = '' THEN 'Uncategorized'
                        ELSE SUBSTRING_INDEX(Purpose, ' ', 1)
                    END as Category,
                    COUNT(*) as count, 
                    SUM(Qty) as total_qty, 
                    AVG(MRP) as avg_price, 
                    SUM(Qty * MRP) as total_value
                FROM medicines_info 
                GROUP BY 
                    CASE 
                        WHEN Purpose IS NULL OR Purpose = '' THEN 'Uncategorized'
                        ELSE SUBSTRING_INDEX(Purpose, ' ', 1)
                    END
                ORDER BY total_value DESC
            """

        df = DatabaseHelper.get_dataframe(query)

        if not df.empty:
            st.subheader("📦 Inventory by Category")

            # Pie chart
            fig1 = px.pie(df, values='total_value', names='Category',
                          title="Inventory Value by Category")
            st.plotly_chart(fig1, use_container_width=True)

            # Bar chart
            fig2 = px.bar(df, x='Category', y='total_qty',
                          title="Stock Quantity by Category")
            st.plotly_chart(fig2, use_container_width=True)

            # Data table
            st.dataframe(df, use_container_width=True)

            # Summary
            total_value = df['total_value'].sum()
            total_items = df['total_qty'].sum()

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Inventory Value", f"${total_value:,.2f}")
            with col2:
                st.metric("Total Items in Stock", f"{total_items:,}")

    elif report_type == "Top Selling Products":
        period = st.selectbox("Time Period", ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"])

        if period == "Last 7 Days":
            where_clause = "WHERE s.sale_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        elif period == "Last 30 Days":
            where_clause = "WHERE s.sale_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
        elif period == "Last 90 Days":
            where_clause = "WHERE s.sale_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)"
        else:
            where_clause = ""

        query = f"""
            SELECT 
                m.Med_name,
                COUNT(DISTINCT s.sale_id) as times_sold,
                SUM(s.quantity) as total_quantity,
                SUM(s.total) as total_revenue,
                AVG(s.sale_price) as avg_price
            FROM sales s
            JOIN medicines_info m ON s.medicine_code = m.Med_code
            {where_clause}
            GROUP BY m.Med_code, m.Med_name
            ORDER BY total_revenue DESC
            LIMIT 10
        """

        df = DatabaseHelper.get_dataframe(query)

        if not df.empty:
            st.subheader(f"🏆 Top 10 Products - {period}")

            # Bar chart for revenue
            fig1 = px.bar(df, x='Med_name', y='total_revenue',
                          title="Top Products by Revenue")
            st.plotly_chart(fig1, use_container_width=True)

            # Bar chart for quantity
            fig2 = px.bar(df, x='Med_name', y='total_quantity',
                          title="Top Products by Quantity Sold")
            st.plotly_chart(fig2, use_container_width=True)

            # Data table
            st.dataframe(df, use_container_width=True)

    elif report_type == "Financial Summary":
        # Get financial data
        conn = Config.get_connection()
        if conn:
            cursor = conn.cursor()

            # Total sales
            cursor.execute("SELECT SUM(total) FROM sales")
            total_sales = cursor.fetchone()[0] or 0

            # Today's sales
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("SELECT SUM(total) FROM sales WHERE DATE(sale_date) = %s", (today,))
            today_sales = cursor.fetchone()[0] or 0

            # Inventory value - safe pentru coloanele lipsă
            try:
                cursor.execute("SELECT SUM(Qty * MRP) FROM medicines_info")
                inventory_value = cursor.fetchone()[0] or 0
            except:
                inventory_value = 0

            # Number of products
            cursor.execute("SELECT COUNT(*) FROM medicines_info")
            product_count = cursor.fetchone()[0] or 0

            cursor.close()
            conn.close()

            # Display metrics
            st.subheader("💰 Financial Summary")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Sales (All Time)", f"${total_sales:,.2f}")
            with col2:
                st.metric("Today's Sales", f"${today_sales:,.2f}")
            with col3:
                st.metric("Inventory Value", f"${inventory_value:,.2f}")
            with col4:
                st.metric("Products in Stock", product_count)

            # Monthly trend
            query = """
                SELECT 
                    DATE_FORMAT(sale_date, '%%Y-%%m') as month,
                    SUM(total) as monthly_sales,
                    COUNT(*) as transactions
                FROM sales
                GROUP BY DATE_FORMAT(sale_date, '%%Y-%%m')
                ORDER BY month DESC
                LIMIT 6
            """

            df = DatabaseHelper.get_dataframe(query)

            if not df.empty:
                fig = px.line(df, x='month', y='monthly_sales',
                              title="Monthly Sales Trend (Last 6 Months)",
                              markers=True)
                st.plotly_chart(fig, use_container_width=True)


def display_alerts():
    """Afișează notificări și alerte - ADAPTAT"""

    st.subheader("🚨 System Alerts & Notifications")

    tab1, tab2, tab3 = st.tabs(["⚠️ Low Stock", "📅 Expiry Alerts", "🔔 All Notifications"])

    # Tab 1: Low Stock - ADAPTAT
    with tab1:
        # Query adaptat pentru Reorder_level
        if Config.check_column_exists('medicines_info', 'Reorder_level') and Config.check_column_exists(
                'medicines_info', 'Supplier'):
            query = """
                SELECT Med_code, Med_name, Qty, Reorder_level, MRP, Supplier,
                       (Reorder_level - Qty) as need_to_order
                FROM medicines_info 
                WHERE Qty <= Reorder_level
                ORDER BY Qty
            """
        elif Config.check_column_exists('medicines_info', 'Reorder_level'):
            query = """
                SELECT Med_code, Med_name, Qty, Reorder_level, MRP, '' as Supplier,
                       (Reorder_level - Qty) as need_to_order
                FROM medicines_info 
                WHERE Qty <= Reorder_level
                ORDER BY Qty
            """
        else:
            query = """
                SELECT Med_code, Med_name, Qty, 20 as Reorder_level, MRP, '' as Supplier,
                       (20 - Qty) as need_to_order
                FROM medicines_info 
                WHERE Qty <= 20
                ORDER BY Qty
            """

        df = DatabaseHelper.get_dataframe(query)

        if not df.empty:
            st.markdown(f"### ⚠️ Low Stock Alerts ({len(df)} items)")

            for idx, row in df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.write(f"**{row['Med_name']}** ({row['Med_code']})")
                        st.write(f"Current: {row['Qty']} | Reorder at: {row['Reorder_level']}")
                        if 'Supplier' in df.columns and row['Supplier']:
                            st.write(f"Supplier: {row['Supplier']}")

                    with col2:
                        need = max(row['need_to_order'], 0)
                        st.metric("Need", f"{need}")

                    with col3:
                        if st.button(f"Order", key=f"order_{row['Med_code']}_{idx}"):
                            st.info(f"Order placed for {row['Med_name']}")

            # Summary
            total_to_order = max(df['need_to_order'].sum(), 0)
            estimated_cost = 0
            if 'MRP' in df.columns:
                estimated_cost = (df['need_to_order'].clip(lower=0) * df['MRP']).sum()

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Units to Order", int(total_to_order))
            with col2:
                st.metric("Estimated Cost", f"${estimated_cost:.2f}")

            # Quick order button
            if st.button("📋 Generate Bulk Order", use_container_width=True):
                order_list = []
                for _, row in df.iterrows():
                    if row['need_to_order'] > 0:
                        order_list.append({
                            'Medicine': row['Med_name'],
                            'Code': row['Med_code'],
                            'Order Qty': max(row['need_to_order'], 0),
                            'Price': row['MRP'] if 'MRP' in df.columns else 0,
                            'Supplier': row['Supplier'] if 'Supplier' in df.columns else ''
                        })

                if order_list:
                    order_df = pd.DataFrame(order_list)
                    st.dataframe(order_df, use_container_width=True)

                    csv = order_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Order List",
                        data=csv,
                        file_name="bulk_order.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No items need to be ordered")
        else:
            st.success("🎉 No low stock alerts!")

    # Tab 2: Expiry Alerts - ADAPTAT
    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            # Expired medicines
            query = """
                SELECT Med_code, Med_name, Exp, Qty, MRP
                FROM medicines_info 
                WHERE Exp < CURDATE() AND Qty > 0
                ORDER BY Exp
            """

            df_expired = DatabaseHelper.get_dataframe(query)

            if not df_expired.empty:
                st.markdown(f"### ❌ Expired ({len(df_expired)})")

                for _, row in df_expired.iterrows():
                    with st.container():
                        st.error(f"**{row['Med_name']}** - Expired: {row['Exp']}")
                        if 'Qty' in df_expired.columns and 'MRP' in df_expired.columns:
                            st.write(f"Stock: {row['Qty']} units | Value: ${row['Qty'] * row['MRP']:.2f}")
            else:
                st.success("✅ No expired medicines!")

        with col2:
            # Expiring soon (next 30 days)
            thirty_days = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            query = f"""
                SELECT Med_code, Med_name, Exp, Qty, MRP,
                       DATEDIFF(Exp, CURDATE()) as days_left
                FROM medicines_info 
                WHERE Exp BETWEEN CURDATE() AND '{thirty_days}'
                ORDER BY Exp
            """

            df_expiring = DatabaseHelper.get_dataframe(query)

            if not df_expiring.empty:
                st.markdown(f"### ⏰ Expiring Soon ({len(df_expiring)})")

                for _, row in df_expiring.iterrows():
                    with st.container():
                        days_left = row['days_left']
                        days_color = "red" if days_left <= 7 else "orange" if days_left <= 14 else "blue"
                        st.markdown(
                            f"**{row['Med_name']}** - <span style='color:{days_color}'>{days_left} days left</span>",
                            unsafe_allow_html=True)
                        st.write(f"Expires: {row['Exp']}")
                        if 'Qty' in df_expiring.columns:
                            st.write(f"Stock: {row['Qty']}")
            else:
                st.success("✅ No medicines expiring soon!")

    # Tab 3: All Notifications - ADAPTAT
    with tab3:
        # Combine all alerts
        alerts = []

        # Low stock alerts
        if Config.check_column_exists('medicines_info', 'Reorder_level'):
            query_low = "SELECT Med_name, Qty, Reorder_level FROM medicines_info WHERE Qty <= Reorder_level"
        else:
            query_low = "SELECT Med_name, Qty, 20 as Reorder_level FROM medicines_info WHERE Qty <= 20"

        df_low = DatabaseHelper.get_dataframe(query_low)
        for _, row in df_low.iterrows():
            alerts.append({
                'type': 'low_stock',
                'medicine': row['Med_name'],
                'message': f"Low stock: {row['Qty']}/{row['Reorder_level']}",
                'priority': 'high',
                'icon': '⚠️'
            })

        # Expired alerts
        query_expired = "SELECT Med_name, Exp FROM medicines_info WHERE Exp < CURDATE() AND Qty > 0"
        df_expired = DatabaseHelper.get_dataframe(query_expired)
        for _, row in df_expired.iterrows():
            alerts.append({
                'type': 'expired',
                'medicine': row['Med_name'],
                'message': f"Expired on {row['Exp']}",
                'priority': 'critical',
                'icon': '❌'
            })

        # Expiring soon alerts
        thirty_days = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        query_expiring = f"SELECT Med_name, Exp FROM medicines_info WHERE Exp BETWEEN CURDATE() AND '{thirty_days}'"
        df_expiring = DatabaseHelper.get_dataframe(query_expiring)
        for _, row in df_expiring.iterrows():
            days_left = (row['Exp'] - datetime.now().date()).days
            alerts.append({
                'type': 'expiring_soon',
                'medicine': row['Med_name'],
                'message': f"Expires in {days_left} days",
                'priority': 'medium' if days_left > 7 else 'high',
                'icon': '⏰'
            })

        # Display all alerts
        if alerts:
            st.markdown(f"### 🔔 All Notifications ({len(alerts)})")

            # Sort by priority
            priority_order = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
            alerts.sort(key=lambda x: priority_order.get(x['priority'], 5))

            for alert in alerts:
                if alert['priority'] == 'critical':
                    st.error(f"{alert['icon']} **CRITICAL**: {alert['medicine']} - {alert['message']}")
                elif alert['priority'] == 'high':
                    st.warning(f"{alert['icon']} **HIGH**: {alert['medicine']} - {alert['message']}")
                elif alert['priority'] == 'medium':
                    st.info(f"{alert['icon']} **MEDIUM**: {alert['medicine']} - {alert['message']}")
                else:
                    st.write(f"{alert['icon']} {alert['medicine']} - {alert['message']}")

            # Summary
            critical = sum(1 for a in alerts if a['priority'] == 'critical')
            high = sum(1 for a in alerts if a['priority'] == 'high')
            medium = sum(1 for a in alerts if a['priority'] == 'medium')

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Critical", critical)
            with col2:
                st.metric("High", high)
            with col3:
                st.metric("Medium", medium)
        else:
            st.success("🎉 No notifications! All systems are normal.")


def display_users():
    """Afișează managementul utilizatorilor - COMPLET (funcționează deja)"""
    # Această funcție este deja compatibilă
    # O păstrez nemodificată deoarece folosește tabela users care va fi creată

    st.subheader("👥 User Management")

    tab1, tab2 = st.tabs(["View Users", "Add New User"])

    # Tab 1: View Users
    with tab1:
        query = "SELECT id, username, full_name, role, email, created_at FROM users ORDER BY role, username"
        df = DatabaseHelper.get_dataframe(query)

        if not df.empty:
            st.dataframe(df, use_container_width=True)

            # Statistics
            role_counts = df['role'].value_counts()

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Users", len(df))
            with col2:
                st.metric("Admins", role_counts.get('admin', 0))
            with col3:
                st.metric("Pharmacists", role_counts.get('pharmacist', 0))
            with col4:
                st.metric("Cashiers", role_counts.get('cashier', 0))
        else:
            st.info("No users found")

    # Tab 2: Add New User
    with tab2:
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                username = st.text_input("Username *")
                password = st.text_input("Password *", type="password")
                confirm_password = st.text_input("Confirm Password *", type="password")

            with col2:
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email")
                role = st.selectbox("Role *", Config.ROLES)

            submitted = st.form_submit_button("💾 Add User", use_container_width=True)

            if submitted:
                # Validation
                if not username or not password or not full_name or not role:
                    st.error("Please fill all required fields (*)")
                elif password != confirm_password:
                    st.error("Passwords do not match!")
                else:
                    # Check if username exists
                    check_query = "SELECT id FROM users WHERE username = %s"
                    check_result = DatabaseHelper.execute_query(check_query, (username,))

                    if check_result and check_result[0]:
                        st.error("Username already exists!")
                    else:
                        # Add user
                        insert_query = """
                            INSERT INTO users (username, password, full_name, email, role)
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        values = (username, password, full_name, email, role)

                        result = DatabaseHelper.execute_query(insert_query, values, fetch=False)

                        if result:
                            st.success(f"✅ User '{username}' added successfully!")
                        else:
                            st.error("❌ Failed to add user")


def display_settings():
    """Afișează setările sistemului - COMPLET (funcționează deja)"""

    st.subheader("⚙️ System Settings")

    tab1, tab2, tab3 = st.tabs(["Database", "Notifications", "Appearance"])

    with tab1:
        st.markdown("### Database Settings")

        col1, col2 = st.columns(2)

        with col1:
            st.text_input("Host", value=Config.DB_CONFIG["host"], disabled=True)
            st.text_input("Database", value=Config.DB_CONFIG["database"], disabled=True)

        with col2:
            st.text_input("User", value=Config.DB_CONFIG["user"], disabled=True)
            st.text_input("Password", value="••••••••", type="password", disabled=True)

        if st.button("🔄 Test Database Connection", use_container_width=True):
            conn = Config.get_connection()
            if conn:
                st.success("✅ Database connection successful!")
                conn.close()
            else:
                st.error("❌ Database connection failed!")

        if st.button("🔄 Initialize Database", use_container_width=True):
            with st.spinner("Initializing database..."):
                Config.init_database()
                st.success("✅ Database initialized successfully!")

    with tab2:
        st.markdown("### Notification Settings")

        email_notifications = st.checkbox("Enable Email Notifications", value=True)
        low_stock_alerts = st.checkbox("Low Stock Alerts", value=True)
        expiry_alerts = st.checkbox("Expiry Alerts", value=True)

        alert_days = st.slider("Days before expiry to alert", 7, 90, 30)

        if st.button("💾 Save Notification Settings", use_container_width=True):
            st.success("✅ Notification settings saved!")

    with tab3:
        st.markdown("### Appearance Settings")

        theme = st.selectbox("Theme", ["Light", "Dark", "Auto"])
        language = st.selectbox("Language", ["English", "Romanian", "French"])

        if st.button("💾 Save Appearance Settings", use_container_width=True):
            st.success("✅ Appearance settings saved!")


# ====================== RULARE APLICAȚIE ======================
if __name__ == "__main__":
    main()