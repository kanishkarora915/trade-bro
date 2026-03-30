from .d01_uoa import detect as d01_uoa
from .d02_order_flow import detect as d02_order_flow
from .d03_sweep import detect as d03_sweep
from .d04_iv_divergence import detect as d04_iv_divergence
from .d05_velocity import detect as d05_velocity
from .d06_confluence_map import detect as d06_confluence_map
from .d07_block_print import detect as d07_block_print
from .d08_repeat_buyer import detect as d08_repeat_buyer
from .d09_skew_shift import detect as d09_skew_shift
from .d10_bid_ask import detect as d10_bid_ask
from .d11_synthetic import detect as d11_synthetic
from .d12_greeks import detect as d12_greeks
from .d14_max_pain import detect as d14_max_pain
from .d15_correlation import detect as d15_correlation
from .d16_vacuum import detect as d16_vacuum
from .d17_fii_dii import detect as d17_fii_dii

ALL_DETECTORS = {
    "d01_uoa": d01_uoa,
    "d02_order_flow": d02_order_flow,
    "d03_sweep": d03_sweep,
    "d04_iv_divergence": d04_iv_divergence,
    "d05_velocity": d05_velocity,
    "d06_confluence_map": d06_confluence_map,
    "d07_block_print": d07_block_print,
    "d08_repeat_buyer": d08_repeat_buyer,
    "d09_skew_shift": d09_skew_shift,
    "d10_bid_ask": d10_bid_ask,
    "d11_synthetic": d11_synthetic,
    "d12_greeks": d12_greeks,
    "d14_max_pain": d14_max_pain,
    "d15_correlation": d15_correlation,
    "d16_vacuum": d16_vacuum,
    "d17_fii_dii": d17_fii_dii,
}
