import requests
import time
from datetime import datetime
from config import BTCTURK_BASE_URL, BTCTURK_GRAPH_URL, REQUEST_DELAY_MS


class BtcTurkAPI:
    def __init__(self):
        self.session = requests.Session()
        self.last_request_time = 0

    def _wait(self):
        elapsed = (time.time() - self.last_request_time) * 1000
        if elapsed < REQUEST_DELAY_MS:
            time.sleep((REQUEST_DELAY_MS - elapsed) / 1000)
        self.last_request_time = time.time()

    def get_ticker(self, symbol=None):
        self._wait()
        url = f"{BTCTURK_BASE_URL}/api/v2/ticker"
        if symbol:
            url += f"?pair={symbol}"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Ticker hatasi: {e}")
            return None

    def get_all_tickers(self):
        return self.get_ticker()

    def get_symbol_ticker(self, symbol):
        data = self.get_ticker()
        if data and "data" in data:
            for item in data["data"]:
                if item.get("pair") == symbol:
                    return item
        return None

    def get_klines(self, symbol, resolution="60", start_date=None, end_date=None):
        self._wait()

        if start_date is None:
            start_date = int(datetime.now().timestamp() - 30 * 24 * 3600)
        if end_date is None:
            end_date = int(datetime.now().timestamp())

        url = f"{BTCTURK_GRAPH_URL}/v1/klines/history"
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": start_date,
            "to": end_date
        }

        try:
            resp = self.session.get(url, params=params, timeout=10)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                print(f"Rate limit, {retry_after}s bekleniyor...")
                time.sleep(retry_after)
                return self.get_klines(symbol, resolution, start_date, end_date)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Klines hatasi: {e}")
            return None

    def get_exchange_info(self):
        self._wait()
        # Dogru yol /api/v2/server/exchangeinfo. Onceki hali 404 doneyordu
        # ve fonksiyon None dondugu icin sessizce yutuluyordu.
        url = f"{BTCTURK_BASE_URL}/api/v2/server/exchangeinfo"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Exchange info hatasi: {e}")
            return None


api = BtcTurkAPI()
