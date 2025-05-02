# 📚 Library Seat Reservation App

A simple Streamlit-based library seat reservation system with persistent user login, role-based access (Admin/Student), and room/time management.

---

## 🚀 Features

- 📅 Book and cancel library seat reservations
- 👥 Persistent login and user registration (SQLite)
- 🔐 Role-based: Students vs Admins
- 🛠 Admin dashboard with all reservations
- 📦 Exports reservations to .ics calendar
- 🖥 Responsive and modular interface

---

## 🛠 Installation Instructions

### 1. Install Miniconda (if you haven't already)

Download: https://docs.conda.io/en/latest/miniconda.html

### 2. Create environment with Python 3.12

```bash
conda create -n reserve python=3.12 -y
conda activate reserve
```

### 3. Install dependencies

```bash
pip install streamlit pandas ics
```

---

## 🧾 Usage

1. Run the app:
```bash
streamlit run app.py
```

2. Open in browser (usually at `http://localhost:8501`)

---

## 🗃 Data

- `users.db`: stores users and reservations
- `app.py`: main Streamlit application
- `README.md`: this file

---

## 👤 Roles

- **Student**: can register, book, and cancel their own reservations
- **Admin**: can see all users and all reservations, and make any booking

---

## 💡 Notes

- Admin and user info stored in `users.db`
- Works offline and persists reservations

## user.db
- email: student@example.com
- password: password123
- Press "login" instead of pressing "Enter" on the keyboard
