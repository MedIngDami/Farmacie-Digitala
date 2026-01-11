"""
PHARMACY MANAGEMENT SYSTEM - Web Interface COMPLET (SQLite)
Păstrează STRICT schema ta medicines_info:
Med_code, Med_name, Qty, MRP, Mfg, Exp, Purpose
"""

import streamlit as st
from db_sqlite import init_db, query_df, exec_sql
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import warnings

warnings.filterwarnings('ignore')


# ====================== CONFIGURARE ======================
class Config:
    ROLES = ["admin", "pharmacist", "manager", "cashier"]

    # IMPORTANT: deoarece nu vrem să stricăm medicines_info,
    # folosim un prag fix pentru low-stock
    LOW_STOCK_THRESHOLD = 20


# ====================== FUNCȚII UTILITARE (SQLite) ======================
class DatabaseHelper:
    @staticmethod
    def get_dataframe(query, params=None):
        try:
            return query_df(query, params or [])
        except Exception as e:
            st.error(f"❌ DataFrame error: {e}")
            return pd.DataFrame()

    @staticmethod
    def execute(query, params=None):
        try:
            return exec_sql(query, params or [])
        except Exception as e:
            st.error(f"❌ Query error: {e}")
            return 0


# ====================== INTERFAȚĂ PRINCIPALĂ ======================
def main():
    # Inițializează SQLite + tabele
    init_db()

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

    # ====================== SIDEBAR LOGIN ======================
    with st.sidebar:
        st.markdown("## 🔐 Authentication")

        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        role = st.selectbox("Role", Config.ROLES, key="login_role")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🚪 Login", use_container_width=True):
                query = """
                    SELECT id, full_name, role
                    FROM users
                    WHERE username = ? AND password = ? AND role = ?
                    LIMIT 1
                """
                dfu = DatabaseHelper.get_dataframe(query, [username, password, role])

                if not dfu.empty:
                    st.session_state.logged_in = True
                    st.session_state.user_id = int(dfu.iloc[0]["id"])
                    st.session_state.user_name = dfu.iloc[0]["full_name"]
                    st.session_state.user_role = dfu.iloc[0]["role"]
                    st.success(f"✅ Welcome, {st.session_state.user_name}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials!")

        with col2:
            if st.button("🚪 Demo Login", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.user_id = 1
                st.session_state.user_name = "Administrator"
                st.session_state.user_role = "admin"
                st.success("✅ Demo login successful!")
                st.rerun()

        st.markdown("---")
        st.markdown("### 👥 Demo Credentials")
        st.markdown("""
        - **Admin**: admin / admin123
        - **Pharmacist**: pharmacist / pharma123  
        - **Cashier**: cashier / cash123
        - **Manager**: manager / manager123
        """)

    # ====================== WELCOME PAGE (not logged in) ======================
    if not st.session_state.get("logged_in"):
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
        </ul>
        </div>
        """, unsafe_allow_html=True)

        st.info("👈 **Please login from the sidebar to access the system**")
        return

    # ====================== LOGOUT ======================
    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.sidebar.markdown(f"### 👤 Welcome, {st.session_state.user_name}")
    st.sidebar.markdown(f"**Role:** {st.session_state.user_role.title()}")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📌 Navigation")

    # meniu per rol
    if st.session_state.user_role == "admin":
        menu_options = ["📊 Dashboard", "📦 Medicines", "💰 Sales", "📈 Reports", "🚨 Alerts", "👥 Users"]
    elif st.session_state.user_role == "pharmacist":
        menu_options = ["📊 Dashboard", "📦 Medicines", "🔍 Search", "🚨 Alerts"]
    elif st.session_state.user_role == "cashier":
        menu_options = ["📊 Dashboard", "💰 Sales", "🔍 Search"]
    else:  # manager
        menu_options = ["📊 Dashboard", "📈 Reports", "💰 Finance", "🚨 Alerts"]

    selected_menu = st.sidebar.selectbox("Go to", menu_options)

    st.markdown('<h1 class="main-header">💊 Pharmacy Management System</h1>', unsafe_allow_html=True)
    st.markdown(f'<h3 class="sub-header">{selected_menu}</h3>', unsafe_allow_html=True)

    # ====================== ROUTING ======================
    if "Dashboard" in selected_menu:
        display_dashboard()

    elif "Medicines" in selected_menu:
        display_medicines()

    elif "Sales" in selected_menu:
        display_sales()

    elif "Reports" in selected_menu:
        display_reports(finance=("Finance" in selected_menu))

    elif "Alerts" in selected_menu:
        display_alerts()

    elif "Users" in selected_menu:
        if st.session_state.user_role in ["admin", "manager"]:
            display_users()
        else:
            st.warning("⛔ You don't have permission to access this section")

    elif "Search" in selected_menu:
        display_search_only()


# ====================== SECTIUNI ======================

def display_dashboard():
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        df = DatabaseHelper.get_dataframe("SELECT COUNT(*) AS c FROM medicines_info")
        total_meds = int(df.iloc[0]["c"]) if not df.empty else 0
        st.markdown(f"""
        <div class="metric-card">
        <h3>📦</h3>
        <h2>{total_meds}</h2>
        <p>Total Medicines</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        df = DatabaseHelper.get_dataframe(
            "SELECT COUNT(*) AS c FROM medicines_info WHERE Qty <= ?",
            [Config.LOW_STOCK_THRESHOLD]
        )
        low_stock = int(df.iloc[0]["c"]) if not df.empty else 0
        st.markdown(f"""
        <div class="metric-card">
        <h3>⚠️</h3>
        <h2>{low_stock}</h2>
        <p>Low Stock Items (≤ {Config.LOW_STOCK_THRESHOLD})</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        df = DatabaseHelper.get_dataframe(
            "SELECT COALESCE(SUM(total),0) AS s FROM sales WHERE date(sale_date)=date('now')"
        )
        today_sales = float(df.iloc[0]["s"]) if not df.empty else 0.0
        st.markdown(f"""
        <div class="metric-card">
        <h3>💰</h3>
        <h2>${today_sales:.2f}</h2>
        <p>Today's Sales</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        df = DatabaseHelper.get_dataframe(
            """
            SELECT COUNT(*) AS c
            FROM medicines_info
            WHERE Exp IS NOT NULL AND Exp != ''
              AND date(Exp) BETWEEN date('now') AND date('now','+30 day')
            """
        )
        expiring = int(df.iloc[0]["c"]) if not df.empty else 0
        st.markdown(f"""
        <div class="metric-card">
        <h3>📅</h3>
        <h2>{expiring}</h2>
        <p>Expiring Soon (30 days)</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Stock Overview")
        df = DatabaseHelper.get_dataframe("""
            SELECT
                CASE
                    WHEN Purpose IS NULL OR Purpose='' THEN 'Unspecified'
                    ELSE Purpose
                END AS GroupKey,
                COUNT(*) AS count
            FROM medicines_info
            GROUP BY GroupKey
            ORDER BY count DESC
            LIMIT 10
        """)
        if not df.empty:
            fig = px.pie(df, values="count", names="GroupKey")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available")

    with col2:
        st.subheader("📈 Sales Trend (Last 7 Days)")
        df = DatabaseHelper.get_dataframe("""
            SELECT date(sale_date) AS date, SUM(total) AS sales
            FROM sales
            WHERE date(sale_date) >= date('now','-7 day')
            GROUP BY date(sale_date)
            ORDER BY date
        """)
        if not df.empty:
            fig = px.line(df, x="date", y="sales", markers=True, title="Daily Sales")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales data for the last 7 days")

    st.subheader("🕐 Recent Activities")
    tab1, tab2 = st.tabs(["Recent Sales", "Recent Medicines"])

    with tab1:
        df = DatabaseHelper.get_dataframe("""
            SELECT s.sale_date, m.Med_name, s.quantity, s.total
            FROM sales s
            JOIN medicines_info m ON s.medicine_code = m.Med_code
            ORDER BY s.sale_date DESC
            LIMIT 10
        """)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No recent sales")

    with tab2:
        # SQLite nu are Created_at la medicines_info (și nu vrem să adăugăm).
        # Așa că afișăm cele mai noi după ROWID (aprox. ordinea inserării).
        df = DatabaseHelper.get_dataframe("""
            SELECT Med_name, Qty, MRP, Exp
            FROM medicines_info
            ORDER BY rowid DESC
            LIMIT 10
        """)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No medicines in database")


def display_medicines():
    st.subheader("📦 Medicine Management")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 View All", "➕ Add New", "🔍 Search", "⚠️ Low Stock"])

    # View All
    with tab1:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()

            export_format = st.selectbox("Export as", ["CSV"])
            if st.button("📥 Export Data", use_container_width=True):
                df = DatabaseHelper.get_dataframe("SELECT * FROM medicines_info ORDER BY Med_name")
                if not df.empty:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="medicines.csv",
                        mime="text/csv"
                    )

        df = DatabaseHelper.get_dataframe("SELECT * FROM medicines_info ORDER BY Med_name")
        if not df.empty:
            st.dataframe(df, use_container_width=True, height=420)

            total_value = (df["Qty"] * df["MRP"]).sum() if "Qty" in df.columns and "MRP" in df.columns else 0
            avg_price = df["MRP"].mean() if "MRP" in df.columns else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Medicines", len(df))
            c2.metric("Total Inventory Value", f"${total_value:,.2f}")
            c3.metric("Average Price", f"${avg_price:.2f}")
        else:
            st.info("No medicines found in database")

    # Add New
    with tab2:
        with st.form("add_medicine_form"):
            col1, col2 = st.columns(2)

            with col1:
                med_code = st.text_input("Medicine Code *", help="Unique code for the medicine")
                med_name = st.text_input("Medicine Name *")
                quantity = st.number_input("Quantity *", min_value=0, value=10)
                mrp = st.number_input("MRP (Price) *", min_value=0.0, value=0.0, format="%.2f")

            with col2:
                mfg_date = st.date_input("Manufacturing Date", value=datetime.now().date())
                exp_date = st.date_input("Expiry Date *", value=(datetime.now() + timedelta(days=365)).date())
                purpose = st.text_area("Purpose")

            submitted = st.form_submit_button("💾 Save Medicine", use_container_width=True)

            if submitted:
                if not med_code or not med_name or mrp <= 0:
                    st.error("Please fill all required fields (*) and MRP > 0")
                else:
                    try:
                        insert = """
                            INSERT INTO medicines_info (Med_code, Med_name, Qty, MRP, Mfg, Exp, Purpose)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """
                        DatabaseHelper.execute(insert, [
                            med_code.strip(),
                            med_name.strip(),
                            int(quantity),
                            float(mrp),
                            str(mfg_date),
                            str(exp_date),
                            (purpose or "").strip()
                        ])
                        st.success(f"✅ Medicine '{med_name}' added successfully!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ Failed to add medicine: {e}")

    # Search
    with tab3:
        col1, col2 = st.columns([1, 3])

        with col1:
            search_by = st.selectbox("Search by", ["Name", "Code", "Purpose"])
            search_term = st.text_input("Search term")

        with col2:
            if search_term:
                if search_by == "Name":
                    query = "SELECT * FROM medicines_info WHERE Med_name LIKE ? ORDER BY Med_name"
                elif search_by == "Code":
                    query = "SELECT * FROM medicines_info WHERE Med_code LIKE ? ORDER BY Med_name"
                else:
                    query = "SELECT * FROM medicines_info WHERE Purpose LIKE ? ORDER BY Med_name"

                df = DatabaseHelper.get_dataframe(query, [f"%{search_term}%"])
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    st.info(f"Found {len(df)} results")
                else:
                    st.warning("No results found")
            else:
                st.info("Enter a search term to find medicines")

    # Low Stock
    with tab4:
        df = DatabaseHelper.get_dataframe("""
            SELECT Med_code, Med_name, Qty, MRP, Exp, Purpose
            FROM medicines_info
            WHERE Qty <= ?
            ORDER BY Qty ASC
        """, [Config.LOW_STOCK_THRESHOLD])

        if not df.empty:
            st.markdown(f"### ⚠️ Low Stock Alert ({len(df)} items)")
            st.dataframe(df, use_container_width=True)

            total_order_qty = int((Config.LOW_STOCK_THRESHOLD - df["Qty"]).clip(lower=0).sum())
            est_value = float(((Config.LOW_STOCK_THRESHOLD - df["Qty"]).clip(lower=0) * df["MRP"]).sum())

            c1, c2 = st.columns(2)
            c1.metric("Suggested Total to Order", f"{total_order_qty} units")
            c2.metric("Estimated Cost (MRP-based)", f"${est_value:.2f}")
        else:
            st.success("🎉 No low stock items!")


def display_sales():
    st.subheader("💰 Sales Management")

    tab1, tab2 = st.tabs(["🛒 New Sale", "📋 Sales History"])

    # New Sale
    with tab1:
        with st.form("new_sale_form"):
            col1, col2 = st.columns([2, 1])

            selected_med = None
            total = 0.0
            quantity = 0

            with col1:
                dfm = DatabaseHelper.get_dataframe("""
                    SELECT Med_code, Med_name, MRP, Qty
                    FROM medicines_info
                    WHERE Qty > 0
                    ORDER BY Med_name
                """)

                if not dfm.empty:
                    options = {f"{r.Med_name} (Stock: {r.Qty})": r for r in dfm.itertuples(index=False)}
                    selected_display = st.selectbox("Select Medicine", options=list(options.keys()))
                    selected_med = options[selected_display]

                    st.info(f"Price: ${float(selected_med.MRP):.2f} | Available: {int(selected_med.Qty)} units")

                    quantity = st.number_input(
                        "Quantity",
                        min_value=1,
                        max_value=int(selected_med.Qty),
                        value=1
                    )

                    total = float(quantity) * float(selected_med.MRP)
                    st.metric("Total Amount", f"${total:.2f}")
                else:
                    st.warning("⚠️ No medicines in stock!")

            with col2:
                st.markdown("### Sale Details")
                customer_name = st.text_input("Customer Name", value="Walk-in Customer")
                payment_method = st.selectbox("Payment Method", ["Cash", "Card", "Insurance"])
                discount = st.number_input("Discount ($)", min_value=0.0, value=0.0, format="%.2f")

                final_total = max(0.0, total - float(discount))
                if discount > 0:
                    st.metric("Final Total", f"${final_total:.2f}")

            submitted = st.form_submit_button("💳 Process Sale", use_container_width=True)

            if submitted:
                if selected_med is None:
                    st.error("No medicine selected!")
                elif quantity <= 0:
                    st.error("Quantity must be greater than 0!")
                else:
                    # tranzacție "manuală" pe SQLite: verificare + update + insert
                    # 1) verificăm stocul actual (anti-race)
                    dfcheck = DatabaseHelper.get_dataframe(
                        "SELECT Qty FROM medicines_info WHERE Med_code = ?",
                        [selected_med.Med_code]
                    )
                    if dfcheck.empty:
                        st.error("Medicine not found!")
                        return
                    current_qty = int(dfcheck.iloc[0]["Qty"])
                    if current_qty < int(quantity):
                        st.error(f"Not enough stock. Available: {current_qty}")
                        return

                    # 2) scădem stoc
                    upd = DatabaseHelper.execute(
                        "UPDATE medicines_info SET Qty = Qty - ? WHERE Med_code = ?",
                        [int(quantity), selected_med.Med_code]
                    )
                    if upd == 0:
                        st.error("Failed to update stock.")
                        return

                    # 3) inserăm vânzarea
                    DatabaseHelper.execute("""
                        INSERT INTO sales (medicine_code, quantity, sale_price, total, cashier_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, [
                        selected_med.Med_code,
                        int(quantity),
                        float(selected_med.MRP),
                        float(final_total),
                        int(st.session_state.user_id)
                    ])

                    # 4) luăm sale_id-ul ultimei vânzări (SQLite)
                    dfid = DatabaseHelper.get_dataframe("SELECT last_insert_rowid() AS id")
                    sale_id = int(dfid.iloc[0]["id"]) if not dfid.empty else 0

                    receipt = f"""
╔══════════════════════════════════════════╗
║         PHARMACY RECEIPT                 ║
╠══════════════════════════════════════════╣
║ Receipt #: {sale_id:^30} ║
║ Date: {datetime.now().strftime('%Y-%m-%d %H:%M'):^26} ║
╠══════════════════════════════════════════╣
║ Medicine: {str(selected_med.Med_name):<27} ║
║ Quantity: {int(quantity):<26} ║
║ Price: ${float(selected_med.MRP):<28.2f} ║
╠══════════════════════════════════════════╣
║ Subtotal: ${total:<27.2f} ║
║ Discount: ${float(discount):<27.2f} ║
║ Final Total: ${float(final_total):<24.2f} ║
╠══════════════════════════════════════════╣
║ Customer: {customer_name:<25} ║
║ Payment: {payment_method:<26} ║
║ Cashier: {st.session_state.user_name:<25} ║
╚══════════════════════════════════════════╝
"""

                    st.success("✅ Sale processed successfully!")
                    st.balloons()
                    st.code(receipt, language=None)

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🖨️ Print Receipt"):
                            st.info("Receipt sent to printer (demo)")
                    with c2:
                        st.download_button(
                            label="📥 Download Receipt",
                            data=receipt,
                            file_name=f"receipt_{sale_id}.txt",
                            mime="text/plain"
                        )

    # Sales History
    with tab2:
        col1, col2, col3 = st.columns(3)

        with col1:
            date_filter = st.date_input("Filter by Date", value=datetime.now().date())
        with col2:
            period = st.selectbox("Period", ["Today", "This Week", "This Month", "All Time"])
        with col3:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

        if period == "Today":
            where_clause = "WHERE date(s.sale_date) = ?"
            params = [str(date_filter)]
        elif period == "This Week":
            where_clause = "WHERE date(s.sale_date) >= date('now','-7 day')"
            params = []
        elif period == "This Month":
            where_clause = "WHERE strftime('%Y-%m', s.sale_date) = strftime('%Y-%m','now')"
            params = []
        else:
            where_clause = ""
            params = []

        query = f"""
            SELECT s.sale_id, s.sale_date, m.Med_name, s.quantity,
                   s.sale_price, s.total
            FROM sales s
            JOIN medicines_info m ON s.medicine_code = m.Med_code
            {where_clause}
            ORDER BY s.sale_date DESC
        """
        df = DatabaseHelper.get_dataframe(query, params)

        if not df.empty:
            st.dataframe(df, use_container_width=True, height=400)

            total_sales = df["total"].sum()
            avg_sale = df["total"].mean()
            total_items = df["quantity"].sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Sales", f"${total_sales:.2f}")
            c2.metric("Average Sale", f"${avg_sale:.2f}")
            c3.metric("Items Sold", int(total_items))

            st.subheader("📈 Sales Trend")
            df["sale_date"] = pd.to_datetime(df["sale_date"])
            df["date"] = df["sale_date"].dt.date
            daily_sales = df.groupby("date")["total"].sum().reset_index()
            if not daily_sales.empty:
                fig = px.line(daily_sales, x="date", y="total", title="Daily Sales Trend", markers=True)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales records found for the selected period")


def display_reports(finance=False):
    st.subheader("📈 Reports & Analytics")

    report_type = st.selectbox(
        "Select Report Type",
        ["Daily Sales Report", "Monthly Summary", "Inventory Report", "Top Selling Products", "Financial Summary"]
    )

    if report_type == "Daily Sales Report":
        date = st.date_input("Select Date", value=datetime.now().date())

        if st.button("Generate Report", use_container_width=True):
            df = DatabaseHelper.get_dataframe("""
                SELECT s.sale_date, m.Med_name, s.quantity, s.sale_price, s.total
                FROM sales s
                JOIN medicines_info m ON s.medicine_code = m.Med_code
                WHERE date(s.sale_date) = ?
                ORDER BY s.sale_date
            """, [str(date)])

            if not df.empty:
                total_sales = df["total"].sum()
                total_items = df["quantity"].sum()
                avg_sale = df["total"].mean()

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Sales", f"${total_sales:.2f}")
                c2.metric("Items Sold", int(total_items))
                c3.metric("Average Sale", f"${avg_sale:.2f}")

                st.subheader("📋 Detailed Sales")
                st.dataframe(df, use_container_width=True)

                st.subheader("🏆 Top Products of the Day")
                top_products = df.groupby("Med_name")["quantity"].sum().nlargest(5)
                fig = px.bar(x=top_products.index, y=top_products.values,
                             title="Top 5 Products by Quantity",
                             labels={'x': 'Product', 'y': 'Quantity Sold'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No sales recorded on {date}")

    elif report_type == "Monthly Summary":
        months = pd.date_range(end=datetime.now(), periods=12, freq="ME").strftime("%Y-%m").tolist()
        month = st.selectbox("Select Month", months)

        if st.button("Generate Monthly Report", use_container_width=True):
            df = DatabaseHelper.get_dataframe("""
                SELECT
                    date(s.sale_date) as date,
                    COUNT(DISTINCT s.sale_id) as transactions,
                    SUM(s.quantity) as items_sold,
                    SUM(s.total) as daily_total
                FROM sales s
                WHERE strftime('%Y-%m', s.sale_date) = ?
                GROUP BY date(s.sale_date)
                ORDER BY date
            """, [month])

            if not df.empty:
                total_revenue = df["daily_total"].sum()
                total_transactions = df["transactions"].sum()
                total_items = df["items_sold"].sum()
                avg_daily = df["daily_total"].mean()

                st.subheader(f"📅 Monthly Report - {month}")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Revenue", f"${total_revenue:.2f}")
                c2.metric("Transactions", int(total_transactions))
                c3.metric("Items Sold", int(total_items))
                c4.metric("Avg Daily", f"${avg_daily:.2f}")

                fig = px.line(df, x="date", y="daily_total", title="Daily Revenue Trend", markers=True)
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(df, use_container_width=True)
            else:
                st.info(f"No data available for {month}")

    elif report_type == "Inventory Report":
        df = DatabaseHelper.get_dataframe("""
            SELECT
                CASE WHEN Purpose IS NULL OR Purpose='' THEN 'Unspecified' ELSE Purpose END as GroupKey,
                COUNT(*) as count,
                SUM(Qty) as total_qty,
                AVG(MRP) as avg_price,
                SUM(Qty * MRP) as total_value
            FROM medicines_info
            GROUP BY GroupKey
            ORDER BY total_value DESC
        """)
        if not df.empty:
            st.subheader("📦 Inventory Overview (grouped by Purpose)")

            fig1 = px.pie(df, values="total_value", names="GroupKey", title="Inventory Value by Purpose")
            st.plotly_chart(fig1, use_container_width=True)

            fig2 = px.bar(df, x="GroupKey", y="total_qty", title="Stock Quantity by Purpose")
            st.plotly_chart(fig2, use_container_width=True)

            st.dataframe(df, use_container_width=True)

            total_value = df["total_value"].sum()
            total_items = df["total_qty"].sum()
            c1, c2 = st.columns(2)
            c1.metric("Total Inventory Value", f"${total_value:,.2f}")
            c2.metric("Total Items in Stock", f"{int(total_items):,}")
        else:
            st.info("No inventory data available")

    elif report_type == "Top Selling Products":
        period = st.selectbox("Time Period", ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"])

        if period == "Last 7 Days":
            where_clause = "WHERE date(s.sale_date) >= date('now','-7 day')"
        elif period == "Last 30 Days":
            where_clause = "WHERE date(s.sale_date) >= date('now','-30 day')"
        elif period == "Last 90 Days":
            where_clause = "WHERE date(s.sale_date) >= date('now','-90 day')"
        else:
            where_clause = ""

        df = DatabaseHelper.get_dataframe(f"""
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
        """)

        if not df.empty:
            st.subheader(f"🏆 Top 10 Products - {period}")

            fig1 = px.bar(df, x="Med_name", y="total_revenue", title="Top Products by Revenue")
            st.plotly_chart(fig1, use_container_width=True)

            fig2 = px.bar(df, x="Med_name", y="total_quantity", title="Top Products by Quantity Sold")
            st.plotly_chart(fig2, use_container_width=True)

            st.dataframe(df, use_container_width=True)
        else:
            st.info("No sales data for selected period")

    elif report_type == "Financial Summary":
        df_total = DatabaseHelper.get_dataframe("SELECT COALESCE(SUM(total),0) AS s FROM sales")
        total_sales = float(df_total.iloc[0]["s"]) if not df_total.empty else 0.0

        df_today = DatabaseHelper.get_dataframe(
            "SELECT COALESCE(SUM(total),0) AS s FROM sales WHERE date(sale_date)=date('now')"
        )
        today_sales = float(df_today.iloc[0]["s"]) if not df_today.empty else 0.0

        df_inv = DatabaseHelper.get_dataframe("SELECT COALESCE(SUM(Qty * MRP),0) AS v FROM medicines_info")
        inventory_value = float(df_inv.iloc[0]["v"]) if not df_inv.empty else 0.0

        df_cnt = DatabaseHelper.get_dataframe("SELECT COUNT(*) AS c FROM medicines_info")
        product_count = int(df_cnt.iloc[0]["c"]) if not df_cnt.empty else 0

        st.subheader("💰 Financial Summary")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Sales (All Time)", f"${total_sales:,.2f}")
        c2.metric("Today's Sales", f"${today_sales:,.2f}")
        c3.metric("Inventory Value", f"${inventory_value:,.2f}")
        c4.metric("Products in Stock", product_count)

        df = DatabaseHelper.get_dataframe("""
            SELECT strftime('%Y-%m', sale_date) as month,
                   SUM(total) as monthly_sales,
                   COUNT(*) as transactions
            FROM sales
            GROUP BY strftime('%Y-%m', sale_date)
            ORDER BY month DESC
            LIMIT 6
        """)
        if not df.empty:
            fig = px.line(df, x="month", y="monthly_sales",
                          title="Monthly Sales Trend (Last 6 Months)", markers=True)
            st.plotly_chart(fig, use_container_width=True)


def display_alerts():
    st.subheader("🚨 System Alerts & Notifications")

    tab1, tab2, tab3 = st.tabs(["⚠️ Low Stock", "📅 Expiry Alerts", "🔔 All Notifications"])

    with tab1:
        df = DatabaseHelper.get_dataframe("""
            SELECT Med_code, Med_name, Qty, MRP, Exp
            FROM medicines_info
            WHERE Qty <= ?
            ORDER BY Qty ASC
        """, [Config.LOW_STOCK_THRESHOLD])

        if not df.empty:
            st.markdown(f"### ⚠️ Low Stock Alerts ({len(df)} items)")
            st.dataframe(df, use_container_width=True)

            need_to_order = (Config.LOW_STOCK_THRESHOLD - df["Qty"]).clip(lower=0)
            total_to_order = int(need_to_order.sum())
            est_cost = float((need_to_order * df["MRP"]).sum())

            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.metric("Total Units to Order", total_to_order)
            c2.metric("Estimated Cost (MRP-based)", f"${est_cost:.2f}")
        else:
            st.success("🎉 No low stock alerts!")

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            df_expired = DatabaseHelper.get_dataframe("""
                SELECT Med_code, Med_name, Exp, Qty, MRP
                FROM medicines_info
                WHERE Exp IS NOT NULL AND Exp != ''
                  AND date(Exp) < date('now')
                  AND Qty > 0
                ORDER BY date(Exp) ASC
            """)
            if not df_expired.empty:
                st.markdown(f"### ❌ Expired ({len(df_expired)})")
                for _, row in df_expired.iterrows():
                    st.error(f"**{row['Med_name']}** - Expired: {row['Exp']} | Stock: {row['Qty']}")
            else:
                st.success("✅ No expired medicines!")

        with col2:
            df_expiring = DatabaseHelper.get_dataframe("""
                SELECT Med_code, Med_name, Exp, Qty, MRP,
                       CAST(julianday(Exp) - julianday(date('now')) AS INTEGER) as days_left
                FROM medicines_info
                WHERE Exp IS NOT NULL AND Exp != ''
                  AND date(Exp) BETWEEN date('now') AND date('now','+30 day')
                ORDER BY date(Exp) ASC
            """)
            if not df_expiring.empty:
                st.markdown(f"### ⏰ Expiring Soon ({len(df_expiring)})")
                for _, row in df_expiring.iterrows():
                    days_left = int(row["days_left"])
                    st.warning(f"**{row['Med_name']}** - {days_left} days left | Expires: {row['Exp']} | Stock: {row['Qty']}")
            else:
                st.success("✅ No medicines expiring soon!")

    with tab3:
        alerts = []

        df_low = DatabaseHelper.get_dataframe(
            "SELECT Med_name, Qty FROM medicines_info WHERE Qty <= ?",
            [Config.LOW_STOCK_THRESHOLD]
        )
        for _, row in df_low.iterrows():
            alerts.append({
                "priority": "high",
                "icon": "⚠️",
                "medicine": row["Med_name"],
                "message": f"Low stock: {row['Qty']}/{Config.LOW_STOCK_THRESHOLD}"
            })

        df_expired = DatabaseHelper.get_dataframe("""
            SELECT Med_name, Exp
            FROM medicines_info
            WHERE Exp IS NOT NULL AND Exp != ''
              AND date(Exp) < date('now')
              AND Qty > 0
        """)
        for _, row in df_expired.iterrows():
            alerts.append({
                "priority": "critical",
                "icon": "❌",
                "medicine": row["Med_name"],
                "message": f"Expired on {row['Exp']}"
            })

        df_expiring = DatabaseHelper.get_dataframe("""
            SELECT Med_name, Exp
            FROM medicines_info
            WHERE Exp IS NOT NULL AND Exp != ''
              AND date(Exp) BETWEEN date('now') AND date('now','+30 day')
        """)
        for _, row in df_expiring.iterrows():
            try:
                days_left = (pd.to_datetime(row["Exp"]).date() - datetime.now().date()).days
            except:
                days_left = 0
            alerts.append({
                "priority": "medium" if days_left > 7 else "high",
                "icon": "⏰",
                "medicine": row["Med_name"],
                "message": f"Expires in {days_left} days"
            })

        if alerts:
            st.markdown(f"### 🔔 All Notifications ({len(alerts)})")
            priority_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}
            alerts.sort(key=lambda x: priority_order.get(x["priority"], 5))

            for a in alerts:
                if a["priority"] == "critical":
                    st.error(f"{a['icon']} **CRITICAL**: {a['medicine']} - {a['message']}")
                elif a["priority"] == "high":
                    st.warning(f"{a['icon']} **HIGH**: {a['medicine']} - {a['message']}")
                else:
                    st.info(f"{a['icon']} **MEDIUM**: {a['medicine']} - {a['message']}")
        else:
            st.success("🎉 No notifications! All systems are normal.")


def display_users():
    st.subheader("👥 User Management")

    tab1, tab2 = st.tabs(["View Users", "Add New User"])

    with tab1:
        df = DatabaseHelper.get_dataframe("""
            SELECT id, username, full_name, role, email, created_at
            FROM users
            ORDER BY role, username
        """)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            role_counts = df["role"].value_counts()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Users", len(df))
            c2.metric("Admins", int(role_counts.get("admin", 0)))
            c3.metric("Pharmacists", int(role_counts.get("pharmacist", 0)))
            c4.metric("Cashiers", int(role_counts.get("cashier", 0)))
        else:
            st.info("No users found")

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
                if not username or not password or not full_name or not role:
                    st.error("Please fill all required fields (*)")
                elif password != confirm_password:
                    st.error("Passwords do not match!")
                else:
                    dfc = DatabaseHelper.get_dataframe("SELECT id FROM users WHERE username = ? LIMIT 1", [username])
                    if not dfc.empty:
                        st.error("Username already exists!")
                    else:
                        DatabaseHelper.execute("""
                            INSERT INTO users (username, password, full_name, email, role)
                            VALUES (?, ?, ?, ?, ?)
                        """, [username, password, full_name, email, role])
                        st.success(f"✅ User '{username}' added successfully!")


def display_search_only():
    st.subheader("🔍 Quick Search")
    search_by = st.selectbox("Search by", ["Name", "Code", "Purpose"])
    term = st.text_input("Search term")
    if term:
        if search_by == "Name":
            q = "SELECT * FROM medicines_info WHERE Med_name LIKE ? ORDER BY Med_name"
        elif search_by == "Code":
            q = "SELECT * FROM medicines_info WHERE Med_code LIKE ? ORDER BY Med_name"
        else:
            q = "SELECT * FROM medicines_info WHERE Purpose LIKE ? ORDER BY Med_name"

        df = DatabaseHelper.get_dataframe(q, [f"%{term}%"])
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No results found")
    else:
        st.info("Enter a search term.")


# ====================== RULARE APLICAȚIE ======================
if __name__ == "__main__":
    main()
