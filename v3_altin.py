import requests
import time
from datetime import datetime


def parse_turkish_number(value):
    if isinstance(value, (int, float)):
        return float(value)
    if not value or value == "-":
        return 0.0
    value = str(value).replace(".", "").replace(",", ".")
    try:
        return float(value)
    except:
        return 0.0


class AltinApi:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://altingrafigi.com/api"
        self.tcmb_url = "https://evds3.tcmb.gov.tr/service/evds"

    def get_canli_altin(self):
        try:
            url = "https://altingrafigi.com/api/fiyatlar"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Altin fiyat hatasi: {e}")
            return None

    def get_tcmb_doviz(self):
        try:
            url = "https://www.tcmb.gov.dev/kurlar/today.xml"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"TCMB doviz hatasi: {e}")
            return None

    def get_altin_from_hisse(self):
        try:
            url = "https://finans.truncgil.com/today.json"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Altin veri hatasi: {e}")
            return None

    def get_gram_altin(self):
        data = self.get_altin_from_hisse()
        if data and "gram-altin" in data:
            altin = data["gram-altin"]
            return {
                "alis": parse_turkish_number(altin.get("Alış", 0)),
                "satis": parse_turkish_number(altin.get("Satış", 0)),
                "degisim": altin.get("Değişim", "0%"),
                "saat": altin.get("Saati", "")
            }
        return None

    def get_ceyrek_altin(self):
        data = self.get_altin_from_hisse()
        if data and "ceyrek-altin" in data:
            altin = data["ceyrek-altin"]
            return {
                "alis": parse_turkish_number(altin.get("Alış", 0)),
                "satis": parse_turkish_number(altin.get("Satış", 0)),
                "degisim": altin.get("Değişim", "0%")
            }
        return None

    def get_yarim_altin(self):
        data = self.get_altin_from_hisse()
        if data and "yarim-altin" in data:
            altin = data["yarim-altin"]
            return {
                "alis": parse_turkish_number(altin.get("Alış", 0)),
                "satis": parse_turkish_number(altin.get("Satış", 0)),
                "degisim": altin.get("Değişim", "0%")
            }
        return None

    def get_tam_altin(self):
        data = self.get_altin_from_hisse()
        if data and "tam-altin" in data:
            altin = data["tam-altin"]
            return {
                "alis": parse_turkish_number(altin.get("Alış", 0)),
                "satis": parse_turkish_number(altin.get("Satış", 0)),
                "degisim": altin.get("Değişim", "0%")
            }
        return None

    def get_ons_altin(self):
        data = self.get_altin_from_hisse()
        if data and "ons-altin" in data:
            altin = data["ons-altin"]
            return {
                "alis": parse_turkish_number(altin.get("Alış", 0)),
                "satis": parse_turkish_number(altin.get("Satış", 0)),
                "degisim": altin.get("Değişim", "0%")
            }
        return None

    def get_doviz(self):
        data = self.get_altin_from_hisse()
        if data:
            doviz = {}
            for key in ["USD", "EUR", "GBP", "JPY"]:
                if key in data:
                    doviz[key] = {
                        "alis": parse_turkish_number(data[key].get("Alış", 0)),
                        "satis": parse_turkish_number(data[key].get("Satış", 0)),
                        "degisim": data[key].get("Değişim", "0%")
                    }
            return doviz
        return None

    def get_tum_fiyatlar(self):
        data = self.get_altin_from_hisse()
        if data:
            result = {}
            for key in data:
                if isinstance(data[key], dict):
                    result[key] = data[key]
            return result
        return None


altin = AltinApi()


def test_altin():
    print("=== ALTIN TEST ===\n")

    print("1. Gram Altin:")
    gram = altin.get_gram_altin()
    if gram:
        print(f"  Alis: {gram['alis']:,.2f} TL")
        print(f"  Satis: {gram['satis']:,.2f} TL")
        print(f"  Degisim: {gram['degisim']}")
    print()

    print("2. Ceyrek Altin:")
    ceyrek = altin.get_ceyrek_altin()
    if ceyrek:
        print(f"  Alis: {ceyrek['alis']:,.2f} TL")
        print(f"  Satis: {ceyrek['satis']:,.2f} TL")
    print()

    print("3. Ons Altin:")
    ons = altin.get_ons_altin()
    if ons:
        print(f"  Alis: {ons['alis']:.2f} USD")
        print(f"  Satis: {ons['satis']:.2f} USD")
    print()

    print("4. Doviz Kurlari:")
    doviz = altin.get_doviz()
    if doviz:
        for key, val in doviz.items():
            print(f"  {key}: {val['alis']:.4f} - {val['satis']:.4f}")


if __name__ == "__main__":
    test_altin()
