import os
import time
import joblib
import psycopg2
from flask import Flask, request, render_template

app = Flask(__name__)
model = joblib.load("model.pkl")
CLASSES = ["setosa", "versicolor", "virginica"]


def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        dbname=os.environ.get("DB_NAME", "mldb"),
        user=os.environ.get("DB_USER", "mluser"),
        password=os.environ.get("DB_PASS", "mlpass"),
    )


def init_db(retries=10):
    for i in range(retries):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    sepal_length REAL, sepal_width REAL,
                    petal_length REAL, petal_width REAL,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
            print("เชื่อมต่อฐานข้อมูลและสร้างตารางสำเร็จ")
            return
        except Exception as e:
            print(f"รอ db... ({i+1}) {e}")
            time.sleep(3)
    raise RuntimeError("เชื่อมต่อฐานข้อมูลไม่ได้")


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    form_values = {
        "sepal_length": 5.1,
        "sepal_width": 3.5,
        "petal_length": 1.4,
        "petal_width": 0.2,
    }

    if request.method == "POST":
        form_values = {
            "sepal_length": float(request.form["sepal_length"]),
            "sepal_width": float(request.form["sepal_width"]),
            "petal_length": float(request.form["petal_length"]),
            "petal_width": float(request.form["petal_width"]),
        }
        features = [
            form_values["sepal_length"],
            form_values["sepal_width"],
            form_values["petal_length"],
            form_values["petal_width"],
        ]
        pred = int(model.predict([features])[0])
        result = CLASSES[pred]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO predictions "
            "(sepal_length, sepal_width, petal_length, petal_width, result) "
            "VALUES (%s,%s,%s,%s,%s)",
            (*features, result),
        )
        conn.commit()
        cur.close()
        conn.close()

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT sepal_length, sepal_width, petal_length, petal_width, "
        "result, created_at FROM predictions ORDER BY id DESC LIMIT 10"
    )
    history = cur.fetchall()
    cur.close()
    conn.close()

    return render_template(
        "index.html", result=result, history=history, form_values=form_values
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
