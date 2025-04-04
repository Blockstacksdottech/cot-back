final_values_old = {
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
        "AUD" : r"^Judo Bank Manufacturing PMI",
        "NZD" : r"^Business NZ PMI  \(",
        "CHF" : r"^procure.ch Manufacturing PMI  \(",
        "CAD" : r"^S&P Global Manufacturing PMI  \(",
        "JPY" : r"^au Jibun Bank Manufacturing PMI  \(",
        "GBP" : r"^S&P Global Manufacturing PMI  \(",
        "EUR" : r"^HCOB Eurozone Manufacturing PMI  \(",
        "MXN" : r"^S&P Global Manufacturing PMI  \(",
        "USD" : r"^S&P Global Manufacturing PMI  \(",
        
    },
    "spmi" : {
        "all" : r"^Judo Bank Australia Manufacturing PMI",
        "AUD" : r"^Judo Bank Services PMI",
        "NZD" : r"^Business NZ PMI  \(",
        "CHF" : r"^procure.ch Manufacturing PMI  \(",
        "CAD" : r"^Ivey PMI  \(",
        "JPY" : r"^au Jibun Bank Services PMI  \(",
        "GBP" : r"^S&P Global Services PMI  \(",
        "EUR" : r"^HCOB Eurozone Services PMI  \(",
        "MXN" : r"^S&P Global Manufacturing PMI  \(",
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

final_values = {
    "gdp": {
        "USD": r"^GDP Growth Rate QoQ \(Q\d\)",
        "EUR": r"^GDP Growth Rate QoQ \(",
        "GBP": r"^GDP MoM \(",
        "JPY": r"^GDP Growth Rate QoQ \(Q\d\)",
        "CAD": r"^GDP MoM \(",
        "CHF": r"^GDP Growth Rate QoQ \(Q\d\)",
        "NZD": r"^GDP Growth Rate QoQ \(Q\d\)",
        "MXN": r"^GDP Growth Rate QoQ \(Q\d\)",
        "AUD": r"^GDP Growth Rate QoQ \(Q\d\)",
    },
    "cpi": {
        "USD": r"^CPI \(",
        "EUR": r"^CPI \(",
        "GBP": r"^Inflation Rate MoM \(",
        "JPY": r"^Tokyo Core CPI YoY \(",
        "CAD": r"^Inflation Rate MoM \(",
        "CHF": r"^Inflation Rate MoM \(",
        "NZD": r"^Inflation Rate QoQ \(Q\d\)",
        "MXN": r"^Inflation Rate MoM \(",
        "AUD": r"^Inflation Rate QoQ \(",
    },
    "unemployment": {
        "USD": r"^Unemployment Rate \(",
        "EUR": r"^Unemployment Rate Harmonised \(",
        "GBP": r"^Unemployment Rate \(",
        "JPY": r"^Unemployment Rate \(",
        "CAD": r"^Unemployment Rate \(",
        "CHF": r"^Unemployment Rate \(",
        "NZD": r"^Unemployment Rate \(Q\d\)",
        "MXN": r"^Unemployment Rate \(",
        "AUD": r"^Unemployment Rate \(",
    },
    "employment": {
        "USD": r"^Nonfarm Payrolls",
        "EUR": r"^Employment Change QoQ \(",
        "GBP": r"^Employment Change \(",
        "JPY": r"^Jobs\/applications ratio \(",
        "CAD": r"^Employment Change \(",
        "CHF": r"^Non Farm Payrolls \(Q\d\)",
        "NZD": r"^Employment Change QoQ \(Q\d\)",
        "MXN": r"^Economic Activity MoM \(",
        "AUD": r"^Employment Change \(",
    },
    "mpmi": {
        "USD": r"^ISM Manufacturing PMI \(",
        "EUR": r"^HCOB Manufacturing PMI \(",
        "GBP": r"^Markit/CIPS Manufacturing PMI \(",
        "JPY": r"^Jibun Bank Manufacturing PMI \(",
        "CAD": r"^Markit Manufacturing PMI \(",
        "CHF": r"^procure\.ch Manufacturing PMI \(",
        "MXN": r"^Markit Manufacturing PMI \(",
        "NZD": r"^Business NZ PMI \(",
        "AUD": r"^Markit Manufacturing PMI \(",
    },
    "spmi": {
        "USD": r"^ISM Services PMI \(",
        "EUR": r"^HCOB Services PMI \(",
        "GBP": r"^Markit/CIPS UK Services PMI \(",
        "JPY": r"^Jibun Bank Services PMI \(",
        "CAD": r"^S&P Global Services PMI \(",
        "NZD": r"^Services NZ PSI \(",
        "AUD": r"^Markit Services PMI \(",
    },
    "retail": {
        "USD": r"^Retail Sales MoM \(",
        "EUR": r"^Retail Sales MoM \(",
        "GBP": r"^Retail Sales MoM \(",
        "JPY": r"^Retail Sales MoM \(",
        "CAD": r"^Retail Sales MoM \(",
        "CHF": r"^Retail Sales MoM \(",
        "NZD": r"^Retail Sales QoQ \(Q\d\)",
        "MXN": r"^Industrial Production MoM \(",
        "AUD": r"^Retail Sales MoM \(",
    },
    "ppi": {
        "USD": r"^PPI MoM \(",
        "EUR": r"^PPI MoM \(",
        "GBP": r"^PPI Output MoM \(",
        "JPY": r"^PPI MoM \(",
        "CAD": r"^PPI MoM \(",
        "CHF": r"^Producer & Import Prices MoM \(",
        "NZD": r"^PPI Output QoQ \(Q\d\)",
        "MXN": r"^Producer Price Index MoM \(",
        "AUD": r"^PPI QoQ \(",
    },
    "interest": {
        "USD": r"^Fed Interest Rate Decision",
        "EUR": r"^ECB Interest Rate Decision",
        "GBP": r"^BoE Interest Rate Decision",
        "JPY": r"^BoJ Interest Rate Decision",
        "CAD": r"^BoC Interest Rate Decision",
        "CHF": r"^SNB Interest Rate Decision",
        "NZD": r"^RBNZ Interest Rate Decision",
        "MXN": r"^Interest Rate Decision",
        "AUD": r"^RBA Interest Rate Decision",
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

weights = {
    "gdp": 0.20,              # Broad measure of economic health
    "cpi": 0.25,              # Direct link to inflation and central bank policy decisions
    "unemployment": 0.10,     # Labor market health but less dynamic than employment change
    "employment": 0.20,       # High-frequency labor market indicator
    "mpmi": 0.07,             # Manufacturing PMI: sector-specific indicator
    "spmi": 0.08,             # Services PMI: significant in service-heavy economies
    "retail": 0.10,           # Retail Sales MoM: critical for consumer spending
    "ppi": 0.05,              # Producer Price Index: important for understanding inflation trends
    "interest": 0.05          # Interest Rate: significant for monetary policy but less frequent
}