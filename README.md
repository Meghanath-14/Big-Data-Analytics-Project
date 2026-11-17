# RailPulse — Railway Ticket Booking Data Analysis

## Run on Windows / VS Code
1. Extract this ZIP.
2. Open the `RailPulse_Complete_Project` folder in VS Code.
3. Open a terminal in that folder and run:

```cmd
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

4. Open `http://127.0.0.1:5000` in Chrome or Edge.
5. Keep the terminal open while using the website. Press Ctrl+C to stop it.

## Features
- Dashboard with five charts and key metrics
- Upload and validate CSV datasets
- Data cleaning: duplicate removal, date parsing, missing fare handling
- Status, train and route summaries
- Searchable booking records (up to 500 displayed)
- Download cleaned CSV and reset to sample dataset

## Required columns for uploaded CSV
Booking_ID, Booking_Date, Train_Name, Source, Destination, Class_Type, Number_of_Passengers, Ticket_Status, Ticket_Fare.

## Academic note
The included 5,000-row dataset is synthetic demonstration data, not official Indian Railways data. This version performs local Pandas analytics. Hadoop HDFS and Apache Spark are not integrated yet; add and test those separately before claiming distributed Big Data processing.
