import streamlit as st
import sqlite3
import pandas as pd
import datetime
import plotly.express as px

# ------------------ Database Setup ------------------ #
conn = sqlite3.connect("appointments.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT,
    email TEXT,
    service TEXT,
    date TEXT,
    time TEXT,
    status TEXT,
    created_at TEXT
)
''')
conn.commit()

# ------------------ Helper Functions ------------------ #
def add_appointment(client_name, email, service, date, time, status):
    c.execute('''INSERT INTO appointments 
                 (client_name, email, service, date, time, status, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (client_name, email, service, date, time, status,
               datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

def fetch_appointments():
    return pd.read_sql("SELECT * FROM appointments", conn)

def update_appointment(appt_id, status, date, time):
    c.execute("UPDATE appointments SET status=?, date=?, time=? WHERE id=?",
              (status, date, time, appt_id))
    conn.commit()

def delete_appointment(appt_id):
    c.execute("DELETE FROM appointments WHERE id=?", (appt_id,))
    conn.commit()

# ------------------ Streamlit UI ------------------ #
st.set_page_config(page_title="Appointment Scheduler", layout="wide")
st.title("📅 Appointment Scheduling, Reminders & Analytics")

tab1, tab2, tab3, tab4 = st.tabs([
    "Manage Appointments", 
    "View Appointments", 
    "Reminders", 
    "Analytics Dashboard"
])

# ------------------ Phase 1: Manage Appointments ------------------ #
with tab1:
    st.subheader("➕ Add New Appointment")
    with st.form("appointment_form"):
        client_name = st.text_input("Client Name")
        email = st.text_input("Client Email")
        service = st.text_input("Service Type")
        date = st.date_input("Appointment Date")
        time = st.time_input("Appointment Time")
        status = st.selectbox("Status", ["Scheduled", "Completed", "Cancelled"])
        submitted = st.form_submit_button("Add Appointment")

        if submitted and client_name and email:
            add_appointment(client_name, email, service,
                            date.strftime("%Y-%m-%d"),
                            time.strftime("%H:%M"),
                            status)
            st.success(f"✅ Appointment booked for {client_name} on {date} at {time}")

# ------------------ Phase 1: View & Manage Appointments ------------------ #
with tab2:
    st.subheader("📋 All Appointments")
    appt_df = fetch_appointments()
    if not appt_df.empty:
        st.dataframe(appt_df)

        appt_id = st.selectbox("Select Appointment ID to Update/Delete", appt_df["id"])
        new_status = st.selectbox("Update Status", ["Scheduled", "Completed", "Cancelled"])
        new_date = st.date_input("New Date", datetime.date.today())
        new_time = st.time_input("New Time", datetime.datetime.now().time())

        if st.button("Update Appointment"):
            update_appointment(appt_id, new_status,
                               new_date.strftime("%Y-%m-%d"),
                               new_time.strftime("%H:%M"))
            st.success("✅ Appointment updated!")

        if st.button("Delete Appointment"):
            delete_appointment(appt_id)
            st.warning("⚠️ Appointment deleted!")
    else:
        st.info("No appointments yet. Add one in the first tab.")

# ------------------ Phase 2: Automated Reminders ------------------ #
with tab3:
    st.subheader("⏰ Appointment Reminders")
    appt_df = fetch_appointments()
    if not appt_df.empty:
        appt_df["date"] = pd.to_datetime(appt_df["date"], errors="coerce")
        today = pd.to_datetime(datetime.date.today())

        # Today's appointments
        today_appts = appt_df[(appt_df["date"] == today) & (appt_df["status"] == "Scheduled")]

        # Missed appointments
        missed_appts = appt_df[(appt_df["date"] < today) & (appt_df["status"] == "Scheduled")]

        if not today_appts.empty:
            st.warning("📌 Appointments Scheduled for Today")
            st.table(today_appts[["id", "client_name", "email", "service", "time"]])

            st.markdown("### ✉️ Reminder Messages for Today")
            for _, row in today_appts.iterrows():
                reminder = f"Hello {row['client_name']}, this is a reminder for your appointment ({row['service']}) scheduled today at {row['time']}."
                st.info(reminder)

        if not missed_appts.empty:
            st.error("⚠️ Missed Appointments")
            st.table(missed_appts[["id", "client_name", "email", "service", "date", "time"]])

        if today_appts.empty and missed_appts.empty:
            st.success("🎉 No pending reminders today!")
    else:
        st.info("No appointments available for reminders.")

# ------------------ Phase 3: Analytics Dashboard ------------------ #
with tab4:
    st.subheader("📊 Appointment Analytics")
    appt_df = fetch_appointments()
    if not appt_df.empty:
        appt_df["date"] = pd.to_datetime(appt_df["date"], errors="coerce")

        # --- KPI Metrics ---
        total_appts = len(appt_df)
        completed = len(appt_df[appt_df["status"] == "Completed"])
        cancelled = len(appt_df[appt_df["status"] == "Cancelled"])
        scheduled = len(appt_df[appt_df["status"] == "Scheduled"])
        no_show = len(appt_df[(appt_df["status"] == "Scheduled") & (appt_df["date"] < datetime.date.today())])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📅 Total Appointments", total_appts)
        col2.metric("✅ Completed", completed)
        col3.metric("❌ Cancelled", cancelled)
        col4.metric("⚠️ No-shows", no_show)

        # --- Appointments per Month ---
        appt_df["month"] = appt_df["date"].dt.to_period("M").astype(str)
        month_counts = appt_df.groupby("month").size().reset_index(name="count")
        fig1 = px.bar(month_counts, x="month", y="count", title="Appointments per Month")
        st.plotly_chart(fig1, use_container_width=True)

        # --- Service Popularity ---
        service_counts = appt_df["service"].value_counts().reset_index()
        service_counts.columns = ["service", "count"]
        fig2 = px.pie(service_counts, values="count", names="service", title="Service Popularity")
        st.plotly_chart(fig2, use_container_width=True)

        # --- Status Breakdown ---
        status_counts = appt_df["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig3 = px.bar(status_counts, x="status", y="count", color="status", title="Status Breakdown")
        st.plotly_chart(fig3, use_container_width=True)

    else:
        st.info("No data available for analytics.")
