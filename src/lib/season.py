from datetime import date

def get_season():
    return date.today().year if date.today().month >=3 else date.today().year - 1
