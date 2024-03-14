import streamlit as st

def handle_input(company_name):
    # This function will handle the input, you can add your own logic here
    st.write(f'Company Name: {company_name}')

def main():
    st.title('Company Name Input')
    company_name = st.text_input('Enter the company name')
    if st.button('Submit'):
        handle_input(company_name)

if __name__ == "__main__":
    main()