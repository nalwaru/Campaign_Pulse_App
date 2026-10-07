import pandas as pd
import pytest


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01"] * 3 + ["2026-01-02"] * 3),
            "Platform": ["Google", "Meta", "LinkedIn"] * 2,
            "Campaign": ["Search_Brand", "Retargeting_V1", "B2B_Outreach"] * 2,
            "Spend": [100.0, 200.0, 300.0, 100.0, 200.0, 300.0],
            "Clicks": [100, 200, 100, 100, 200, 100],
            "Conversions": [10, 20, 3, 10, 20, 3],
            "Revenue": [500.0, 600.0, 600.0, 500.0, 600.0, 600.0],
        }
    )
