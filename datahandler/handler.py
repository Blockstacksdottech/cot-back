import cot_reports as cot
import pandas as pd
import numpy as np
import json
from .models import DateInterval, Data, GeneralData, ProcessedData
from django.utils.timezone import make_aware

symbol_mapping = {
    'USD INDEX - ICE FUTURES U.S.': 'USD',
    'EURO FX - CHICAGO MERCANTILE EXCHANGE': 'EUR',
    'GOLD - COMMODITY EXCHANGE INC.': 'GOLD',
    'BRITISH POUND - CHICAGO MERCANTILE EXCHANGE': 'GBP',
    'JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE': 'JPY',
    'EURO FX/BRITISH POUND XRATE - CHICAGO MERCANTILE EXCHANGE': 'EURGBP',
    'CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE': 'CAD',
    'SWISS FRANC - CHICAGO MERCANTILE EXCHANGE': 'CHF',
    'NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE': 'NZD',
    'MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE': 'MXN'
}


relevant_contracts = ['USD INDEX - ICE FUTURES U.S.',
                      'EURO FX - CHICAGO MERCANTILE EXCHANGE',
                      'BRITISH POUND - CHICAGO MERCANTILE EXCHANGE',
                      'JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE',
                      'EURO FX/BRITISH POUND XRATE - CHICAGO MERCANTILE EXCHANGE',
                      'CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE',
                      'SWISS FRANC - CHICAGO MERCANTILE EXCHANGE',
                      'NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE',
                      'MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE',
                      'AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE',
                      'WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE',
                      'GOLD - COMMODITY EXCHANGE INC.',
                      'S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE'
                      ]

currency_to_symbol = {
    'USD INDEX - ICE FUTURES U.S.': 'USD',
    'EURO FX - CHICAGO MERCANTILE EXCHANGE': 'EUR',
    'GOLD - COMMODITY EXCHANGE INC.': 'GOLD',
    'BRITISH POUND - CHICAGO MERCANTILE EXCHANGE': 'GBP',
    'JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE': 'JPY',
    'EURO FX/BRITISH POUND XRATE - CHICAGO MERCANTILE EXCHANGE': 'EUR',
    'CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE': 'CAD',
    'SWISS FRANC - CHICAGO MERCANTILE EXCHANGE': 'CHF',
    'NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE': 'NZD',
    'MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE': 'MXN',
    'AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE': 'AUD',
    'NEW ZEALAND DOLLAR - CHICAGO MERCANTILE EXCHANGE': 'NZD',
    'WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE': "Crude OIL",
    'GOLD - COMMODITY EXCHANGE INC.': "GOLD",
    'S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE': "S&P 500"

}


def filter_legacy_df(final_data):
    # filter the legacy report
    legacy_report = final_data[0].copy()
    important_headers = [
        'Market and Exchange Names',
        'date',
        'Open Interest (All)',
        'Noncommercial Positions-Long (All)',
        'Noncommercial Positions-Short (All)',
        'Commercial Positions-Long (All)',
        'Commercial Positions-Short (All)',
        ' Total Reportable Positions-Long (All)',
        'Total Reportable Positions-Short (All)',
        'Nonreportable Positions-Long (All)',
        'Nonreportable Positions-Short (All)',
        'Change in Open Interest (All)',
        'Change in Noncommercial-Long (All)',
        'Change in Noncommercial-Short (All)',
        'Change in Commercial-Long (All)',
        'Change in Commercial-Short (All)'
    ]

    # Filter the dataframe
    filtered_legacy_df = legacy_report[important_headers]
    filtered_legacy_df["Symbol"] = filtered_legacy_df[important_headers[0]].str.split(
        " ").str[0]
    filtered_legacy_df = filtered_legacy_df[filtered_legacy_df['Market and Exchange Names'].isin(
        relevant_contracts)]
    return filtered_legacy_df


def calculate_net_positions(df):
    df['Net_Noncommercial_Positions'] = df['Noncommercial Positions-Long (All)'] - \
        df['Noncommercial Positions-Short (All)']
    df['Net_Commercial_Positions'] = df['Commercial Positions-Long (All)'] - \
        df['Commercial Positions-Short (All)']
    df['Net_Nonreportable_Positions'] = df['Nonreportable Positions-Long (All)'] - \
        df['Nonreportable Positions-Short (All)']
    return df


def calculate_percentage_change(df):
    df[f'pct_change'] = df['pair_net_position'].pct_change() * 100
    return df


def calculate_5_week_avg_change(df, window):
    df[f'{window}_week_change'] = df['pct_change'].rolling(
        window=window).mean()
    return df


def analyze_legacy_df(legacy_df, currency_pairs, isContract=False):
    combined_results = []
    pair_result = {}

    for base_currency, quote_currency in currency_pairs:
        base_filtered_df = legacy_df[legacy_df['Market and Exchange Names'].str.contains(
            base_currency, regex=True)]
        quote_filtered_df = legacy_df[legacy_df['Market and Exchange Names'].str.contains(
            quote_currency, regex=True)]

        # Calculate net positions for both currencies
        base_filtered_df = calculate_net_positions(base_filtered_df)
        quote_filtered_df = calculate_net_positions(quote_filtered_df)

        # Aggregate by date
        base_agg = base_filtered_df.groupby('date').sum().reset_index()
        quote_agg = quote_filtered_df.groupby('date').sum().reset_index()

        # Merge base and quote dataframes on date
        merged_df = pd.merge(base_agg, quote_agg, on='date',
                             suffixes=('_base', '_quote'))

        # Rename columns to base and quote positions
        merged_df = merged_df.rename(columns={
            'Noncommercial Positions-Long (All)_base': 'base_long',
            'Noncommercial Positions-Short (All)_base': 'base_short',
            'Net_Noncommercial_Positions_base': 'base_net_position',
            'Noncommercial Positions-Long (All)_quote': 'quote_long',
            'Noncommercial Positions-Short (All)_quote': 'quote_short',
            'Net_Noncommercial_Positions_quote': 'quote_net_position',
            'Commercial Positions-Long (All)_base': 'base_comm_long',
            'Commercial Positions-Short (All)_base': 'base_comm_short',
            'Net_Commercial_Positions_base': 'base_comm_net_position',
            'Commercial Positions-Long (All)_quote': 'quote_comm_long',
            'Commercial Positions-Short (All)_quote': 'quote_comm_short',
            'Net_Commercial_Positions_quote': 'quote_comm_net_position',
            'Nonreportable Positions-Long (All)_base': 'base_nonrep_long',
            'Nonreportable Positions-Short (All)_base': 'base_nonrep_short',
            'Net_Nonreportable_Positions_base': 'base_nonrep_net_position',
            'Nonreportable Positions-Long (All)_quote': 'quote_nonrep_long',
            'Nonreportable Positions-Short (All)_quote': 'quote_nonrep_short',
            'Net_Nonreportable_Positions_quote': 'quote_nonrep_net_position',
        })

        # Add pair information

        # print(f'Pair : {currency_to_symbol[base_currency]}/{currency_to_symbol[quote_currency]}')

        if not isContract:
            pair = f'{currency_to_symbol[base_currency]}/{currency_to_symbol[quote_currency]}'
            merged_df['pair'] = pair
            # Calculate pair positions based on the given rules
            if quote_currency == "US Dollar":
                merged_df['pair_long'] = merged_df['base_long']
                merged_df['pair_short'] = merged_df['base_short']
                merged_df['pair_net_position'] = merged_df['base_net_position']
            elif base_currency == "US Dollar":
                merged_df['pair_long'] = merged_df['quote_short']
                merged_df['pair_short'] = merged_df['quote_long']
                merged_df['pair_net_position'] = - \
                    merged_df['quote_net_position']
            else:
                merged_df['pair_long'] = merged_df['base_long']
                merged_df['pair_short'] = merged_df['base_short']
                merged_df['pair_net_position'] = merged_df['base_net_position']
        else:
            pair = f'{currency_to_symbol[base_currency]}'
            print(f'Pair is {pair}')
            merged_df['pair'] = pair
            merged_df['pair_long'] = merged_df['base_long']
            merged_df['pair_short'] = merged_df['base_short']
            merged_df['pair_net_position'] = merged_df['base_net_position']

        # Calculate percentage changes for base, quote, and pair net positions
        merged_df = calculate_percentage_change(merged_df)

        # Calculate 5-week average percentage change
        for i in range(2, 11):
            merged_df = calculate_5_week_avg_change(merged_df, i)

        # Calculate sentiment
        merged_df['sentiment'] = merged_df.apply(
            lambda row: 'long dominated' if row['base_long'] > row['quote_long'] else 'short dominated',
            axis=1
        )

        # Calculate crowding data
        merged_df['crowding_data'] = merged_df.apply(
            lambda row: f'Long: {row["base_long"]}, Short: {row["base_short"]}',
            axis=1
        )

        # Append to combined results
        combined_results.append(merged_df)
        pair_result[pair] = merged_df
    # print(f"combined length : {len(combined_results)}")
    # for r in combined_results:
        # print(r["pair"].head(1))
    # return pair_result

    # Concatenate all results into a single DataFrame
    combined_df = pd.concat(combined_results, ignore_index=True)

    # Sort the combined DataFrame by date
    combined_df = combined_df.sort_values(by='date')

    return combined_df


def filter_and_analyze_legacy_data(final_data):
    usd_pairs = [
        ("EURO FX - CHICAGO MERCANTILE EXCHANGE", "USD INDEX - ICE FUTURES U.S."),
        ("USD INDEX - ICE FUTURES U.S.",
         "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"),
        ("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
         "USD INDEX - ICE FUTURES U.S."),
        ("USD INDEX - ICE FUTURES U.S.", "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE"),
        ("USD INDEX - ICE FUTURES U.S.",
         "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"),
        ("AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
         "USD INDEX - ICE FUTURES U.S."),
        ("NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE", "USD INDEX - ICE FUTURES U.S.")
    ]

    eur_pairs = [
        ("EURO FX - CHICAGO MERCANTILE EXCHANGE",
         "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"),
        ("EURO FX - CHICAGO MERCANTILE EXCHANGE",
         "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE"),
        ("EURO FX - CHICAGO MERCANTILE EXCHANGE",
         "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE"),
        ("EURO FX - CHICAGO MERCANTILE EXCHANGE",
         "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"),
        ("EURO FX - CHICAGO MERCANTILE EXCHANGE",
         "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"),
        ("EURO FX - CHICAGO MERCANTILE EXCHANGE",
         "NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE")
    ]

    jpy_pairs = [
        ("USD INDEX - ICE FUTURES U.S.",
         "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"),
        ("EURO FX - CHICAGO MERCANTILE EXCHANGE",
         "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"),
        ("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
         "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"),
        ("AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
         "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"),
        ("NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE",
         "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE")
    ]

    gbp_pairs = [
        ("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
         "USD INDEX - ICE FUTURES U.S."),
        ("EURO FX - CHICAGO MERCANTILE EXCHANGE",
         "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE"),
        ("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
         "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"),
        ("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
         "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE"),
        ("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
         "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"),
        ("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
         "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"),
        ("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
         "NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE")
    ]

    chf_pairs = [
        ("USD INDEX - ICE FUTURES U.S.", "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE"),
        ("EURO FX - CHICAGO MERCANTILE EXCHANGE",
         "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE"),
        ("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
         "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE")
    ]

    contracts = [(x, x) for x in relevant_contracts]

    # Combine all pairs
    all_currency_pairs = usd_pairs + eur_pairs + jpy_pairs + gbp_pairs + chf_pairs
    all_currency_pairs = list(set(all_currency_pairs))
    print(len(all_currency_pairs))
    print(len(contracts))

    # Assuming final_data is loaded and passed to filter_legacy_df
    filtered_legacy_df = filter_legacy_df(final_data)

    important_headers = [
        'date',
        'pair',
        'base_long',
        'base_short',
        'base_net_position',
        'quote_long',
        'quote_short',
        'quote_net_position',
        'base_comm_long',
        'base_comm_short',
        'base_comm_net_position',
        'quote_comm_long',
        'quote_comm_short',
        'quote_comm_net_position',
        'base_nonrep_long',
        'base_nonrep_short',
        'base_nonrep_net_position',
        'quote_nonrep_long',
        'quote_nonrep_short',
        'quote_nonrep_net_position',
        # Noncommercial Positions-Long (All) for the pair
        'pair_long',
        # Noncommercial Positions-Short (All) for the pair
        'pair_short',
        'pair_net_position',
        'pct_change',
        '2_week_change',
        '3_week_change',
        '4_week_change',
        '5_week_change',
        '6_week_change',
        '7_week_change',
        '8_week_change',
        '9_week_change',
        '10_week_change',
        'sentiment'
    ]

    # Process all currency pairs
    legacy_df = filter_legacy_df(final_data)
   # Process all currency pairs
    combined_df1 = analyze_legacy_df(
        filtered_legacy_df, all_currency_pairs).fillna(0)
    combined_df2 = analyze_legacy_df(
        filtered_legacy_df, contracts, isContract=True).fillna(0)
    combined_df = pd.concat([combined_df1, combined_df2], ignore_index=True)
    res = combined_df.sort_values(by='date')[important_headers]
    # print(analyzed_df.head()[["Symbol","Decision",'Sentiment_Score']])
    return res

# Example call to the function
# filter_and_analyze_tff_data(final_data)


# helper
def format_date(date_str):
    date_str = str(date_str)
    date_str = ("0" * (6 - len(date_str)))+date_str
    # Assuming century information is missing in the first 2 digits
    year = int(date_str[:2]) + 2000
    month = int(date_str[2:4])
    day = int(date_str[4:])
    return pd.to_datetime(f"{year}-{month:02d}-{day:02d}")

# partial fetching function


def fetch_cot_data(start_year, end_year, cot_type, date_header):
    df = pd.DataFrame()
    for i in range(start_year, end_year + 1):
        try:
            single_year = pd.DataFrame(
                cot.cot_year(i, cot_report_type=cot_type))
            # print(list(single_year.columns))
            single_year['date'] = single_year[date_header].apply(format_date)
            # df.append(single_year, ignore_index=True)
            df = pd.concat([df, single_year], ignore_index=True)
        except Exception as e:
            print(e)
            continue
    df = df.sort_values(by=date_header, ascending=False)
    return df

# main grouping function


def main(start_year, end_year):
    reports_type = ['legacy_futopt']
    date_header = ['As of Date in Form YYMMDD']
    final_data = []
    index = 0
    for c_type in reports_type:
        print(f"########## fetching {c_type} ##########")
        data = fetch_cot_data(start_year, end_year, c_type, date_header[index])
        final_data.append(data)
        index += 1
    return final_data


def dataframe_to_json(dataframe):
    return dataframe.to_json(orient='records')


def save_to_django_models(symbol_dataframes):
    for symbol, dataframe in symbol_dataframes.items():
        json_data = dataframe_to_json(dataframe)
        data_list = json.loads(json_data)

        for data in data_list:
            try:
                date = data['date']
                pair = data["pair"]
                date_obj = make_aware(pd.to_datetime(date, unit='ms'))

                date_interval, created = DateInterval.objects.get_or_create(
                    date=date_obj)
                date_interval.save()

                if ProcessedData.objects.filter(date_interval=date_interval, pair=pair).exists():
                    print(
                        f"Entry for {pair} on {date_obj} already exists. Skipping...")
                    continue

                # Ensure all necessary fields are available and handle edge cases
                base_long = data.get('base_long', 0) or 0
                base_short = data.get('base_short', 0) or 0
                base_net_position = data.get('base_net_position', 0) or 0
                quote_long = data.get('quote_long', 0) or 0
                quote_short = data.get('quote_short', 0) or 0
                quote_net_position = data.get('quote_net_position', 0) or 0
                base_comm_long = data.get('base_comm_long', 0) or 0
                base_comm_short = data.get('base_comm_short', 0) or 0
                base_comm_net_position = data.get(
                    'base_comm_net_position', 0) or 0
                quote_comm_long = data.get('quote_comm_long', 0) or 0
                quote_comm_short = data.get('quote_comm_short', 0) or 0
                quote_comm_net_position = data.get(
                    'quote_comm_net_position', 0) or 0
                base_nonrep_long = data.get('base_nonrep_long', 0) or 0
                base_nonrep_short = data.get('base_nonrep_short', 0) or 0
                base_nonrep_net_position = data.get(
                    'base_nonrep_net_position', 0) or 0
                quote_nonrep_long = data.get('quote_nonrep_long', 0) or 0
                quote_nonrep_short = data.get('quote_nonrep_short', 0) or 0
                quote_nonrep_net_position = data.get(
                    'quote_nonrep_net_position', 0) or 0
                pair_long = data.get('pair_long', 0) or 0
                pair_short = data.get('pair_short', 0) or 0
                pair_net_position = data.get('pair_net_position', 0) or 0
                pct_change = data.get('pct_change', 0) or 0
                two_week_change = data.get('2_week_change', 0) or 0
                three_week_change = data.get('3_week_change', 0) or 0
                four_week_change = data.get('4_week_change', 0) or 0
                five_week_change = data.get('5_week_change', 0) or 0
                six_week_change = data.get('6_week_change', 0) or 0
                seven_week_change = data.get('7_week_change', 0) or 0
                eight_week_change = data.get('8_week_change', 0) or 0
                nine_week_change = data.get('9_week_change', 0) or 0
                ten_week_change = data.get('10_week_change', 0) or 0
                sentiment = data.get('sentiment', 'Neutral')

                general_data = ProcessedData.objects.create(
                    date_interval=date_interval,
                    pair=pair,
                    base_long=base_long,
                    base_short=base_short,
                    base_net_position=base_net_position,
                    quote_long=quote_long,
                    quote_short=quote_short,
                    quote_net_position=quote_net_position,
                    base_comm_long=base_comm_long,
                    base_comm_short=base_comm_short,
                    base_comm_net_position=base_comm_net_position,
                    quote_comm_long=quote_comm_long,
                    quote_comm_short=quote_comm_short,
                    quote_comm_net_position=quote_comm_net_position,
                    base_nonrep_long=base_nonrep_long,
                    base_nonrep_short=base_nonrep_short,
                    base_nonrep_net_position=base_nonrep_net_position,
                    quote_nonrep_long=quote_nonrep_long,
                    quote_nonrep_short=quote_nonrep_short,
                    quote_nonrep_net_position=quote_nonrep_net_position,
                    pair_long=pair_long,
                    pair_short=pair_short,
                    pair_net_position=pair_net_position,
                    pct_change=pct_change,
                    two_week_change=two_week_change,
                    three_week_change=three_week_change,
                    four_week_change=four_week_change,
                    five_week_change=five_week_change,
                    six_week_change=six_week_change,
                    seven_week_change=seven_week_change,
                    eight_week_change=eight_week_change,
                    nine_week_change=nine_week_change,
                    ten_week_change=ten_week_change,
                    sentiment=sentiment
                )
                general_data.save()
                print("Saved")
            except Exception as e:
                print(e)
                input(data)


def regroup_by_symbol(important_data):
    # Group the dataframe by 'Symbol'
    grouped_data = important_data.groupby('date')

    # Create a dictionary to store dataframes for each symbol
    symbol_dataframes = {}

    # Iterate through the groups and store each group's dataframe in the dictionary
    for symbol, group in grouped_data:
        symbol_dataframes[symbol] = group.reset_index(drop=True)

    return symbol_dataframes


def execute():
    start_year = 2005
    end_year = 2024
    final_data = main(start_year, end_year)
    analyzed_data = filter_and_analyze_legacy_data(final_data)
    important_headers = [
        'date',
        'pair',
        'base_long',
        'base_short',
        'base_net_position',
        'quote_long',
        'quote_short',
        'quote_net_position',
        'base_comm_long',
        'base_comm_short',
        'base_comm_net_position',
        'quote_comm_long',
        'quote_comm_short',
        'quote_comm_net_position',
        'base_nonrep_long',
        'base_nonrep_short',
        'base_nonrep_net_position',
        'quote_nonrep_long',
        'quote_nonrep_short',
        'quote_nonrep_net_position',
        # Noncommercial Positions-Long (All) for the pair
        'pair_long',
        # Noncommercial Positions-Short (All) for the pair
        'pair_short',
        'pair_net_position',
        'pct_change',
        '2_week_change',
        '3_week_change',
        '4_week_change',
        '5_week_change',
        '6_week_change',
        '7_week_change',
        '8_week_change',
        '9_week_change',
        '10_week_change',
        'sentiment'
    ]
    important_data = analyzed_data[important_headers]
    symbol_dataframes = regroup_by_symbol(important_data)
    save_to_django_models(symbol_dataframes)
