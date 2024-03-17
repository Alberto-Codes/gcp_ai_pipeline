import json

import requests
from bs4 import BeautifulSoup


def fetch_sasb_pdf_links(company_name):

    # Send an initial request to the website
    url = "https://sasb.ifrs.org/company-use/sasb-reporters/"
    response = requests.get(url)

    # Get the cookie from the response headers
    cookie = response.cookies.get_dict()

    # Convert the cookie dictionary to a string
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookie.items()])

    url = "https://sasb.ifrs.org/wp-json/sasb/v1/reportsSearch"
    params = {"search": company_name, "format": "html"}
    headers = {
        "authority": "sasb.ifrs.org",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "cookie": cookie_str,
        "referer": "https://sasb.ifrs.org/company-use/sasb-reporters/",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        return []

    # Parse the JSON response
    data = json.loads(response.text)

    # Parse the HTML content
    soup = BeautifulSoup(data["html"], "html.parser")

    # Find all 'a' tags (which define hyperlinks) in the HTML content
    links = soup.find_all("a")

    base_url = "https://sasb.ifrs.org/company-use/sasb-reporters/"

    # Extract the href attribute (which contains the URL) from each 'a' tag
    pdf_links = [
        (
            base_url + link.get("href")
            if not link.get("href").startswith("http")
            else link.get("href")
        )
        for link in links
    ]

    return pdf_links
