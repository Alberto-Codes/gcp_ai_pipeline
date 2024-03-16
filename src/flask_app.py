from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

def search_pdfs(company_name, api_key, search_engine_id):
    search_url = "https://www.googleapis.com/customsearch/v1"
    query = f"{company_name} ESG OR environmental social governance filetype:pdf"
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query,
        "num": 5,
    }
    response = requests.get(search_url, params=params, timeout=5)
    response.raise_for_status()
    search_results = response.json()
    pdf_urls = [
        item["link"]
        for item in search_results.get("items", [])
        if item.get("link").endswith(".pdf")
    ]
    return pdf_urls

@app.route('/search_pdfs', methods=['GET'])
def handle_search():
    company_name = request.args.get('company_name')
    api_key = request.args.get('api_key')
    search_engine_id = request.args.get('search_engine_id')
    if not (company_name and api_key and search_engine_id):
        return jsonify({"error": "Missing required parameters"}), 400
    try:
        pdf_urls = search_pdfs(company_name, api_key, search_engine_id)
        return jsonify(pdf_urls), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
