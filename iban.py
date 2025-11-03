from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

class IBANAPI:
    def __init__(self):
        self.base_url = "https://hesapno.com/mod_iban_coz"
        
    def analyze_iban(self, iban_number):
        """IBAN numarasını analiz eder"""
        try:
            # IBAN doğrulama
            if not self.validate_iban(iban_number):
                return {"error": "Geçersiz IBAN formatı"}
            
            # Web sayfasına POST isteği gönder
            payload = {
                'iban': iban_number,
                'coz': 'Çözümle'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(self.base_url, data=payload, headers=headers)
            
            if response.status_code == 200:
                return self.parse_response(response.text, iban_number)
            else:
                return {"error": "API erişim hatası"}
                
        except Exception as e:
            return {"error": f"Sistem hatası: {str(e)}"}
    
    def validate_iban(self, iban):
        """IBAN formatını doğrular"""
        # TR ile başlamalı, 26 karakter olmalı
        if not re.match(r'^TR\d{24}$', iban.replace(' ', '').upper()):
            return False
        return True
    
    def parse_response(self, html_content, iban):
        """HTML cevabını parse eder"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            "iban": iban,
            "banka_adi": "",
            "sube_kodu": "", 
            "hesap_no": "",
            "durum": "",
            "ulke": "Türkiye",
            "banka_kodu": ""
        }
        
        try:
            # Tablo içindeki verileri çek
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        key = cells[0].get_text().strip().lower()
                        value = cells[1].get_text().strip()
                        
                        if 'banka' in key:
                            result["banka_adi"] = value
                        elif 'şube' in key:
                            result["sube_kodu"] = value
                        elif 'hesap' in key:
                            result["hesap_no"] = value
                        elif 'durum' in key:
                            result["durum"] = value
            
            # Banka kodunu IBAN'dan çıkar
            if iban.startswith('TR'):
                result["banka_kodu"] = iban[4:6]
                
        except Exception as e:
            result["error"] = f"Parse hatası: {str(e)}"
        
        return result

# API nesnesi
iban_api = IBANAPI()

@app.route('/iban_sorgulama', methods=['GET', 'POST'])
def iban_sorgulama():
    """IBAN sorgulama endpoint'i"""
    if request.method == 'GET':
        iban = request.args.get('iban', '')
    else:
        iban = request.form.get('iban', '')
    
    if not iban:
        return jsonify({
            "error": "IBAN parametresi gerekli",
            "kullanim": "/iban_sorgulama?iban=TR330006100519786457841326"
        })
    
    result = iban_api.analyze_iban(iban)
    return jsonify(result)

@app.route('/iban_dogrulama', methods=['GET'])
def iban_dogrulama():
    """Sadece IBAN doğrulama"""
    iban = request.args.get('iban', '')
    
    if not iban:
        return jsonify({"error": "IBAN parametresi gerekli"})
    
    is_valid = iban_api.validate_iban(iban)
    return jsonify({
        "iban": iban,
        "gecerli": is_valid
    })

@app.route('/iban_banka_kodlari', methods=['GET'])
def banka_kodlari():
    """Banka kodları listesi"""
    banka_kodlari = {
        "10": "Türkiye Cumhuriyet Merkez Bankası",
        "12": "Türkiye Halk Bankası",
        "15": "Türkiye İş Bankası", 
        "30": "Türkiye Vakıflar Bankası",
        "32": "Türkiye Garanti Bankası",
        "46": "Akbank",
        "62": "Türkiye Halk Bankası",
        "67": "Yapı Kredi Bankası",
        "90": "Türkiye Emlak Bankası"
    }
    return jsonify(banka_kodlari)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
