import streamlit as st
import pandas as pd

class BysykkelView:
    def show_title(self):
        """Display the main title of the app"""
        st.title("Bysykkel Dashboard")
    
    def show_tabs(self):
        """Create and return tabs for different sections of the app"""
        return st.tabs(["Dashboard", "Add User", "Analysis", "CHECKOUT", "DROPOFF", "Mapping"])
    
    def show_dashboard(self, tab, users_df, bikes_df, subscriptions_df):
        """Display the dashboard with all tables"""
        with tab:
            # (a) Users - with filter
            st.header("Users")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                name_filter = st.text_input("Filter by name:", key="user_filter")
            with col2:
                st.write(" ")
                st.write(" ")
                filter_button = st.button("Filter", key="filter_users_button")
            
            # The users dataframe will be updated in the controller based on the filter
            st.dataframe(users_df)
            
            # (b) Bikes and status
            st.header("Bikes and status")
            st.dataframe(bikes_df)
            
            # (c) Subscription types count
            st.header("Number of subscriptions per type")
            st.dataframe(subscriptions_df)
    
    def show_analysis(self, tab, station_trips_df, bikes_at_stations_df):
        with tab:
            # (a) Station trips count
            st.header("Number of trips ending at each station")
            st.dataframe(station_trips_df.copy())  # Use copy to ensure we have a clean dataframe
    
            # (b) Bikes at stations with filters
            st.header("Bikes available at stations")
    
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                station_filter = st.text_input("Filter by station name:", key="station_filter")
            with col2:
                bike_filter = st.text_input("Filter by bike name:", key="bike_filter")
            with col3:
                st.write(" ")
                st.write(" ")
                filter_button = st.button("Filter", key="filter_stations_button")
    
            # Make sure we have the expected columns and convert to simple format
            try:
                # Reset index to avoid any index-related issues
                df_to_show = bikes_at_stations_df.reset_index(drop=True).copy()
                st.dataframe(df_to_show)
            except Exception as e:
                st.error(f"Error displaying dataframe: {str(e)}")
                st.write("DataFrame info:", bikes_at_stations_df.info())

    def show_user_form(self, tab):
        """Display user registration form and return input values"""
        with tab:
            st.header("User Registration")
            
            with st.form("user_registration_form"):
                user_name = st.text_input("Name:")
                user_phone = st.text_input("Phone Number:")
                email = st.text_input("Email:")
                
                # Additional fields
                col1, col2 = st.columns(2)
                with col1:
                    latitude = st.number_input("Latitude:", value=59.9, min_value=0.0, max_value=90.0)
                with col2:
                    longitude = st.number_input("Longitude:", value=10.7, min_value=0.0, max_value=180.0)
                
                # Submit button
                submitted = st.form_submit_button("Register")
                
                return {
                    "submitted": submitted,
                    "user_name": user_name,
                    "user_phone": user_phone,
                    "email": email,
                    "latitude": latitude,
                    "longitude": longitude
                }
    
    def show_validation_results(self, tab, input_data, validation_results):
        """Display validation results for user input"""
        with tab:
            if input_data["submitted"]:
                st.subheader("Validation Results:")
                
                # Use a different approach to avoid f-string with backslashes
                valid_span = '<span style="color:green">Valid</span>'
                invalid_span = '<span style="color:red">Not valid</span>'
                
                # Name validation
                name_valid = validation_results["name_valid"]
                st.markdown(
                    f"**Name:** {input_data['user_name']} - "
                    f"{valid_span if name_valid else invalid_span}",
                    unsafe_allow_html=True
                )
                
                # Email validation
                email_valid = validation_results["email_valid"]
                st.markdown(
                    f"**Email:** {input_data['email']} - "
                    f"{valid_span if email_valid else invalid_span}",
                    unsafe_allow_html=True
                )
                
                # Phone validation
                phone_valid = validation_results["phone_valid"]
                st.markdown(
                    f"**Phone:** {input_data['user_phone']} - "
                    f"{valid_span if phone_valid else invalid_span}",
                    unsafe_allow_html=True
                )
                
                # Success message if all valid
                if all(validation_results.values()):
                    st.success("User successfully registered!")
    
    def show_checkout_tab(self, tab, users_df, stations_df, available_bikes_df=None):
        """Display the checkout interface"""
        with tab:
            st.header("Bike Checkout")
            
            # Select user
            st.subheader("Select User")
            if not users_df.empty:
                selected_user = st.selectbox(
                    "Select a user:",
                    options=users_df['User_ID'].tolist(),
                    format_func=lambda x: f"{users_df[users_df['User_ID'] == x]['User_Name'].values[0]}"
                )
            else:
                st.warning("No users available")
                selected_user = None
                
            # Select station
            st.subheader("Select Station")
            if not stations_df.empty:
                selected_station_id = st.selectbox(
                    "Select a station:",
                    options=stations_df['Station_ID'].tolist(),
                    format_func=lambda x: f"{stations_df[stations_df['Station_ID'] == x]['Station_Name'].values[0]}"
                )
                
                # Get bikes at selected station
                if selected_station_id and available_bikes_df is not None:
                    station_bikes = available_bikes_df[available_bikes_df['Station_ID'] == selected_station_id]
                    
                    if not station_bikes.empty:
                        st.subheader("Available Bikes")
                        selected_bike = st.selectbox(
                            "Select a bike:",
                            options=station_bikes['Bike_ID'].tolist(),
                            format_func=lambda x: f"{station_bikes[station_bikes['Bike_ID'] == x]['Bike_Name'].values[0]} ({x})"
                        )
                        
                        checkout_button = st.button("Checkout Bike")
                        return {
                            "checkout_button": checkout_button,
                            "user_id": selected_user,
                            "station_id": selected_station_id,
                            "bike_id": selected_bike
                        }
                    else:
                        st.warning("No bikes available at this station")
                        return {
                            "checkout_button": False,
                            "user_id": selected_user,
                            "station_id": selected_station_id,
                            "bike_id": None
                        }
                else:
                    st.warning("Please select a station to see available bikes")
                    return {
                        "checkout_button": False,
                        "user_id": selected_user,
                        "station_id": selected_station_id if selected_station_id else None,
                        "bike_id": None
                    }
            else:
                st.warning("No stations available")
                return {
                    "checkout_button": False,
                    "user_id": selected_user if selected_user else None,
                    "station_id": None,
                    "bike_id": None
                }
        

    def show_dropoff_tab(self, tab, users_df, stations_df, active_trips_df=None):
        """Display the dropoff interface with integrated issue reporting"""
        with tab:
            st.header("Bike Dropoff")
        
            # Session state for tracking dropoff process
            if 'dropoff_step' not in st.session_state:
                st.session_state.dropoff_step = "select_user"
            if 'current_bike_id' not in st.session_state:
                st.session_state.current_bike_id = None
            if 'current_bike_name' not in st.session_state:
                st.session_state.current_bike_name = ""
        
            # Step 1: Select user and trip
            if st.session_state.dropoff_step == "select_user":
                # Select user
                st.subheader("Select User")
                if not users_df.empty:
                    selected_user = st.selectbox(
                        "Select a user:",
                        options=users_df['User_ID'].tolist(),
                        format_func=lambda x: f"{users_df[users_df['User_ID'] == x]['User_Name'].values[0]} ({x})",
                        key="dropoff_user"
                    )
                
                    # Show active trips for this user
                    if selected_user and active_trips_df is not None:
                        user_trips = active_trips_df[active_trips_df['User_ID'] == selected_user]
                    
                        if not user_trips.empty:
                            st.subheader("Active Trips")
                            selected_trip = st.selectbox(
                                "Select a trip to end:",
                                options=user_trips['Trip_ID'].tolist(),
                                format_func=lambda x: f"Trip {x}: {user_trips[user_trips['Trip_ID'] == x]['Bike_Name'].values[0]} from {user_trips[user_trips['Trip_ID'] == x]['Start_Station_Name'].values[0]}"
                            )
                        
                            # Get bike ID from the selected trip
                            bike_id = user_trips[user_trips['Trip_ID'] == selected_trip]['Bike_ID'].values[0]
                            bike_name = user_trips[user_trips['Trip_ID'] == selected_trip]['Bike_Name'].values[0]
                        
                            # Select dropoff station
                            st.subheader("Select Dropoff Station")
                            if not stations_df.empty:
                                selected_station = st.selectbox(
                                    "Select a station:",
                                    options=stations_df['Station_ID'].tolist(),
                                    format_func=lambda x: f"{stations_df[stations_df['Station_ID'] == x]['Station_Name'].values[0]} ({x})",
                                    key="dropoff_station"
                                )
                            
                                dropoff_button = st.button("Complete Dropoff")
                            
                                if dropoff_button:
                                    # Store values for next step
                                    st.session_state.dropoff_user_id = selected_user
                                    st.session_state.dropoff_bike_id = bike_id
                                    st.session_state.dropoff_bike_name = bike_name
                                    st.session_state.dropoff_station_id = selected_station
                                    st.session_state.dropoff_trip_id = selected_trip
                                
                                    return {
                                        "dropoff_button": True,
                                        "user_id": selected_user,
                                        "bike_id": bike_id,
                                        "station_id": selected_station,
                                        "trip_id": selected_trip
                                    }
                            
                                return {
                                    "dropoff_button": False,
                                    "user_id": selected_user,
                                    "bike_id": bike_id,
                                    "station_id": selected_station,
                                    "trip_id": selected_trip
                                }
                            else:
                                st.warning("No stations available")
                                return {
                                    "dropoff_button": False,
                                    "user_id": selected_user,
                                    "bike_id": bike_id,
                                    "station_id": None,
                                    "trip_id": selected_trip
                                }
                        else:
                            st.warning("No active trips for this user")
                            return {
                                "dropoff_button": False,
                                "user_id": selected_user,
                                "bike_id": None,
                                "station_id": None,
                                "trip_id": None
                            }
                    else:
                        st.warning("Please select a user to see active trips")
                        return {
                            "dropoff_button": False,
                            "user_id": selected_user if selected_user else None,
                            "bike_id": None,
                            "station_id": None,
                            "trip_id": None
                        }
                else:
                    st.warning("No users available")
                    return {
                        "dropoff_button": False,
                        "user_id": None,
                        "bike_id": None,
                        "station_id": None,
                        "trip_id": None
                    }
        
            # Step 2: Show report issues section after successful dropoff
            elif st.session_state.dropoff_step == "report_issues":
                st.success(f"Bike dropoff successful! Trip ID: {st.session_state.dropoff_trip_id}")
            
                st.subheader(f"Did you experience any issues with the bike?")
            
                col1, col2 = st.columns(2)
                with col1:
                    report_issues = st.button("Yes, report issues")
                with col2:
                    no_issues = st.button("No, everything was fine")
            
                if report_issues:
                    st.session_state.dropoff_step = "show_issue_form"
                    st.rerun()
                
                if no_issues:
                    st.success("Thank you! Hope you had a nice trip!")
                    # Reset the dropoff flow
                    st.session_state.dropoff_step = "select_user"
                    st.session_state.current_bike_id = None
                    st.session_state.current_bike_name = ""
                    st.rerun()
                
                return {
                    "dropoff_button": False,
                    "report_button": report_issues,
                    "no_issues_button": no_issues,
                    "user_id": st.session_state.dropoff_user_id,
                    "bike_id": st.session_state.dropoff_bike_id,
                    "station_id": st.session_state.dropoff_station_id,
                    "trip_id": st.session_state.dropoff_trip_id
                }
            
            # Step 3: Show issue form if user selected "Yes, report issues"
            elif st.session_state.dropoff_step == "show_issue_form":
                st.subheader(f"Report Issues with Bike: {st.session_state.dropoff_bike_name}")
            
                issues = [
                    "Flat tire",
                    "Broken chain",
                    "Brake issues",
                    "Gear problems",
                    "Damaged frame",
                    "Bent wheel",
                    "Faulty lights",
                    "Missing bell",
                    "Handlebar issues",
                    "Pedal problems",
                    "Seat issues",
                    "Other mechanical issue"
                ]
            
                selected_issues = []
                for issue in issues:
                    if st.checkbox(issue):
                        selected_issues.append(issue)
            
                additional_notes = st.text_area("Additional Notes:")
            
                submit_button = st.button("Submit Report")
                back_button = st.button("Back")
            
                if back_button:
                    st.session_state.dropoff_step = "report_issues"
                    st.rerun()
                
                if submit_button:
                    return {
                        "dropoff_button": False,
                        "submit_issues": True,
                        "selected_issues": selected_issues,
                        "additional_notes": additional_notes,
                        "user_id": st.session_state.dropoff_user_id,
                        "bike_id": st.session_state.dropoff_bike_id,
                        "station_id": st.session_state.dropoff_station_id,
                        "trip_id": st.session_state.dropoff_trip_id
                    }
            
                return {
                    "dropoff_button": False,
                    "submit_issues": False,
                    "selected_issues": [],
                    "additional_notes": "",
                    "user_id": st.session_state.dropoff_user_id,
                    "bike_id": st.session_state.dropoff_bike_id,
                    "station_id": st.session_state.dropoff_station_id,
                    "trip_id": st.session_state.dropoff_trip_id
                }

    def show_mapping_tab(self, tab, stations_df):
        """Display the station mapping interface"""
        with tab:
            st.header("Station Availability Map")
        
            # Create a two-column layout
            col1, col2 = st.columns([3, 1])
        
            with col1:
                # Station selector
                if not stations_df.empty:
                    station_options = stations_df.index.tolist()
                    selected_station = st.selectbox(
                        "Select a station:",
                        options=station_options,
                        format_func=lambda x: stations_df.loc[x, 'Station_Name'],
                        key="mapping_station_selector"
                    )
                else:
                    st.warning("No stations available")
                    selected_station = None
        
            with col2:
                # Trip status toggle
                in_progress = st.toggle("Trip in progress", value=False, key="trip_status_toggle")
        
            # Display the table with availability info
            if selected_station is not None:
                # We'll need to filter the data for the selected station in the controller
                st.subheader(f"Availability for {stations_df.loc[selected_station, 'Station_Name']}")
            
                # Use st.markdown to render HTML links
                st.markdown(
                stations_df.loc[[selected_station]].to_html(escape=False),
                unsafe_allow_html=True
            )
            
                # Alternative way using a DataFrame
                st.dataframe(
                stations_df.loc[[selected_station]],
                column_config={
                    "Location": st.column_config.LinkColumn("Location")
                },
                hide_index=True
            )
            
