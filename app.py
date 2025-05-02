import base64
import hashlib
import locale
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from ics import Calendar, Event

st.set_page_config(layout="wide")


# ---------- CONFIG ----------
ROOMS_BY_FLOOR = {
    "1.OG": [f"Bibliothek / {i:03d} / 1.OG" for i in range(1, 228)],
    "EG":   [f"Bibliothek / {i:03d} /   EG" for i in range(1, 182)],
}
ALL_ROOMS = sum(ROOMS_BY_FLOOR.values(), [])

try:
    locale.setlocale(locale.LC_TIME, "de_CH.UTF-8")
except:  # noqa: E722
    pass

# ---------- DATABASE ----------
DB_PATH = "users.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT
)""")
c.execute("""CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    seat TEXT NOT NULL
)""")
conn.commit()

# ---------- SESSION ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "full_name" not in st.session_state:
    st.session_state.full_name = None
if "reservation_time" not in st.session_state:
    st.session_state.reservation_time = datetime.now().time()


# ---------- AUTH ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def load_user_reservations(username):
    df = pd.read_sql(
        "SELECT * FROM reservations WHERE username = ?", conn, params=(username,)
    )
    return df.to_dict(orient="records")


def delete_reservation_by_id(res_id):
    c.execute("DELETE FROM reservations WHERE id = ?", (res_id,))
    conn.commit()


if not st.session_state.logged_in:
    auth_action = st.sidebar.radio("Authentifizierung", ["Login", "Registrieren"])

    if auth_action == "Login":
        email = st.sidebar.text_input("Studenten-E-Mail")
        password = st.sidebar.text_input("Passwort", type="password")
        if st.sidebar.button("Einloggen"):
            c.execute(
                "SELECT password, role, first_name, last_name FROM users WHERE email = ?",
                (email,),
            )
            result = c.fetchone()
            if result and hash_password(password) == result[0]:
                st.session_state.logged_in = True
                st.session_state.username = email
                st.session_state.user_role = result[1]
                st.session_state.full_name = f"{result[2]} {result[3]}"
                st.rerun()
            else:
                st.error(
                    "Login fehlgeschlagen. Bitte überprüfen Sie Ihre Anmeldedaten."
                )

    elif auth_action == "Registrieren":
        new_email = st.sidebar.text_input("Neue E-Mail")
        first_name = st.sidebar.text_input("Vorname")
        last_name = st.sidebar.text_input("Nachname")
        new_password = st.sidebar.text_input("Neues Passwort", type="password")
        role = st.sidebar.selectbox("Rolle", ["Student", "Admin"])
        if st.sidebar.button("Registrieren"):
            try:
                c.execute(
                    "INSERT INTO users (email, password, role, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                    (
                        new_email,
                        hash_password(new_password),
                        role,
                        first_name,
                        last_name,
                    ),
                )
                conn.commit()
                st.success("Registrierung erfolgreich. Sie können sich nun einloggen.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Diese E-Mail ist bereits registriert.")

if not st.session_state.logged_in:
    st.warning("Bitte melden Sie sich an, um fortzufahren.")
    st.stop()

# ---------- APP ----------
username = st.session_state.username
is_admin = st.session_state.user_role == "Admin"
full_name = st.session_state.full_name

st.sidebar.markdown(f"👤 Eingeloggt als: {full_name} ({st.session_state.user_role})")
if st.sidebar.button("🚪 Abmelden"):
    for key in ["logged_in", "username", "user_role", "full_name"]:
        st.session_state[key] = None
    st.session_state.logged_in = False
    st.rerun()

main_menu = ["Tisch reservieren", "Meine Reservierungen", "Reservierungsübersicht"]
if is_admin:
    main_menu.append("Admin Dashboard")
menu = st.sidebar.radio("Menü", main_menu)

if menu == "Admin Dashboard" and is_admin:
    st.header("📊 Admin Dashboard")
    all_users = pd.read_sql(
        "SELECT email, role, first_name, last_name FROM users", conn
    )
    st.subheader("Benutzerliste")
    st.dataframe(all_users, use_container_width=True)
    all_res = pd.read_sql("SELECT * FROM reservations", conn)
    st.subheader("Alle Reservierungen")
    st.dataframe(all_res, use_container_width=True)

elif menu == "Tisch reservieren":
    st.header("Tisch reservieren")
    reservation_date = st.date_input("Datum auswählen")
    reservation_time = st.time_input(
        "Startzeit", value=st.session_state.reservation_time
    )
    st.session_state.reservation_time = reservation_time
    duration = st.number_input("Dauer (Stunden)", 1, 8, 1)
    seat_number = st.selectbox("Platznummer", ALL_ROOMS)

    if st.button("Reservieren"):
        end_time = (
            datetime.combine(datetime.today(), reservation_time)
            + timedelta(hours=duration)
        ).time()
        c.execute(
            """
            INSERT INTO reservations (username, date, start_time, end_time, seat)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                username,
                str(reservation_date),
                str(reservation_time),
                str(end_time),
                seat_number,
            ),
        )
        conn.commit()
        st.success(
            f"Reservierung erfolgreich: {reservation_date}, {reservation_time} - {end_time}, {seat_number}"
        )

elif menu == "Meine Reservierungen":
    st.header("Meine Reservierungen")
    user_res = load_user_reservations(username)

    for idx, res in enumerate(user_res):
        st.write(
            f"{res['date']} {res['start_time']} - {res['end_time']} @ {res['seat']}"
        )
        if (
            datetime.now().date().isoformat() == res["date"]
            and res["start_time"]
            <= datetime.now().time().isoformat()
            <= res["end_time"]
        ):
            if st.button("Frühzeitig beenden", key=f"end_{idx}"):
                delete_reservation_by_id(res["id"])
                st.warning("Reservierung wurde beendet.")
                st.rerun()
        elif datetime.now().date().isoformat() < res["date"]:
            if st.button("Stornieren", key=f"cancel_{idx}"):
                delete_reservation_by_id(res["id"])
                st.warning("Reservierung storniert.")
                st.rerun()

    if st.button("Als Kalenderdatei exportieren"):
        calendar = Calendar()
        for res in user_res:
            e = Event()
            e.name = f"Bibliotheksplatz: {res['seat']}"
            e.begin = f"{res['date']}T{res['start_time']}"
            e.end = f"{res['date']}T{res['end_time']}"
            e.location = res["seat"]
            calendar.events.add(e)
        ics_content = str(calendar)
        b64 = base64.b64encode(ics_content.encode()).decode()
        href = f'<a href="data:text/calendar;base64,{b64}" download="meine_reservierungen.ics">ICS-Datei herunterladen</a>'
        st.markdown(href, unsafe_allow_html=True)

elif menu == "Reservierungsübersicht":
    st.header("Reservierungsübersicht")
    today = datetime.now().date()
    selected_day = st.selectbox(
        "Tag auswählen",
        [today + timedelta(days=i) for i in range(7)],
        format_func=lambda d: d.strftime("%A, %d. %B %Y"),
    )
    start_hour, end_hour = 8, 22
    grid_data = []

    all_res = pd.read_sql(
        "SELECT * FROM reservations WHERE date = ?", conn, params=(str(selected_day),)
    )

    for room in ALL_ROOMS:
        for hour in range(start_hour, end_hour + 1):
            slot_time = datetime.combine(selected_day, datetime.min.time()) + timedelta(
                hours=hour
            )
            status = "Verfügbar"
            for _, res in all_res.iterrows():
                if (
                    res["seat"] == room
                    and res["start_time"]
                    <= slot_time.time().isoformat()
                    < res["end_time"]
                ):
                    status = (
                        "Meine Reservierung"
                        if res["username"] == username
                        else "Reserviert"
                    )
                    break
            grid_data.append(
                {
                    "Raum": room,
                    "Zeit": f"{hour:02d}:00",
                    "Status": status,
                    "Datetime": slot_time,
                }
            )

    df = pd.DataFrame(grid_data)

    with st.expander("Direktbuchung (ein Slot klicken)"):
        col1, col2 = st.columns(2)
        for idx, row in df.iterrows():
            with col1 if idx % 2 == 0 else col2:
                if row["Status"] == "Verfügbar" or is_admin:
                    if st.button(
                        f"Buchen: {row['Raum']} - {row['Zeit']}", key=f"book_{idx}"
                    ):
                        end_time = (
                            (row["Datetime"] + timedelta(hours=1)).time().isoformat()
                        )
                        c.execute(
                            """
                            INSERT INTO reservations (username, date, start_time, end_time, seat)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                username,
                                str(selected_day),
                                row["Datetime"].time().isoformat(),
                                end_time,
                                row["Raum"],
                            ),
                        )
                        conn.commit()
                        st.success(
                            f"Reservierung erfolgreich für {row['Raum']} um {row['Zeit']}"
                        )
                        st.rerun()

    grid = df.pivot(index="Raum", columns="Zeit", values="Status")

    def color_map(val):
        return {
            "Verfügbar": "background-color: #d4edda; color: black;",
            "Reserviert": "background-color: #f8d7da; color: black;",
            "Meine Reservierung": "background-color: #c62121; color: black; font-weight: bold;",
        }.get(val, "")

    st.dataframe(grid.style.map(color_map), use_container_width=True, height=600)
    st.caption(
        "Farblegende: Verfügbar (grün), Reserviert (rot), Meine Reservierung (blau)"
    )
