from src.f1_data import load_session, load_driver_telemetry

def main():
    #testing bridge with OpenF1 data
    year = 2024
    gp_name = "Bahrain"
    session_type = "Race"
    driver_number = 1

    #test for session data
    print(f'finding session data for {year} {gp_name} {session_type}')
    try:
        session = load_session(grand_prix= gp_name, session_type=session_type, year=year)
        session_key = session['session_key']
    except Exception as e:
        print(f'Error loading session: {e}')
        return

    #test for driver telemetry
    print(f'Fetching telemetry for Driver {driver_number}')
    try:
        telemetry = load_driver_telemetry(session_key=session_key, driver_number=driver_number)
        if telemetry.empty:
            print("No telemetry")
            return
        print(f"Successfully loaded telemetry records")
        print(telemetry[['Time', 'Speed', 'Throttle', 'Brake', 'Gear']].head())

    except Exception as e:
        print(f'Error loading telemetry {e}')
    


if __name__ == '__main__':
    main()