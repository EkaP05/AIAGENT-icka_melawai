import requests
import time

BASE_URL = "http://localhost:8000"

def test_ingest():
    print("Testing /ingest endpoint...")
    with open("docs/[PT TMD] BUKU SAKU KEBIJAKAN SUMBER DAYA MANUSIA.pdf", "rb") as f:
        files = {"file": f}
        response = requests.post(f"{BASE_URL}/ingest", files=files)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 200

def test_chat(question):
    print(f"Testing chat: '{question}'")
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"question": question}
    )
    data = response.json()
    print(f"Answer: {data['answer']}")
    print(f"Sources: {data['sources']}")
    print(f"Relevant: {data['is_relevant']}\n")
    return data

if __name__ == "__main__":
    time.sleep(2)
    
    test_ingest()
    
    test_chat("Berapa hari cuti tahunan yang saya dapat?")
    test_chat("Bagaimana cara klaim asuransi kesehatan?")
    test_chat("Siapa presiden Amerika?")
    test_chat("Berapa tunjangan makan per bulan?")
