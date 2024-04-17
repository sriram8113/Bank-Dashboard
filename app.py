import streamlit as st
import pandas as pd
import requests
import fdicdata as fdic
import io
from datetime import datetime




# Function to fetch data from the API
def get_institutions():
    df = fdic.getInstitutionsAll()
    return df

def get_name(CERT_NO):
    df = get_institutions()
    return df.loc[df['CERT'] == CERT_NO, 'NAME'].values[0]     

def get_bank_class(CERT_NO):
    df = get_institutions()
    return df.loc[df['CERT'] == CERT_NO, 'BKCLASS'].values[0]

def get_RSS_ID(CERT_NO):
    df = get_institutions()
    return df.loc[df['CERT'] == CERT_NO, 'FED_RSSD'].values[0]

def Established_year(CERT_NO):
    df = get_institutions()
    return df.loc[df['CERT'] == CERT_NO, 'ESTYMD'].values[0]

def get_location_data(CERT_NO):
    df = fdic.getLocation(CERT_NO)
    return df

def No_of_Domestic_Locations(CERT_NO):
    df = get_location_data(CERT_NO)
    return len(df)

def No_of_States(CERT_NO):
    df = fdic.getLocation(CERT_NO)
    return len(df.STNAME.unique())

def get_location_details(CERT_NO):
      
      url = f"https://banks.data.fdic.gov/api/history?filters=CERT%3A%20{CERT_NO}"
      response = requests.get(url)
      json_data = response.json()

      details = {}

      details['BankName'] = json_data['data'][0]['data']['INSTNAME']

      details['FDIC_Unique_Number'] = json_data['data'][0]['data']['FI_UNINUM']

      details['Insured'] = json_data['data'][0]['data']['BANK_INSURED']

      details['ADDRESS']  = json_data['data'][0]['data']['MADDR']

      details['CITY']  = json_data['data'][0]['data']['MCITY']

      details['ZIP_CODE']  = json_data['data'][0]['data']['MZIP5']

      details['Class']  = json_data['data'][0]['data']['FRM_CLASS']

      return details



def getFinancials(IDRSSD_or_CERT, metrics, limit=1, IDRSSD=True, date_range=None):
    assert IDRSSD_or_CERT is not None and metrics is not None, "IDRSSD_or_CERT and metrics cannot be empty"
    assert isinstance(IDRSSD_or_CERT, int), "IDRSSD_or_CERT must be a numeric value"
    if date_range is not None:
        assert len(date_range) == 2, "Date range must have two values"

    url = f"https://banks.data.fdic.gov/api/financials?filters={('RSSDID' if IDRSSD else 'CERT')}%3A%20{IDRSSD_or_CERT}"
    if date_range is not None:
        url += f"%20AND%20REPDTE%3A%5B{date_range[0]}%20TO%20{date_range[1]}%5D"
    url += f"&fields=RSSDID%2CREPDTE%2C{('%2C'.join(metrics))}&sort_by=REPDTE&sort_order=DESC&limit={limit}&offset=0&agg_term_fields=REPDTE&format=csv&download=false&filename=data_file"

    try:
        response = requests.get(url)
        df = pd.read_csv(io.StringIO(response.text))
        df = df.assign(DATE=pd.to_datetime(df["REPDTE"], format="%Y%m%d")).drop(["REPDTE", "ID"], axis=1).rename(columns={"RSSDID": "IDRSSD"})
        return df
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return None


def get_final_data(CERT_NO, start_date):
    RSS_ID = get_RSS_ID(CERT_NO)
    # Fetch financial data using a custom function `getFinancials`

    start_date = pd.to_datetime(start_date)
    current_date = pd.to_datetime("today")
    number_of_quarters = ((current_date.year - start_date.year) * 12 + (current_date.month - start_date.month)) // 3 + 1

    formatted_start_date = pd.to_datetime(start_date).strftime('%Y%m%d')
    financials = getFinancials(
        IDRSSD_or_CERT=int(RSS_ID),
        metrics=["NUMEMP", "NETINC", "NIMY", "ASSET", "TFRA", "EEFFR", "DEPDOM", "LNLSNET", "INTINC", 'INTINCY', 'ROA', 'ROE','LNLSDEPR', 'IDLNCORR'],
        limit=number_of_quarters,
        date_range=[formatted_start_date, "*"]
    )

    # Convert the result to a DataFrame and rename the columns
    final_data = pd.DataFrame(financials).rename(columns={
        'ASSET': 'Total_Assets',
        'DEPDOM': 'Total_Deposits',  # Corrected spelling from 'DEpDOM' to 'DEPDOM'
        'EEFFR': 'Effective_Efficiency_Ratio',
        'TFRA': 'AUM',
        'NIMY': 'Net_Interest_Margin',
        'NUMEMP': 'No_Of_Employees',
        'LNLSNET': 'Net_Loan_Leases',
        'NETINC': 'Net_Income',
        'INTINC': 'Interest_Income',
        'INTINCY' : 'Yield_On_Earning_Assets',
        'ROA' : 'Return_On_Assets',
        'ROE' : 'Return_On_Equity',
        'LNLSDEPR' : 'Net_Loan_And_Leases_to_Deposits',
        'IDLNCORR' : 'Net_Loan_And_Leases_to_Core_Deposits'
    })

    return final_data


def main():


    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("https://i.imgur.com/hFVHclE.jpeg");
            background-size: 100%;  // Adjust this value to control the zoom level
            background-position: center center;
            background-repeat: no-repeat;          
        }}
        .dataframe-container, .dataframe-container table, .dataframe-container table tr, .dataframe-container table tr th, .dataframe-container table tr td {{
        background-color: black !important; /* Black background for tables */
        color: white !important; /* White text color for readability */
        font-weight: bold; /* Makes text bold */
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


    st.title('Bank Details Based On CERT')
    CERT_NO = st.number_input("Enter the CERT number:", key="cert_no")
    start_date = st.date_input("Enter the start date (yyyy-mm-dd):", key="start_date")

    fetch_button = st.button('Fetch Data')

    # Check if it's the initial load or a fetch button has been pressed
    if fetch_button or not st.session_state.get('data_fetched', False):
        if CERT_NO and start_date:
            try:
                basic_info, location_info, financial_data = fetch_all_data(CERT_NO, start_date)
                # Store fetched data in session state
                st.session_state['basic_info'] = basic_info
                st.session_state['location_info'] = location_info
                st.session_state['financial_data'] = financial_data
                st.session_state['data_fetched'] = True
            except Exception as e:
                st.error(f"Failed to retrieve data: {str(e)}")
                st.session_state['data_fetched'] = False

    if st.session_state.get('data_fetched', False):
        display_data()



def fetch_all_data(CERT_NO, start_date):
    basic_info = {
        "Name": get_name(CERT_NO),
        "Bank Class": get_bank_class(CERT_NO),
        "RSS ID": get_RSS_ID(CERT_NO),
        "Established Year": Established_year(CERT_NO),
        "No_of_locations" : No_of_Domestic_Locations(int(CERT_NO)),
        "No_of_states" : No_of_States(int(CERT_NO))
    }
    
    location_info = get_location_details(CERT_NO)
    
    financial_data = get_final_data(CERT_NO, start_date)
    
    return basic_info, location_info, financial_data

def display_data():
    st.subheader("Bank Basic Information")
    for key, value in st.session_state['basic_info'].items():
        st.write(f"{key}: {value}")
        
    st.subheader("Location Information")
    st.write("Location Details:", st.session_state['location_info'])
    
    if 'financial_data' in st.session_state and not st.session_state['financial_data'].empty:
        st.subheader("Financial Information")
        st.dataframe(st.session_state['financial_data'])

        # Quarter selection and display
        st.session_state['financial_data']['Year'] = st.session_state['financial_data']['DATE'].dt.year
        st.session_state['financial_data']['Quarter'] = st.session_state['financial_data']['DATE'].dt.to_period('Q')
        years_quarters = st.session_state['financial_data']['Quarter'].drop_duplicates().sort_values(ascending=False)
        selected_quarter = st.selectbox("Select a quarter:", years_quarters, key="selected_quarter")
        
        filtered_data = st.session_state['financial_data'][st.session_state['financial_data']['Quarter'] == selected_quarter]
        transposed_data = filtered_data.transpose()
        st.table(transposed_data)

if __name__ == '__main__':
    main()
