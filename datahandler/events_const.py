final_values = {
    "gdp" : {"all" : r"^GDP \(QoQ\)  \("},
    "cpi" : {"all" :  r"^CPI \(MoM\)  \(",
             "NZD" : r"^CPI \(QoQ\)  \(",
             "AUD" : r"^CPI \(QoQ\)  \(",
             "JPY" : r"^National Core CPI \(YoY\)  \("
             },
    "unemployment" : {
        "all" : r"^Unemployment Rate  \(",
        "CHF" : r"^Unemployment Rate s.a.  \("
    },
    "employment" : {
        "all" : r"^Economic Activity \(MoM",
        "MXN" : r"^Economic Activity \(MoM",
        "CHF" : r"^Employment Level  \(",
        "JPY" : r"^Jobs/applications ratio  \(",
        "GBP" : r"^Employment Change 3M/3M \(",
        "CAD" : r"^Employment Change  \(",
        "AUD" : r"^Employment Change  \(",
        "EUR" : r"^Employment Change \(QoQ\)  \(",
        "NZD" : r"^Employment Change \(QoQ\)  \(",
        "USD" : r"^Nonfarm Payrolls  \("

    },
    "mpmi" : {
        "all" : r"^Judo Bank Australia Manufacturing PMI",
        "AUD" : r"^Judo Bank Australia Manufacturing PMI",
        "NZD" : r"^Business NZ PMI  \(",
        "CHF" : r"^procure.ch PMI  \(",
        "CAD" : r"^S&P Global Canada Manufacturing PMI  \(",
        "JPY" : r"^au Jibun Bank Japan Manufacturing PMI  \(",
        "GBP" : r"^S&P Global/CIPS UK Manufacturing PMI  \(",
        "EUR" : r"^HCOB Eurozone Manufacturing PMI  \(",
        "MXN" : r"^S&P Global Mexico Manufacturing PMI  \(",
        "USD" : r"^S&P Global US Manufacturing PMI  \(",
        
    },
    "spmi" : {
        "all" : r"^Judo Bank Australia Manufacturing PMI",
        "AUD" : r"^Judo Bank Australia Services PMI",
        "NZD" : r"^Business NZ PMI  \(",
        "CHF" : r"^procure.ch PMI  \(",
        "CAD" : r"^Ivey PMI  \(",
        "JPY" : r"^au Jibun Bank Japan Services PMI  \(",
        "GBP" : r"^S&P Global/CIPS UK Services PMI  \(",
        "EUR" : r"^HCOB Eurozone Services PMI  \(",
        "MXN" : r"^S&P Global Mexico Services PMI  \(",
        "USD" : r"^S&P Global Services PMI  \(",
    },
    "retail" : {
        "all" : r"^Retail Sales \(MoM\)  \(",
        "USD" : r"^Retail Control \(MoM\)  \(",
        "JPY" : r"^Retail Sales \(YoY\)  \(",
        "CHF" : r"^Retail Sales \(YoY\)  \(",
        "NZD" : r"^Retail Sales \(QoQ\)  \(",

    },
    "ppi" : {
        "all" : r"^PPI \(MoM\)  \(",
        "GBP" : r"^PPI Output \(MoM\)  \(",
        "CAD" : r"^IPPI \(MoM\)  \(",
        "AUD" : r"^PPI \(QoQ\)  \(",
        "NZD" : r"^PPI Output \(QoQ\)  \(",

    },
    "interest" : {
        "all" : r"^RBA Interest Rate Decision  \(",
        "AUD" : r"^RBA Interest Rate Decision  \(",
        "MXN" : r"^Interest Rate Decision",
        "NZD" : r"^RBNZ Interest Rate Decision",
        "CHF" : r"^SNB Interest Rate Decision  \(",
        "JPY" : r"^BoJ Interest Rate Decision",
        "CAD" : r"^BoC Interest Rate Decision",
        "GBP" : r"^BoE Interest Rate Decision  \(",
        "EUR" : r"^ECB Interest Rate Decision  \(",
        "USD" : r"^Fed Interest Rate Decision",

    }
}

target = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'CHF', 'NZD', 'MXN', 'AUD']

zone_mapping = {
    "EUR" : "euro zone",
    'USD' : 'united states',
    "GBP" : 'united kingdom',
    "JPY" : 'japan',
    "CAD" : 'canada',
    "CHF" : 'switzerland',
    "NZD" : 'new zealand',
    "MXN" : 'mexico',
    "AUD" : 'australia'
}