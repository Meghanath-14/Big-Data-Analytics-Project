from pathlib import Path
from datetime import datetime
import io
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session

app = Flask(__name__)
app.secret_key = "railpulse-local-course-project"
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "dataset"
DEFAULT_DATA = DATA_DIR / "railway_ticket_booking.csv"
REQUIRED = ["Booking_ID","Booking_Date","Train_Name","Source","Destination","Class_Type","Number_of_Passengers","Ticket_Status","Ticket_Fare"]

def load_data():
    selected = session.get("uploaded_dataset")
    path = Path(selected) if selected else DEFAULT_DATA
    if not path.exists():
        raise FileNotFoundError("Dataset not found. Upload a CSV file.")
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError("Missing CSV columns: " + ", ".join(missing))
    df = df.drop_duplicates(subset=["Booking_ID"]).copy()
    df["Booking_Date"] = pd.to_datetime(df["Booking_Date"], errors="coerce")
    df["Ticket_Fare"] = pd.to_numeric(df["Ticket_Fare"], errors="coerce")
    median = df["Ticket_Fare"].median()
    df["Ticket_Fare"] = df["Ticket_Fare"].fillna(0 if pd.isna(median) else median)
    df["Number_of_Passengers"] = pd.to_numeric(df["Number_of_Passengers"], errors="coerce").fillna(1)
    df["Ticket_Status"] = df["Ticket_Status"].fillna("Unknown").astype(str).str.strip().str.title()
    df["Route"] = df["Source"].astype(str) + " - " + df["Destination"].astype(str)
    return df

def metrics(df):
    total = len(df)
    cancelled = int((df.Ticket_Status == "Cancelled").sum())
    return {
        "total": int(total),
        "passengers": int(df.Number_of_Passengers.sum()),
        "confirmed": int((df.Ticket_Status == "Confirmed").sum()),
        "waiting": int((df.Ticket_Status == "Waiting").sum()),
        "cancelled": cancelled,
        "cancel_rate": round(cancelled / total * 100, 2) if total else 0.0,
        "revenue": float(df.loc[df.Ticket_Status == "Confirmed", "Ticket_Fare"].sum()),
        "avg_fare": float(df.Ticket_Fare.mean()) if total else 0.0
    }

@app.route("/")
def dashboard():
    try:
        df = load_data()
        m = metrics(df)
        s = df.Ticket_Status.value_counts()
        t = df.Train_Name.value_counts().head(8)
        r = df.Route.value_counts().head(8)
        dated = df.dropna(subset=["Booking_Date"]).copy()
        mo = dated.groupby(dated.Booking_Date.dt.to_period("M")).size()
        rev = df[df.Ticket_Status == "Confirmed"].groupby("Train_Name").Ticket_Fare.sum().sort_values(ascending=False).head(8)
        return render_template(
            "dashboard.html", m=m,
            status_labels=[str(x) for x in s.index], status_values=[int(x) for x in s.values],
            train_labels=[str(x) for x in t.index], train_values=[int(x) for x in t.values],
            route_labels=[str(x) for x in r.index], route_values=[int(x) for x in r.values],
            month_labels=[str(x) for x in mo.index], month_values=[int(x) for x in mo.values],
            rev_labels=[str(x) for x in rev.index], rev_values=[float(x) for x in rev.values],
            dataset_name=Path(session.get("uploaded_dataset", str(DEFAULT_DATA))).name
        )
    except Exception as exc:
        return render_template("error.html", message=str(exc)), 500

@app.route("/upload", methods=["GET","POST"])
def upload():
    if request.method == "POST":
        f = request.files.get("dataset")
        if not f or not f.filename.lower().endswith(".csv"):
            flash("Please choose a CSV file.", "error")
            return redirect(url_for("upload"))
        DATA_DIR.mkdir(exist_ok=True)
        dest = DATA_DIR / ("uploaded_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".csv")
        f.save(dest)
        old = session.get("uploaded_dataset")
        session["uploaded_dataset"] = str(dest)
        try:
            check = load_data()
            if check.empty:
                raise ValueError("The uploaded dataset is empty.")
            flash(f"Successfully uploaded {len(check):,} records.", "success")
            return redirect(url_for("dashboard"))
        except Exception as exc:
            if old:
                session["uploaded_dataset"] = old
            else:
                session.pop("uploaded_dataset", None)
            dest.unlink(missing_ok=True)
            flash("Upload failed: " + str(exc), "error")
            return redirect(url_for("upload"))
    return render_template("upload.html")

@app.route("/analysis")
def analysis():
    try:
        df = load_data()
        m = metrics(df)
        status_table = df.groupby("Ticket_Status").agg(Bookings=("Booking_ID","count"), Passengers=("Number_of_Passengers","sum"), Fare_Total=("Ticket_Fare","sum")).reset_index().to_dict("records")
        train_table = df.groupby("Train_Name").agg(Bookings=("Booking_ID","count"), Passengers=("Number_of_Passengers","sum")).sort_values("Bookings",ascending=False).reset_index().to_dict("records")
        route_table = df.groupby("Route").agg(Bookings=("Booking_ID","count"), Average_Fare=("Ticket_Fare","mean")).sort_values("Bookings",ascending=False).reset_index().to_dict("records")
        return render_template("analysis.html", m=m, status_table=status_table, train_table=train_table, route_table=route_table)
    except Exception as exc:
        return render_template("error.html", message=str(exc)), 500

@app.route("/records")
def records():
    try:
        df = load_data()
        q = request.args.get("q","").strip()
        if q:
            mask = df.astype(str).apply(lambda c: c.str.contains(q,case=False,na=False,regex=False)).any(axis=1)
            df = df[mask]
        total = len(df)
        visible = df.head(500).fillna("")
        return render_template("records.html", rows=visible.to_dict("records"), columns=list(visible.columns), query=q, total=int(total))
    except Exception as exc:
        return render_template("error.html", message=str(exc)), 500

@app.route("/download")
def download():
    try:
        output = io.BytesIO()
        output.write(load_data().to_csv(index=False).encode("utf-8-sig"))
        output.seek(0)
        return send_file(output, mimetype="text/csv", as_attachment=True, download_name="railway_booking_cleaned.csv")
    except Exception as exc:
        return render_template("error.html", message=str(exc)), 500

@app.route("/reset")
def reset():
    session.pop("uploaded_dataset", None)
    flash("Restored the included sample dataset.", "success")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
