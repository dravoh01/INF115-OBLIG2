import re
import pandas as pd

class BysykkelController:
    def __init__(self, model):
        self.model = model
        # Store the current filter state
        self.user_filter = ""
        self.station_filter = ""
        self.bike_filter = ""
    
    def get_dashboard_data(self, user_filter=""):
        """Get all data needed for the dashboard"""
        # Update the filter if provided
        if user_filter != "":
            self.user_filter = user_filter
        
        # Get users based on filter
        if self.user_filter:
            users = self.model.get_users_filtered(self.user_filter)
        else:
            users = self.model.get_users_alphabetical()
            
        return {
            "users": users,
            "bikes": self.model.get_bikes_with_status(),
            "subscriptions": self.model.get_subscription_counts()
        }
    
    def get_analysis_data(self, station_filter="", bike_filter=""):
        """Get data for analysis tab"""
        # Update the filters if provided
        if station_filter != "":
            self.station_filter = station_filter
        if bike_filter != "":
            self.bike_filter = bike_filter
        
        # Get bikes at stations based on filters
        if self.station_filter or self.bike_filter:
            bikes_at_stations = self.model.get_filtered_bikes_at_stations(
                self.station_filter, self.bike_filter
            )
        else:
            bikes_at_stations = self.model.get_bikes_at_stations()
            
        return {
            "station_trips": self.model.get_station_trips_count(),
            "bikes_at_stations": bikes_at_stations
        }
    
    def clear_analysis_filters(self):
        """Clear the analysis tab filters"""
        self.station_filter = ""
        self.bike_filter = ""
    
    def validate_user_input(self, input_data):
        """Validate user input according to rules"""
        validation_results = {}
        
        # Validate name (only letters A-Å)
        name = input_data["user_name"]
        validation_results["name_valid"] = bool(re.match(r'^[A-Za-zÆØÅæøå ]+$', name))
        
        # Validate email (contains @)
        email = input_data["email"]
        validation_results["email_valid"] = '@' in email
        
        # Validate phone (exactly 8 digits)
        phone = input_data["user_phone"]
        validation_results["phone_valid"] = bool(re.match(r'^\d{8}$', phone))
        
        return validation_results
    
    def register_user(self, input_data, validation_results):
        """Register a new user if all validations pass"""
        if all(validation_results.values()):
            try:
                user_id = self.model.add_user(
                    input_data["user_name"],
                    input_data["user_phone"],
                    input_data["email"],
                    input_data["latitude"],
                    input_data["longitude"]
                )
                return True, user_id
            except Exception as e:
                return False, str(e)
        return False, "Validation failed"
    
    def get_stations(self):
        """Get all stations"""
        return self.model.get_all_stations()
    
    def get_active_trips(self, user_id=None):
        """Get active trips for a user or all active trips"""
        return self.model.get_active_trips(user_id)
    
    def checkout_bike(self, user_id, bike_id, station_id):
        """Process bike checkout"""
        return self.model.create_card_checkout(user_id, bike_id, station_id)
    
    def dropoff_bike(self, user_id, bike_id, station_id):
        """Process bike dropoff"""
        return self.model.create_card_dropoff(user_id, bike_id, station_id)
    
    def report_bike_issues(self, bike_id, issues, notes=None):
        """Report issues with a bike"""
        return self.model.report_bike_issue(bike_id, issues, notes)
    
    # Combined function for processing dropoff with issue reporting
    def process_dropoff_and_issues(self, dropoff_data):
        """Process bike dropoff and handle issue reporting if needed"""
        # First handle the dropoff
        if dropoff_data.get("dropoff_button", False):
            success, result = self.dropoff_bike(
                dropoff_data["user_id"],
                dropoff_data["bike_id"],
                dropoff_data["station_id"]
            )
            return {"success": success, "result": result, "step": "dropoff"}
            
        # Then handle issue reporting if submitted
        elif dropoff_data.get("submit_issues", False):
            if "selected_issues" not in dropoff_data or not dropoff_data["selected_issues"]:
                return {"success": False, "result": "No issues selected", "step": "issues"}
            
            issues_success, issues_result = self.report_bike_issues(
                dropoff_data["bike_id"],
                dropoff_data["selected_issues"],
                dropoff_data.get("additional_notes", "")
            )
            return {"success": issues_success, "result": issues_result, "step": "issues"}
            
        # Otherwise just return info about the current state
        else:
            return {"success": True, "result": None, "step": "form"}
        
    def get_users_with_active_trips(self):
        """Get users who have active trips"""
        return self.model.get_users_with_active_trips()
    
    def get_stations_availability(self, in_progress=False):
        """
        Get stations with availability percentage
    
        Args:
            in_progress: Boolean indicating if a trip is in progress
    
        Returns:
            DataFrame with station info and calculated availability
        """
        # Get stations data from model
        stations_df = self.model.get_stations_with_availability()
    
        # Calculate availability percentage based on in_progress flag
        if in_progress:
            # If trip is in progress, availability is percentage of available spots
            stations_df['Availability'] = (stations_df['Available_Parking'] / stations_df['Max_Parking'] * 100).round(0).astype(int)
        else:
            # If trip is not in progress, availability is percentage of non-available spots
            stations_df['Availability'] = ((stations_df['Max_Parking'] - stations_df['Available_Parking']) / stations_df['Max_Parking'] * 100).round(0).astype(int)
    
        # Add Map link column
        stations_df['Location'] = stations_df.apply(
            lambda row: f'<a href="https://www.google.com/maps?q={row.Latitude},{row.Longitude}" target="_blank">Google Maps</a>', 
            axis=1
        )
            
        # Select only the needed columns
        result_df = stations_df[['Station_Name', 'Availability', 'Location']]
    
        # Add % sign to availability
        result_df.loc[:, 'Availability'] = result_df['Availability'].astype(str) + '%'    
        return result_df