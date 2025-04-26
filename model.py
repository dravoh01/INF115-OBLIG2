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
            # First check if the bike exists and is available at the specified station
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

    def create_card_dropoff(self, user_id, bike_id, station_id):
        """Create a card DROPOFF and update bike status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Try both integer and float versions of bike_id for compatibility
            bike_id_float = float(bike_id)
        
            # Debug: Check the bike's current status
            bike_current = pd.read_sql_query(
            "SELECT Bike_ID, Current_Status, Last_Station FROM Bike WHERE Bike_ID = ? OR Bike_ID = ?",
            conn,
            params=[bike_id, bike_id_float]
            )
            print(f"Current bike status: {bike_current}")
        
            # Debug: Show all active trips
            all_trips = pd.read_sql_query(
            "SELECT * FROM Trip WHERE End_Time IS NULL",
            conn
            )
            print(f"All active trips: {len(all_trips)}")
            print(all_trips)
        
            # First check if the bike is in use by this user - try both int and float versions
            bike_status = pd.read_sql_query(
            """
            SELECT t.Trip_ID, t.Start_Time
            FROM Trip t
            WHERE (t.Bike_ID = ? OR t.Bike_ID = ?) AND t.User_ID = ? AND t.End_Time IS NULL
            ORDER BY t.Start_Time DESC
            LIMIT 1
            """,
            conn,
            params=[bike_id, bike_id_float, user_id]
            )
        
            # Debug
            print(f"Query results for active trips with bike {bike_id} and user {user_id}: {len(bike_status)}")
            print(bike_status)
        
            if bike_status.empty:
                # Try a more general query to see what we have, testing both int and float
                broader_query = pd.read_sql_query(
                    "SELECT * FROM Trip WHERE (Bike_ID = ? OR Bike_ID = ?) AND End_Time IS NULL",
                    conn,
                    params=[bike_id, bike_id_float]
                )
                print(f"Broader query for bike {bike_id} active trips: {len(broader_query)}")
                print(broader_query)
            
                # If we found a trip but with a different user, provide a better error message
                if not broader_query.empty:
                    actual_user = broader_query.iloc[0]['User_ID']
                    return False, f"This bike is currently checked out by user {actual_user}"
            
                conn.close()
                return False, "No active trip found for this bike"
        
            trip_id = bike_status.iloc[0]['Trip_ID']
        
        # Update bike status and location - try updating with both int and float versions
            try:
                cursor.execute(
                """
                UPDATE Bike
                SET Current_Status = 'Parked', Last_Station = ?
                WHERE Bike_ID = ?
                """,
                (station_id, bike_id)
            )
            
                if cursor.rowcount == 0:
                # Try with float version if int version didn't work
                    cursor.execute(
                    """
                    UPDATE Bike
                    SET Current_Status = 'Parked', Last_Station = ?
                    WHERE Bike_ID = ?
                    """,
                    (station_id, bike_id_float)
                )
            except Exception as e:
                print(f"Error updating bike status: {e}")
            # Continue anyway, as we want to update the trip record even if the bike update fails
        
        # Update the trip record
            cursor.execute(
            """
            UPDATE Trip
            SET End_Station_ID = ?, End_Time = CURRENT_TIMESTAMP
            WHERE Trip_ID = ?
            """,
            (station_id, trip_id)
        )
        
            conn.commit()
            conn.close()
            return True, trip_id
        except Exception as e:
            print(f"Exception in dropoff: {e}")
            conn.rollback()
            conn.close()
            return False, str(e)

    def report_bike_issue(self, bike_id, issues, user_id = None):
        """Report issues with a bike after dropoff"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Create maintenance record for each reported issue
            for issue in issues:
                cursor.execute(
                    """
                    INSERT INTO Complaint (Bike_ID, User_ID, Complaint_Type)
                    VALUES (?, ?, ?)
                    """,
                    (bike_id, user_id, issue)
                )
                
            # If there are issues, update bike status to 'Missing'
            if issues:
                cursor.execute(
                    """
                    UPDATE Bike
                    SET Current_Status = 'Missing'
                    WHERE Bike_ID = ?
                    """,
                    (bike_id,)
                )
                
            conn.commit()
            conn.close()
            return True, "Issues reported successfully"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
        
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
        

