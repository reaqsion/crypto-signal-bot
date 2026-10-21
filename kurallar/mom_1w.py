from kurallar.motor import Rule
import pandas as pd


class MOM_1W(Rule):
    def __init__(self, threshold_pct=5):
        super().__init__(
            name=f"MOM_1W_{threshold_pct}",
            description=f"Son 7 gun getirisi > %{threshold_pct}",
            direction="long"
        )
        self.threshold_pct = threshold_pct

    def get_required_lookback(self):
        return 7 * 24

    def evaluate(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < self.get_required_lookback():
            return False

        current_price = df.iloc[current_idx]['close']
        price_7d_ago = df.iloc[current_idx - self.get_required_lookback()]['close']

        if price_7d_ago <= 0:
            return False

        ret = (current_price - price_7d_ago) / price_7d_ago * 100
        return ret > self.threshold_pct
