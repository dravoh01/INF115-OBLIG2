import streamlit as st
import pandas as pd
from model.model import BysykkelModel
from view.view import BysykkelView
from controller.controller import BysykkelController

def main():
    # Initialize components
    model = BysykkelModel()
    view = BysykkelView()
    controller = BysykkelController(model)
    
    # Display title
    view.show_title()
    
    # Create tabs (now without the separate report issues tab)
    dashboard_tab, add_user_tab, analysis_tab, checkout_tab, dropoff_tab, mapping_tab = view.show_tabs()
    
    # Initialize session state for filters if not exist
    if 'user_filter' not in st.session_state:
        st.session_state.user_filter = ""
    if 'station_filter' not in st.session_state:
        st.session_state.station_filter = ""
    if 'bike_filter' not in st.session_state:
        st.session_state.bike_filter = ""
    
    # Session state for dropoff flow
    if 'dropoff_step' not in st.session_state:
        st.session_state.dropoff_step = "select_user"
    
    # Get common data
    try:
        users_data = controller.get_dashboard_data()["users"]
        stations_data = controller.get_stations()
        available_bikes = controller.get_analysis_data()["bikes_at_stations"]
        active_trips = controller.get_active_trips()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        users_data = pd.DataFrame(columns=["User_ID", "User_Name", "User_Phone"])
        stations_data = pd.DataFrame(columns=["Station_ID", "Station_Name"])
        available_bikes = pd.DataFrame(columns=["Station_ID", "Station_Name", "Bike_ID", "Bike_Name"])
        active_trips = pd.DataFrame(columns=["Trip_ID", "User_ID", "Bike_ID", "Bike_Name", "Start_Station_ID", "Start_Station_Name", "Start_Time"])
    
    # Process dashboard tab
    try:
        # Check if the filter button was clicked
        if st.session_state.get('filter_users_button', False):
            user_filter = st.session_state.get('user_filter', "")
            dashboard_data = controller.get_dashboard_data(user_filter)
        else:
            dashboard_data = controller.get_dashboard_data()
        
        # Show dashboard
        view.show_dashboard(
            dashboard_tab,
            dashboard_data["users"],
            dashboard_data["bikes"],
            dashboard_data["subscriptions"]
        )
    except Exception as e:
        with dashboard_tab:
            st.error(f"Error loading dashboard data: {e}")
        dashboard_data = {
            "users": pd.DataFrame(columns=["User_ID", "User_Name", "User_Phone"]),
            "bikes": pd.DataFrame(columns=["Bike_Name", "Current_Status"]),
            "subscriptions": pd.DataFrame(columns=["Type", "Purchased"])
        }
    
    # Process analysis tab
    try:
        # Check if the filter button was clicked
        if st.session_state.get('filter_stations_button', False):
            station_filter = st.session_state.get('station_filter', "")
            bike_filter = st.session_state.get('bike_filter', "")
            analysis_data = controller.get_analysis_data(station_filter, bike_filter)
        else:
            analysis_data = controller.get_analysis_data()
        
        # Show analysis tab
        view.show_analysis(
            analysis_tab,
            analysis_data["station_trips"],
            analysis_data["bikes_at_stations"]
        )
    except Exception as e:
        with analysis_tab:
            st.error(f"Error loading analysis data: {e}")
        analysis_data = {
            "station_trips": pd.DataFrame(columns=["Station_ID", "Station_Name", "Number_of_trips"]),
            "bikes_at_stations": pd.DataFrame(columns=["Station_ID", "Station_Name", "Bike_ID", "Bike_Name"])
        }
    
    # Process user form
    try:
        # Show user form and get input
        user_input = view.show_user_form(add_user_tab)
        
        # If form submitted, validate and process
        if user_input["submitted"]:
            # Validate input
            validation_results = controller.validate_user_input(user_input)
            
            # Show validation results
            view.show_validation_results(add_user_tab, user_input, validation_results)
            
            # If all valid, register user
            if all(validation_results.values()):
                success, result = controller.register_user(user_input, validation_results)
                if not success:
                    with add_user_tab:
                        st.error(f"Error registering user: {result}")
    except Exception as e:
        with add_user_tab:
            st.error(f"Error processing user form: {e}")
    
    # Handle checkout tab
    try:
        checkout_data = view.show_checkout_tab(checkout_tab, users_data, stations_data, available_bikes)
        
        if checkout_data["checkout_button"] and checkout_data["user_id"] and checkout_data["station_id"] and checkout_data["bike_id"]:
            success, result = controller.checkout_bike(
                checkout_data["user_id"],
                checkout_data["bike_id"],
                checkout_data["station_id"]
            )
            
            if success:
                st.session_state.checkout_success = True
                with checkout_tab:
                    st.success(f"Bike checkout successful! Trip ID: {result}")
            else:
                with checkout_tab:
                    st.error(f"Error during checkout: {result}")
    except Exception as e:
        with checkout_tab:
            st.error(f"Error processing checkout: {e}")
    
    # Handle dropoff tab with integrated issue reporting
    try:
        # Display the dropoff interface - this will handle multiple steps internally
        dropoff_data = view.show_dropoff_tab(dropoff_tab, users_data, stations_data, active_trips)
        
        # Process dropoff if the button was clicked
        if dropoff_data.get("dropoff_button", False):
            success, result = controller.dropoff_bike(
                dropoff_data["user_id"],
                dropoff_data["bike_id"],
                dropoff_data["station_id"]
            )
            
            if success:
                # If dropoff was successful, move to issue reporting step
                st.session_state.dropoff_step = "report_issues"
                st.rerun()
            else:
                with dropoff_tab:
                    st.error(f"Error during dropoff: {result}")
        
        # Process issue reporting if submitted
        if dropoff_data.get("submit_issues", False):
            success, result = controller.report_bike_issues(
                dropoff_data["bike_id"],
                dropoff_data["selected_issues"],
                dropoff_data.get("additional_notes", "")
            )
            
            if success:
                with dropoff_tab:
                    st.success("Issues reported successfully!")
                    # Reset the dropoff flow
                    st.session_state.dropoff_step = "select_user"
                    st.rerun()
            else:
                with dropoff_tab:
                    st.error(f"Error reporting issues: {result}")
                
    except Exception as e:
        with dropoff_tab:
            st.error(f"Error processing dropoff: {e}")
            st.session_state.dropoff_step = "select_user"  # Reset if error
    
    # Handle mapping tab
    try:
        # Get stations data
        stations_data = controller.get_stations_availability()
        
        # Check if the trip status toggle has changed
        if "trip_in_progress" in st.session_state:
            in_progress = st.session_state.trip_in_progress
            stations_data = controller.get_stations_availability(in_progress)
        
        # Show mapping interface
        view.show_mapping_tab(mapping_tab, stations_data)
    except Exception as e:
        with mapping_tab:
            st.error(f"Error loading mapping data: {e}")

if __name__ == "__main__":
    main()
