import sqlite3
import pandas as pd

class BysykkelModel:
    def __init__(self, db_path='bysykkel.db'):
        self.db_path = db_path
        
    def get_connection(self):
        """Create and return a database connection"""
        return sqlite3.connect(self.db_path)
    
    def get_users_alphabetical(self):
        """Get all users sorted alphabetically by name"""
        conn = self.get_connection()
        users = pd.read_sql_query(
            "SELECT User_ID, User_Name, User_Phone FROM User WHERE User_Name IS NOT NULL AND User_Name != '' ORDER BY User_Name ASC",
            conn
        )
        conn.close()
        return users
    
    def get_users_filtered(self, name_filter):
        """Get users filtered by name"""
        conn = self.get_connection()
        users = pd.read_sql_query(
            "SELECT User_ID, User_Name, User_Phone FROM User WHERE User_Name LIKE ? ORDER BY User_Name ASC",
            conn,
            params=[f'%{name_filter}%']
        )
        conn.close()
        return users
    
    def get_bikes_with_status(self):
        """Get all bikes with their current status"""
        conn = self.get_connection()
        bikes = pd.read_sql_query(
            "SELECT Bike_ID, Bike_Name, Current_Status FROM Bike WHERE Bike_Name IS NOT NULL AND Bike_Name != ''",
            conn
        )
        conn.close()
        return bikes
    
    def get_subscription_counts(self):
        """Get count of each subscription type"""
        conn = self.get_connection()
        subs = pd.read_sql_query(
            """
            SELECT Type AS Type, COUNT(*) AS Purchased
            FROM Subscription
            GROUP BY Type
            ORDER BY Purchased DESC
            """,
            conn
        )
        conn.close()
        return subs
    
    def get_station_trips_count(self):
        """Get count of trips ending at each station"""
        conn = self.get_connection()
        station_trips = pd.read_sql_query(
            """
            SELECT s.Station_ID, s.Station_Name, COUNT(t.Trip_ID) AS Number_of_trips
            FROM Station s
            LEFT JOIN Trip t ON s.Station_ID = t.End_Station_ID
            GROUP BY s.Station_ID, s.Station_Name
            ORDER BY s.Station_ID
            """,
            conn
        )
        conn.close()
        return station_trips
    
    def get_bikes_at_stations(self):
        """Get bikes available at each station"""
        conn = self.get_connection()
        bikes_at_stations = pd.read_sql_query(
            """
            SELECT s.Station_ID, s.Station_Name, b.Bike_ID, b.Bike_Name, b.Current_Status
            FROM Station s
            JOIN Bike b ON s.Station_ID = b.Last_Station
            WHERE b.Current_Status = 'Parked'
            ORDER BY s.Station_Name, b.Bike_Name
            """,
            conn
        )
        conn.close()
        return bikes_at_stations
    
    def get_filtered_bikes_at_stations(self, station_filter=None, bike_filter=None):
        """Get bikes at stations filtered by station name and bike name"""
        conn = self.get_connection()
    
        # Start with the base query
        query = """
        SELECT s.Station_ID, s.Station_Name, b.Bike_ID, b.Bike_Name, b.Current_Status
        FROM Station s
        INNER JOIN Bike b ON s.Station_ID = b.Last_Station
        WHERE b.Current_Status = 'Parked'
        """
    
        # List to hold parameter values for the SQL query
        params = []
    
        # Add filters if they exist
        if station_filter and station_filter.strip():
            query += " AND s.Station_Name LIKE ?"
            params.append(f'%{station_filter}%')
    
        if bike_filter and bike_filter.strip():
            query += " AND b.Bike_Name LIKE ?"
            params.append(f'%{bike_filter}%')
    
        # Add order by clause
        query += " ORDER BY s.Station_Name, b.Bike_Name"
    
        # Execute the query with parameters
        try:
            bikes_at_stations = pd.read_sql_query(query, conn, params=params)
            print(f"Query returned {len(bikes_at_stations)} results") 
            return bikes_at_stations
        except Exception as e:
            print(f"Error executing query: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
        finally:
            conn.close()
    
    def get_all_stations(self):
        """Get all stations"""
        conn = self.get_connection()
        stations = pd.read_sql_query(
            "SELECT Station_ID, Station_Name FROM Station ORDER BY Station_Name",
            conn
        )
        conn.close()
        return stations

    def create_card_checkout(self, user_id, bike_id, station_id):
        """Create a card CHECKOUT and update bike status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Check if the user already has an active trip
            user_active_trips = pd.read_sql_query(
                """SELECT Trip_ID 
                FROM Trip 
                WHERE User_ID = ? 
                AND End_Time IS NULL
                """, 
                conn,
                params=[user_id]
            )

            if not user_active_trips.empty:
                conn.close()
                return False, "User already has an active trip"
            
            # Check if the bike exists and is available at the specified station
            bike_status = pd.read_sql_query(
                """
                SELECT Current_Status, Last_Station
                FROM Bike
                WHERE Bike_ID = ?
                """,
                conn,
                params=[bike_id]
            )
        
            # Check if the query returned results
            if bike_status.empty:
                conn.close()
                return False, f"Bike with ID {bike_id} not found"
            
            # Now check if it's available at the right station
            if bike_status.iloc[0]['Current_Status'] != 'Parked' or bike_status.iloc[0]['Last_Station'] != station_id:
                conn.close()
                return False, "Bike is not available at this station"
            
            # Update bike status
            cursor.execute(
                """
                UPDATE Bike
                SET Current_Status = 'Active'
                WHERE Bike_ID = ?
                """,
                (bike_id,)
            )
        
            # Create a new trip record
            cursor.execute(
                """
                INSERT INTO Trip (User_ID, Bike_ID, Start_Station_ID, Start_Time)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (user_id, bike_id, station_id)
            )
        
            trip_id = cursor.lastrowid
        
            # Debug: Verify the trip was created
            print(f"Created trip with ID: {trip_id}")
            trip_check = pd.read_sql_query(
                "SELECT * FROM Trip WHERE Trip_ID = ?",
                conn,
                params=[trip_id]
            )
            print(f"Trip details: {trip_check}")
        
            conn.commit()
            conn.close()
            return True, trip_id
        except Exception as e:
            print(f"Exception in checkout: {e}")
            conn.rollback()
            conn.close()
            return False, str(e)
    
    def get_users_with_active_trips(self):
        """Get only users who have active trips"""
        conn = self.get_connection()
        users_with_trips = pd.read_sql_query(
            """
            SELECT DISTINCT u.User_ID, u.User_Name, u.User_Phone, t.Trip_ID, 
                t.Bike_ID, b.Bike_Name, t.Start_Station_ID, s.Station_Name as Start_Station_Name,
                t.Start_Time
            FROM User u
            JOIN Trip t ON u.User_ID = t.User_ID
            JOIN Bike b ON t.Bike_ID = b.Bike_ID
            JOIN Station s ON t.Start_Station_ID = s.Station_ID
            WHERE t.End_Time IS NULL
            ORDER BY u.User_Name
            """,
            conn
        )
        # Debug: print found trips
        print(f"Found {len(users_with_trips)} active trips:")
        for _, row in users_with_trips.iterrows():
            print(f"User: {row['User_ID']} ({row['User_Name']}), Trip: {row['Trip_ID']}, Bike: {row['Bike_ID']} ({row['Bike_Name']})")
    
        conn.close()
        return users_with_trips

    def create_card_dropoff(self, user_id, bike_id, station_id):
        """Create a card DROPOFF and update bike status"""
        conn = self.get_connection()
        cursor = conn.cursor()
    
        try:
            # Try to standardize types
            try:
                user_id = int(user_id)
                bike_id = int(bike_id)  
                station_id = int(station_id)
            except (ValueError, TypeError):
                print(f"Type conversion failed for one of the values")
        
            print(f"Looking for active trip for User={user_id} (type: {type(user_id)}), Bike={bike_id} (type: {type(bike_id)})")
        
            # First, check if the trip exists at all
            trip_exists = pd.read_sql_query(
                "SELECT * FROM Trip WHERE Trip_ID = 10",  # Hardcoded for testing
                conn
            )
            print(f"Trip 10 exists in database: {not trip_exists.empty}")
            if not trip_exists.empty:
                print(trip_exists)
        
            # Get ALL active trips for debugging
            all_active = pd.read_sql_query(
                "SELECT Trip_ID, User_ID, Bike_ID, End_Time FROM Trip WHERE End_Time IS NULL", 
                conn
            )
            print("All active trips:")
            print(all_active)
        
            # Find the trip by User and Bike
            trip_result = pd.read_sql_query(
                """
                SELECT Trip_ID 
                FROM Trip 
                WHERE User_ID = ? AND Bike_ID = ? AND End_Time IS NULL
                """,
                conn,
                params=[user_id, bike_id]
            )
        
            if trip_result.empty:
                print("No active trip found matching user_id and bike_id")
                conn.close()
                return False, "No active trip found for this user and bike"
        
            trip_id = trip_result.iloc[0]['Trip_ID']
            print(f"Found active trip: {trip_id}")
        
            # Test if we can update ANY record in the Trip table
            test_trip = pd.read_sql_query(
                "SELECT * FROM Trip WHERE Trip_ID = ?", 
                conn, 
                params=[trip_id]
            )
            print(f"Target trip record before update:")
            print(test_trip)
        
            # Begin transaction
            print("Starting transaction")
            cursor.execute("BEGIN TRANSACTION")
        
            # Directly update by Trip_ID to avoid any join issues
            update_query = """
            UPDATE Trip
            SET End_Station_ID = ?, End_Time = CURRENT_TIMESTAMP
            WHERE Trip_ID = ?
            """
            print(f"Executing update with params: station_id={station_id}, trip_id={trip_id}")
            cursor.execute(update_query, (station_id, trip_id))
        
            # Check if update worked
            rowcount = cursor.rowcount
            print(f"Trip update affected {rowcount} rows")
        
            if rowcount == 0:
                # Try direct SQL for debugging
                print("Trying direct SQL update for debugging")
                cursor.execute(f"UPDATE Trip SET End_Station_ID = {station_id}, End_Time = CURRENT_TIMESTAMP WHERE Trip_ID = {trip_id}")
                print(f"Direct SQL update affected {cursor.rowcount} rows")
            
                # Check if anything changed
                after_update = pd.read_sql_query(
                    "SELECT * FROM Trip WHERE Trip_ID = ?", 
                    conn, 
                    params=[trip_id]
                )
                print("Trip record after update attempt:")
                print(after_update)
            
                if cursor.rowcount == 0:
                    print("Update failed, rolling back transaction")
                    conn.rollback()
                    conn.close()
                    return False, "Failed to update trip record - no rows affected"
        
            # Update bike status
            print(f"Updating Bike {bike_id} status to Parked")
            cursor.execute(
                """
                UPDATE Bike
                SET Current_Status = 'Parked', Last_Station = ?
                WHERE Bike_ID = ?
                """,
                (station_id, bike_id)
            )
        
            print(f"Bike update affected {cursor.rowcount} rows")
        
            # Commit the transaction
            print("Committing transaction")
            conn.commit()
        
            # Verify the changes were committed
            final_check = pd.read_sql_query(
                "SELECT * FROM Trip WHERE Trip_ID = ?", 
                conn, 
                params=[trip_id]
            )
            print("Trip record after commit:")
            print(final_check)
        
            conn.close()
            return True, trip_id
        
        except Exception as e:
            print(f"Error in dropoff: {str(e)}")
            try:
                conn.rollback()
            except:
                pass
            conn.close()
            return False, str(e)

    # This function is called after the bike has been dropped off
    def report_bike_issue(self, bike_id, issues, notes=None):
        """Report issues with a bike after dropoff"""
        conn = self.get_connection()
        cursor = conn.cursor()
    
        try:
            print(f"Notes received: '{notes}'")

            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")
        
            # Create maintenance record for each reported issue
            for issue in issues:
                print(f"Adding complaint for Bike {bike_id}: {issue}")

                # Check if notes is None or empty and provide a default
                actual_notes = notes if notes else ""
            
                # Insert into Complaint table
                cursor.execute(
                    """
                INSERT INTO Complaint (Bike_ID, Complaint_Type, Additional_Notes)
                VALUES (?, ?, ?)
                    """,
                    (bike_id, issue, actual_notes)
                )
                
            # If there are issues, update bike status to 'Missing'
            if issues:
                print(f"Updating Bike {bike_id} status to Missing")
                cursor.execute(
                """
                UPDATE Bike
                SET Current_Status = 'Missing'
                WHERE Bike_ID = ?
                """,
                    (bike_id,)
                )
                
            # Commit changes
            conn.commit()
            print(f"Successfully reported {len(issues)} issues for Bike {bike_id}")
            conn.close()
            return True, "Issues reported successfully"
        
        except Exception as e:
            print(f"Error reporting issues: {str(e)}")
            conn.rollback()
            conn.close()
            return False, str(e)
        
    # This function is called to get active trips for a user or all active trips
    def get_active_trips(self, user_id=None):
        """Get active trips for a user or all active trips"""
        conn = self.get_connection()
        query = """
            SELECT t.Trip_ID, t.User_ID, t.Bike_ID, b.Bike_Name, t.Start_Station_ID, 
                   s.Station_Name as Start_Station_Name, t.Start_Time 
            FROM Trip t
            JOIN Bike b ON t.Bike_ID = b.Bike_ID
            JOIN Station s ON t.Start_Station_ID = s.Station_ID
            WHERE t.End_Time IS NULL
        """
        
        params = []
        if user_id:
            query += " AND t.User_ID = ?"
            params.append(user_id)
            
        query += " ORDER BY t.Start_Time DESC"
        
        active_trips = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return active_trips
    
    # This function is called to add a new user to the database
    def add_user(self, user_name, user_phone, email, latitude=None, longitude=None):
        """Add a new user to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO User (User_Name, User_Phone, Email, Latitude, Longitude)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_name, user_phone, email, latitude, longitude)
            )
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def get_stations_with_availability(self):
        """Get all stations with their availability information"""
        conn = self.get_connection()
        stations = pd.read_sql_query(
            """
            SELECT 
                Station_ID, 
                Station_Name, 
                Latitude, 
                Longitude, 
                Max_Parking, 
                Available_Parking
            FROM Station
            ORDER BY Station_Name
            """,
            conn
        )
        conn.close()
        return stations
        

