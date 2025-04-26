import sqlite3
import pandas as pd

# Connect to SQLite database (creates it if it doesn't exist)
conn = sqlite3.connect('bysykkel.db')
cursor = conn.cursor()

# Enable foreign key constraints
cursor.execute('PRAGMA foreign_keys = ON')

# Read only the first 25 columns (adjust this number as needed)
try:
    # First read just the header to see how many columns we should have
    header = pd.read_csv('bysykkel-old.csv', nrows=0).columns
    num_cols = len(header)
    
    # Then read the file using only the valid columns
    df = pd.read_csv('bysykkel-old.csv', usecols=range(num_cols))
    print(f"Successfully loaded {len(df)} rows with {num_cols} columns")
except Exception as e:
    print(f"Error loading CSV: {e}")

# Create tables
# User(#User_ID, User_Name, User_Phone, Latitude, Longitude)
cursor.execute('''
CREATE TABLE IF NOT EXISTS User (
    User_ID INTEGER PRIMARY KEY,
    User_Name TEXT,
    User_Phone TEXT,
    Latitude REAL,
    Longitude REAL
    )
''')

# Station(#Station_ID, Station_Name, Latitude, Longitude, Max_Parking, Available_Parking)
# Creating the Station table first since Bike references it
cursor.execute('''
CREATE TABLE IF NOT EXISTS Station (
    Station_ID INTEGER PRIMARY KEY,
    Station_Name TEXT,
    Latitude REAL,
    Longitude REAL,
    Max_Parking INTEGER,
    Available_Parking INTEGER
    )
''')

# Bike(#Bike_ID, *Last_Station, Bike_Name, Current_Status)
cursor.execute('''
CREATE TABLE IF NOT EXISTS Bike (
    Bike_ID INTEGER PRIMARY KEY,
    Last_Station INTEGER,
    Bike_Name TEXT,
    Current_Status TEXT,
    FOREIGN KEY (Last_Station) REFERENCES Station(Station_ID)
    )
''')

# Subscription(#SubscriptionID, *User_ID, Type, Status, Start, End)
cursor.execute('''
CREATE TABLE IF NOT EXISTS Subscription (
    SubscriptionID INTEGER PRIMARY KEY,
    User_ID INTEGER,
    Type TEXT,
    Start TEXT,
    FOREIGN KEY (User_ID) REFERENCES User(User_ID)
)
''')

# Trip(#Trip_ID, *User_ID, *Bike_ID, *End_Station_ID, *Start_Station_ID, Start_Time, End_Time)
cursor.execute('''
CREATE TABLE IF NOT EXISTS Trip (
    Trip_ID INTEGER PRIMARY KEY,
    User_ID INTEGER,
    Bike_ID INTEGER,
    Start_Station_ID INTEGER,
    End_Station_ID INTEGER,
    Start_Time TEXT,
    End_Time TEXT,
    FOREIGN KEY (User_ID) REFERENCES User(User_ID),
    FOREIGN KEY (Bike_ID) REFERENCES Bike(Bike_ID),
    FOREIGN KEY (Start_Station_ID) REFERENCES Station(Station_ID),
    FOREIGN KEY (End_Station_ID) REFERENCES Station(Station_ID)
)
''')

# Complaint(#Complaint_ID, *Bike_ID, *User_ID, Complaint_Type)
cursor.execute('''
CREATE TABLE IF NOT EXISTS Complaint (
    Complaint_ID INTEGER PRIMARY KEY,
    Bike_ID INTEGER,
    User_ID INTEGER,
    Complaint_Type TEXT,
    FOREIGN KEY (Bike_ID) REFERENCES Bike(Bike_ID),
    FOREIGN KEY (User_ID) REFERENCES User(User_ID)
)
''')

# Reparation(#Reparation_ID, *Bike_ID, *Station_ID, Start_Time, End_Time)
cursor.execute('''
CREATE TABLE IF NOT EXISTS Reparation (
    Reparation_ID INTEGER PRIMARY KEY,
    Bike_ID INTEGER,
    Complaint_ID INTEGER,
    Status TEXT,
    FOREIGN KEY (Bike_ID) REFERENCES Bike(Bike_ID),
    FOREIGN KEY (Complaint_ID) REFERENCES Complaint(Complaint_ID)
)
''')

# === Set up error tracking ===
success_count = {
    'users': 0,
    'subscriptions': 0,
    'stations': 0,
    'bikes': 0,
    'trips': 0
}

# === First, clear the existing Station table for a clean insert ===
cursor.execute('DELETE FROM Station')
print("Cleared existing Station table for clean insert")

# === Insert stations first to ensure foreign key constraints are met ===
# Create a set to track unique station IDs we've processed
processed_stations = set()

for _, row in df.iterrows():
    # Start-station
    try:
        # Only process each station ID once
        if row['start_station_id'] not in processed_stations and pd.notna(row['start_station_id']):
            # Fix the typo in column name: satart_station_available_spots -> start_station_available_spots
            available_spots_col = 'start_station_available_spots'
            if 'satart_station_available_spots' in df.columns:
                available_spots_col = 'satart_station_available_spots'
                
            cursor.execute('''
                INSERT INTO Station (Station_ID, Station_Name, Latitude, Longitude, Max_Parking, Available_Parking)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                row['start_station_id'], row['start_station_name'],
                row['start_station_latitude'], row['start_station_longitude'],
                row['start_station_max_spots'], row[available_spots_col]
            ))
            if cursor.rowcount > 0:
                success_count['stations'] += 1
                processed_stations.add(row['start_station_id'])
    except Exception as e:
        print(f"Error inserting start station {row['start_station_id']}: {e}")

    # End-station
    try:
        # Only process each station ID once
        if row['end_station_id'] not in processed_stations and pd.notna(row['end_station_id']):
            cursor.execute('''
                INSERT INTO Station (Station_ID, Station_Name, Latitude, Longitude, Max_Parking, Available_Parking)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                row['end_station_id'], row['end_station_name'],
                row['end_station_latitude'], row['end_station_longitude'],
                row['end_station_max_spots'], row['end_station_available_spots']
            ))
            if cursor.rowcount > 0:
                success_count['stations'] += 1
                processed_stations.add(row['end_station_id'])
    except Exception as e:
        print(f"Error inserting end station {row['end_station_id']}: {e}")

# Commit stations now to ensure they're available for bike foreign keys
conn.commit()
print(f"Inserted {success_count['stations']} unique stations")

# === Clear existing data for clean re-insert ===
cursor.execute('DELETE FROM Bike')
print("Cleared existing Bike table for clean insert")

# === Insert bikes ===
processed_bikes = set()  # Track which bikes we've processed

for _, row in df.iterrows():
    try:
        # Only try to insert each unique bike once
        if row['bike_id'] not in processed_bikes and pd.notna(row['bike_id']):
            bike_id = row['bike_id']
            bike_name = row['bike_name'] if pd.notna(row['bike_name']) else None
            bike_status = row['bike_status'] if pd.notna(row['bike_status']) else None
            bike_station_id = row['bike_station_id'] if pd.notna(row['bike_station_id']) else None
            
            cursor.execute('''
                INSERT INTO Bike (Bike_ID, Bike_Name, Current_Status, Last_Station)
                VALUES (?, ?, ?, ?)
            ''', (bike_id, bike_name, bike_status, bike_station_id))
            
            # Add to processed set regardless of success to avoid duplicates
            processed_bikes.add(bike_id)
            success_count['bikes'] += 1
            print(f"Successfully inserted bike {bike_id}")
    except Exception as e:
        print(f"Error inserting bike {row['bike_id']}: {e}")

# Commit bikes before inserting trips
conn.commit()
print(f"Inserted {success_count['bikes']} unique bikes")

# === Insert users ===
cursor.execute('DELETE FROM User')
print("Cleared existing User table for clean insert")

processed_users = set()
for _, row in df.iterrows():
    try:
        if row['user_id'] not in processed_users and pd.notna(row['user_id']):
            cursor.execute('''
                INSERT INTO User (User_ID, User_Name, User_Phone)
                VALUES (?, ?, ?)
            ''', (row['user_id'], row['user_name'], row['user_phone_number']))
            processed_users.add(row['user_id'])
            success_count['users'] += 1
    except Exception as e:
        print(f"Error inserting user {row['user_id']}: {e}")

conn.commit()
print(f"Inserted {success_count['users']} unique users")

# === Insert subscriptions ===
cursor.execute('DELETE FROM Subscription')
print("Cleared existing Subscription table for clean insert")

processed_subscriptions = set()
for _, row in df.iterrows():
    try:
        if pd.notna(row['subscription_id']) and row['subscription_id'] not in processed_subscriptions:
            cursor.execute('''
                INSERT INTO Subscription (SubscriptionID, Type, Start, User_ID)
                VALUES (?, ?, ?, ?)
            ''', (row['subscription_id'], row['subscription_type'], row['subscription_start_time'], row['user_id']))
            processed_subscriptions.add(row['subscription_id'])
            success_count['subscriptions'] += 1
    except Exception as e:
        print(f"Error inserting subscription {row['subscription_id']}: {e}")

conn.commit()
print(f"Inserted {success_count['subscriptions']} unique subscriptions")

# === Insert trips ===
cursor.execute('DELETE FROM Trip')
print("Cleared existing Trip table for clean insert")

processed_trips = set()
for _, row in df.iterrows():
    try:
        if pd.notna(row['trip_id']) and row['trip_id'] not in processed_trips:
            cursor.execute('''
                INSERT INTO Trip (
                    Trip_ID, User_ID, Bike_ID, Start_Station_ID, End_Station_ID,
                    Start_Time, End_Time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['trip_id'], row['user_id'], row['bike_id'],
                row['start_station_id'], row['end_station_id'],
                row['trip_start_time'], row['trip_end_time']
            ))
            processed_trips.add(row['trip_id'])
            success_count['trips'] += 1
    except Exception as e:
        print(f"Error inserting trip {row['trip_id']}: {e}")

# === Print summary and commit changes ===
print("\nInsert Summary:")
for table, count in success_count.items():
    print(f"  {table.capitalize()}: {count} rows inserted")

# IMPORTANT: Commit changes to save them to the database
conn.commit()

# Verify data was inserted
print("\nData Verification:")
for table in ['User', 'Subscription', 'Station', 'Bike', 'Trip']:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {table} table: {count} rows")

# === Verify station names ===
cursor.execute("SELECT Station_ID, Station_Name FROM Station LIMIT 10")
sample_stations = cursor.fetchall()
print("\nSample Station Names:")
for station in sample_stations:
    print(f"  ID: {station[0]}, Name: {station[1]}")

# === Verify bike details ===
cursor.execute("SELECT Bike_ID, Bike_Name, Current_Status, Last_Station FROM Bike")
all_bikes = cursor.fetchall()
print("\nAll Bikes in the Database:")
for bike in all_bikes:
    print(f"  ID: {bike[0]}, Name: {bike[1]}, Status: {bike[2]}, Station: {bike[3]}")

# Close the connection
conn.close()