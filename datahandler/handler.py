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
        'Change in Commercial-Short (All)',
        'Change in Nonreportable-Long (All)',
        'Change in Nonreportable-Short (All)'
    ]

    # Filter the dataframe
    filtered_legacy_df = legacy_report[important_headers]
    filtered_legacy_df["Symbol"] = filtered_legacy_df[important_headers[0]].str.split(
        " ").str[0]
    filtered_legacy_df = filtered_legacy_df[filtered_legacy_df['Market and Exchange Names'].isin(
        relevant_contracts)]
    return filtered_legacy_df


def calculate_net_positions_old(df):
    df['Net_Noncommercial_Positions'] = df['Change in Noncommercial-Long (All)'] - \
        df['Change in Noncommercial-Short (All)']
    df['Net_Commercial_Positions'] = df['Change in Commercial-Long (All)'] - \
        df['Change in Commercial-Short (All)']
    df['Net_Nonreportable_Positions'] = df['Change in Nonreportable-Long (All)'] - \
        df['Change in Nonreportable-Short (All)']
    return df

# Assuming the columns contain string representations of numbers


def calculate_net_positions(df):
    for col in ['Noncommercial', 'Commercial', 'Nonreportable']:
        long_col = f'Change in {col}-Long (All)'
        short_col = f'Change in {col}-Short (All)'
        net_col = f'Net_{col}_Positions'

        # Try converting to numeric, handling errors with 'coerce'
        try:
            df[long_col] = pd.to_numeric(df[long_col], errors='coerce')
            df[short_col] = pd.to_numeric(df[short_col], errors='coerce')
        except:
            # Handle potential conversion errors (e.g., print a message)
            print(
                f"Error converting columns {long_col} and {short_col} to numeric.")

        # Now the subtraction should work (ignoring rows with conversion errors)
        df[net_col] = df[long_col] - df[short_col]

    return df


def calculate_percentage_change(df, prefix, base, quote, isContract=False):
    df[f'{prefix}_pct_change'] = (
        (df[f'{prefix}_net_position'] - df[f'{prefix}_net_position'].shift(1)) / df[f'{prefix}_net_position'].shift(1)) * 100
    return df


def calculate_5_week_avg_change(df, window, prefix):
    df[f'{prefix}_{window}_week_change'] = df[f'{prefix}_pct_change'].rolling(
        window=window).sum()  # .mean()
    return df


def calculate_5_week_avg_change_open(df, window, prefix):
    df[f'{prefix}_{window}_week_change_open_interest'] = df[f'{prefix}_pct_change_open_interest'].rolling(
        window=window).sum()  # .mean()
    return df


def calculate_5_week_avg_diff_absolute(df, window, prefix, suff):
    df[f'{prefix}_{window}_diff_absolute_{suff}'] = df[f'{prefix}_diff_absolute_{suff}'].rolling(
        window=window).sum()  # .mean()
    return df


def convert_to_numeric(df):
    """Converts specified columns in a DataFrame to numeric data types.

    Args:
        df (pandas.DataFrame): The DataFrame containing the columns to convert.

    Returns:
        pandas.DataFrame: The DataFrame with the specified columns converted to numeric.
    """

    # Columns to convert (modify this list as needed)
    numeric_cols = [
        'base_open_interest',
        'base_change_open_interest',
        'quote_open_interest',
        'quote_change_open_interest',
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
    ]

    # Try converting columns to numeric, handling errors with 'coerce'
    for col in numeric_cols:
        try:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        except:
            # Handle potential conversion errors (e.g., print a message)
            print(f"Error converting column {col} to numeric.")

    return df


def analyze_legacy_df(legacy_df, currency_pairs, isContract=False):
    print("analyzing")
    print(isContract)
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
            'Open Interest (All)_base': 'base_open_interest',
            'Change in Open Interest (All)_base': 'base_change_open_interest',
            'Open Interest (All)_quote': 'quote_open_interest',
            'Change in Open Interest (All)_quote': 'quote_change_open_interest',
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
        merged_df = convert_to_numeric(merged_df.copy())

        # Add pair information

        # print(f'Pair : {currency_to_symbol[base_currency]}/{currency_to_symbol[quote_currency]}')
        print("before check")

        if not isContract:

            pair = f'{currency_to_symbol[base_currency]}/{currency_to_symbol[quote_currency]}'
            print(pair)
            merged_df['pair'] = pair
            merged_df['noncomm_diff_absolute_long'] = ((merged_df["base_long"] / merged_df["base_open_interest"]) * 100) - (
                (merged_df["quote_long"] / merged_df["quote_open_interest"]) * 100)
            merged_df['noncomm_diff_absolute_short'] = ((merged_df["base_short"] / merged_df["base_open_interest"]) * 100) - (
                (merged_df["quote_short"] / merged_df["quote_open_interest"]) * 100)
            merged_df['comm_diff_absolute_long'] = ((merged_df["base_comm_long"] / merged_df["base_open_interest"]) * 100) - (
                (merged_df["quote_comm_long"] / merged_df["quote_open_interest"]) * 100)
            merged_df['comm_diff_absolute_short'] = ((merged_df["base_comm_short"] / merged_df["base_open_interest"]) * 100) - (
                (merged_df["quote_comm_short"] / merged_df["quote_open_interest"]) * 100)
            # Calculate pair positions based on the given rules
            if currency_to_symbol[quote_currency] == "USD":
                print('quote issue')
                merged_df['pair_long'] = merged_df['base_long']
                merged_df['pair_short'] = merged_df['base_short']
                merged_df['pair_pct_change'] = (
                    merged_df['base_net_position'] / (merged_df['base_long'] + merged_df['base_short'])) * 100
                merged_df['pair_comm_pct_change'] = (merged_df['base_comm_net_position'] / (
                    merged_df['base_comm_long'] + merged_df['base_comm_short'])) * 100
                merged_df['pair_open_interest'] = merged_df['base_open_interest']
                merged_df['pair_pct_change_open_interest'] = (
                    merged_df['base_change_open_interest'] / merged_df['base_open_interest']) * 100
            elif currency_to_symbol[base_currency] == "USD":
                merged_df['pair_long'] = merged_df['quote_short']
                merged_df['pair_short'] = merged_df['quote_long']
                print('base issue')
                merged_df['pair_pct_change'] = (-merged_df['quote_net_position'] / (
                    merged_df['quote_long'] + merged_df['quote_short'])) * 100
                merged_df['pair_comm_pct_change'] = (-merged_df['quote_comm_net_position'] / (
                    merged_df['quote_comm_long'] + merged_df['quote_comm_short'])) * 100
                merged_df['pair_open_interest'] = merged_df['quote_open_interest']

                merged_df['pair_pct_change_open_interest'] = (
                    -merged_df['quote_change_open_interest'] / merged_df['quote_open_interest']) * 100
            else:
                merged_df['pair_long'] = merged_df['base_long']
                merged_df['pair_short'] = merged_df['base_short']
                merged_df['pair_pct_change'] = ((merged_df['base_net_position'] / (merged_df['base_long'] + merged_df['base_short'])) - (
                    merged_df['quote_net_position'] / (merged_df['quote_long'] + merged_df['quote_short']))) * 100
                merged_df['pair_comm_pct_change'] = ((merged_df['base_comm_net_position'] / (merged_df['base_comm_long'] + merged_df['base_comm_short'])) - (
                    merged_df['quote_comm_net_position'] / (merged_df['quote_comm_long'] + merged_df['quote_comm_short']))) * 100
                merged_df['pair_open_interest'] = merged_df['base_open_interest']
                merged_df['pair_pct_change_open_interest'] = ((merged_df['base_change_open_interest'] / merged_df['base_open_interest']) - (
                    merged_df['quote_change_open_interest'] / merged_df['quote_open_interest'])) * 100

        else:
            pair = f'{currency_to_symbol[base_currency]}'
            print(f'Pair is {pair}')
            merged_df['pair'] = pair
            merged_df['pair_long'] = merged_df['base_long']
            merged_df['pair_short'] = merged_df['base_short']
            merged_df['pair_pct_change'] = (
                merged_df['base_net_position'] / (merged_df['base_long'] + merged_df['base_short'])) * 100
            merged_df['pair_comm_pct_change'] = (merged_df['base_comm_net_position'] / (
                merged_df['base_comm_long'] + merged_df['base_comm_short'])) * 100
            merged_df['pair_open_interest'] = merged_df['base_open_interest']
            merged_df['pair_pct_change_open_interest'] = (
                merged_df['base_change_open_interest'] / merged_df['base_open_interest']) * 100
            merged_df['noncomm_diff_absolute_long'] = ((merged_df["base_long"] / merged_df["base_open_interest"]) * 100) - (
                (merged_df["quote_long"] / merged_df["quote_open_interest"]) * 100)
            merged_df['noncomm_diff_absolute_short'] = ((merged_df["base_short"] / merged_df["base_open_interest"]) * 100) - (
                (merged_df["quote_short"] / merged_df["quote_open_interest"]) * 100)
            merged_df['comm_diff_absolute_long'] = ((merged_df["base_comm_long"] / merged_df["base_open_interest"]) * 100) - (
                (merged_df["quote_comm_long"] / merged_df["quote_open_interest"]) * 100)
            merged_df['comm_diff_absolute_short'] = ((merged_df["base_comm_short"] / merged_df["base_open_interest"]) * 100) - (
                (merged_df["quote_comm_short"] / merged_df["quote_open_interest"]) * 100)

        # Calculate percentage changes for base, quote, and pair net positions
        # merged_df = calculate_percentage_change(merged_df,"pair")
        # merged_df = calculate_percentage_change(merged_df,"base")
        # merged_df = calculate_percentage_change(merged_df,"quote")

        # Calculate 5-week average percentage change
        for i in range(2, 11):
            merged_df = calculate_5_week_avg_change(merged_df, i, "pair")
            merged_df = calculate_5_week_avg_change(merged_df, i, "pair_comm")
            merged_df = calculate_5_week_avg_diff_absolute(
                merged_df, i, "noncomm", "long")
            merged_df = calculate_5_week_avg_diff_absolute(
                merged_df, i, "noncomm", "short")
            merged_df = calculate_5_week_avg_diff_absolute(
                merged_df, i, "comm", "long")
            merged_df = calculate_5_week_avg_diff_absolute(
                merged_df, i, "comm", "short")
        for i in range(2, 11):
            merged_df = calculate_5_week_avg_change_open(merged_df, i, "pair")

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
        merged_df['isContract'] = isContract

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
    general_headers = [
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
    ]

    pct_change_position_headers = [
        'pair_pct_change',
        'pair_comm_pct_change',
        'pair_2_week_change',
        'pair_3_week_change',
        'pair_4_week_change',
        'pair_5_week_change',
        'pair_6_week_change',
        'pair_7_week_change',
        'pair_8_week_change',
        'pair_9_week_change',
        'pair_10_week_change',
        'pair_comm_2_week_change',
        'pair_comm_3_week_change',
        'pair_comm_4_week_change',
        'pair_comm_5_week_change',
        'pair_comm_6_week_change',
        'pair_comm_7_week_change',
        'pair_comm_8_week_change',
        'pair_comm_9_week_change',
        'pair_comm_10_week_change',
    ]

    pct_change_open_interest = [
        'pair_pct_change_open_interest',
        'pair_2_week_change_open_interest',
        'pair_3_week_change_open_interest',
        'pair_4_week_change_open_interest',
        'pair_5_week_change_open_interest',
        'pair_6_week_change_open_interest',
        'pair_7_week_change_open_interest',
        'pair_8_week_change_open_interest',
        'pair_9_week_change_open_interest',
        'pair_10_week_change_open_interest',
    ]

    pct_change_diff_absolute_noncomm = [
        'noncomm_diff_absolute_long',
        'noncomm_diff_absolute_short',
        'noncomm_2_diff_absolute_long',
        'noncomm_3_diff_absolute_long',
        'noncomm_4_diff_absolute_long',
        'noncomm_5_diff_absolute_long',
        'noncomm_6_diff_absolute_long',
        'noncomm_7_diff_absolute_long',
        'noncomm_8_diff_absolute_long',
        'noncomm_9_diff_absolute_long',
        'noncomm_10_diff_absolute_long',
        'noncomm_2_diff_absolute_short',
        'noncomm_3_diff_absolute_short',
        'noncomm_4_diff_absolute_short',
        'noncomm_5_diff_absolute_short',
        'noncomm_6_diff_absolute_short',
        'noncomm_7_diff_absolute_short',
        'noncomm_8_diff_absolute_short',
        'noncomm_9_diff_absolute_short',
        'noncomm_10_diff_absolute_short'
    ]

    pct_change_diff_absolute_comm = [
        'comm_diff_absolute_long',
        'comm_diff_absolute_short',
        'comm_2_diff_absolute_long',
        'comm_3_diff_absolute_long',
        'comm_4_diff_absolute_long',
        'comm_5_diff_absolute_long',
        'comm_6_diff_absolute_long',
        'comm_7_diff_absolute_long',
        'comm_8_diff_absolute_long',
        'comm_9_diff_absolute_long',
        'comm_10_diff_absolute_long',
        'comm_2_diff_absolute_short',
        'comm_3_diff_absolute_short',
        'comm_4_diff_absolute_short',
        'comm_5_diff_absolute_short',
        'comm_6_diff_absolute_short',
        'comm_7_diff_absolute_short',
        'comm_8_diff_absolute_short',
        'comm_9_diff_absolute_short',
        'comm_10_diff_absolute_short'
    ]

    extras_headers = [
        'sentiment',
        'isContract'
    ]

    important_headers = general_headers + pct_change_diff_absolute_comm + \
        pct_change_diff_absolute_noncomm + \
        pct_change_open_interest + pct_change_position_headers + extras_headers

    # Process all currency pairs
    legacy_df = filter_legacy_df(final_data)
   # Process all currency pairs
    combined_df1 = analyze_legacy_df(
        filtered_legacy_df, all_currency_pairs).fillna(0)
    combined_df2 = analyze_legacy_df(
        filtered_legacy_df, contracts, isContract=True).fillna(0)
    combined_df = pd.concat([combined_df1, combined_df2], ignore_index=True)
    res = combined_df.sort_values(by='date')  # [important_headers]
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
    reports_type = ['legacy_fut']
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

                # Extract and handle all necessary fields
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

                # Extract percentage change headers
                pair_pct_change = data.get('pair_pct_change', 0) or 0
                pair_comm_pct_change = data.get('pair_comm_pct_change', 0) or 0
                pair_2_week_change = data.get('pair_2_week_change', 0) or 0
                pair_3_week_change = data.get('pair_3_week_change', 0) or 0
                pair_4_week_change = data.get('pair_4_week_change', 0) or 0
                pair_5_week_change = data.get('pair_5_week_change', 0) or 0
                pair_6_week_change = data.get('pair_6_week_change', 0) or 0
                pair_7_week_change = data.get('pair_7_week_change', 0) or 0
                pair_8_week_change = data.get('pair_8_week_change', 0) or 0
                pair_9_week_change = data.get('pair_9_week_change', 0) or 0
                pair_10_week_change = data.get('pair_10_week_change', 0) or 0
                pair_comm_2_week_change = data.get(
                    'pair_comm_2_week_change', 0) or 0
                pair_comm_3_week_change = data.get(
                    'pair_comm_3_week_change', 0) or 0
                pair_comm_4_week_change = data.get(
                    'pair_comm_4_week_change', 0) or 0
                pair_comm_5_week_change = data.get(
                    'pair_comm_5_week_change', 0) or 0
                pair_comm_6_week_change = data.get(
                    'pair_comm_6_week_change', 0) or 0
                pair_comm_7_week_change = data.get(
                    'pair_comm_7_week_change', 0) or 0
                pair_comm_8_week_change = data.get(
                    'pair_comm_8_week_change', 0) or 0
                pair_comm_9_week_change = data.get(
                    'pair_comm_9_week_change', 0) or 0
                pair_comm_10_week_change = data.get(
                    'pair_comm_10_week_change', 0) or 0

                # Extract open interest headers
                pair_pct_change_open_interest = data.get(
                    'pair_pct_change_open_interest', 0) or 0
                pair_2_week_change_open_interest = data.get(
                    'pair_2_week_change_open_interest', 0) or 0
                pair_3_week_change_open_interest = data.get(
                    'pair_3_week_change_open_interest', 0) or 0
                pair_4_week_change_open_interest = data.get(
                    'pair_4_week_change_open_interest', 0) or 0
                pair_5_week_change_open_interest = data.get(
                    'pair_5_week_change_open_interest', 0) or 0
                pair_6_week_change_open_interest = data.get(
                    'pair_6_week_change_open_interest', 0) or 0
                pair_7_week_change_open_interest = data.get(
                    'pair_7_week_change_open_interest', 0) or 0
                pair_8_week_change_open_interest = data.get(
                    'pair_8_week_change_open_interest', 0) or 0
                pair_9_week_change_open_interest = data.get(
                    'pair_9_week_change_open_interest', 0) or 0
                pair_10_week_change_open_interest = data.get(
                    'pair_10_week_change_open_interest', 0) or 0

                # Extract noncommercial diff absolute headers
                noncomm_diff_absolute_long = data.get(
                    'noncomm_diff_absolute_long', 0) or 0
                noncomm_diff_absolute_short = data.get(
                    'noncomm_diff_absolute_short', 0) or 0
                noncomm_2_diff_absolute_long = data.get(
                    'noncomm_2_diff_absolute_long', 0) or 0
                noncomm_3_diff_absolute_long = data.get(
                    'noncomm_3_diff_absolute_long', 0) or 0
                noncomm_4_diff_absolute_long = data.get(
                    'noncomm_4_diff_absolute_long', 0) or 0
                noncomm_5_diff_absolute_long = data.get(
                    'noncomm_5_diff_absolute_long', 0) or 0
                noncomm_6_diff_absolute_long = data.get(
                    'noncomm_6_diff_absolute_long', 0) or 0
                noncomm_7_diff_absolute_long = data.get(
                    'noncomm_7_diff_absolute_long', 0) or 0
                noncomm_8_diff_absolute_long = data.get(
                    'noncomm_8_diff_absolute_long', 0) or 0
                noncomm_9_diff_absolute_long = data.get(
                    'noncomm_9_diff_absolute_long', 0) or 0
                noncomm_10_diff_absolute_long = data.get(
                    'noncomm_10_diff_absolute_long', 0) or 0
                noncomm_2_diff_absolute_short = data.get(
                    'noncomm_2_diff_absolute_short', 0) or 0
                noncomm_3_diff_absolute_short = data.get(
                    'noncomm_3_diff_absolute_short', 0) or 0
                noncomm_4_diff_absolute_short = data.get(
                    'noncomm_4_diff_absolute_short', 0) or 0
                noncomm_5_diff_absolute_short = data.get(
                    'noncomm_5_diff_absolute_short', 0) or 0
                noncomm_6_diff_absolute_short = data.get(
                    'noncomm_6_diff_absolute_short', 0) or 0
                noncomm_7_diff_absolute_short = data.get(
                    'noncomm_7_diff_absolute_short', 0) or 0
                noncomm_8_diff_absolute_short = data.get(
                    'noncomm_8_diff_absolute_short', 0) or 0
                noncomm_9_diff_absolute_short = data.get(
                    'noncomm_9_diff_absolute_short', 0) or 0
                noncomm_10_diff_absolute_short = data.get(
                    'noncomm_10_diff_absolute_short', 0) or 0

                # Extract commercial diff absolute headers
                comm_diff_absolute_long = data.get(
                    'comm_diff_absolute_long', 0) or 0
                comm_diff_absolute_short = data.get(
                    'comm_diff_absolute_short', 0) or 0
                comm_2_diff_absolute_long = data.get(
                    'comm_2_diff_absolute_long', 0) or 0
                comm_3_diff_absolute_long = data.get(
                    'comm_3_diff_absolute_long', 0) or 0
                comm_4_diff_absolute_long = data.get(
                    'comm_4_diff_absolute_long', 0) or 0
                comm_5_diff_absolute_long = data.get(
                    'comm_5_diff_absolute_long', 0) or 0
                comm_6_diff_absolute_long = data.get(
                    'comm_6_diff_absolute_long', 0) or 0
                comm_7_diff_absolute_long = data.get(
                    'comm_7_diff_absolute_long', 0) or 0
                comm_8_diff_absolute_long = data.get(
                    'comm_8_diff_absolute_long', 0) or 0
                comm_9_diff_absolute_long = data.get(
                    'comm_9_diff_absolute_long', 0) or 0
                comm_10_diff_absolute_long = data.get(
                    'comm_10_diff_absolute_long', 0) or 0
                comm_2_diff_absolute_short = data.get(
                    'comm_2_diff_absolute_short', 0) or 0
                comm_3_diff_absolute_short = data.get(
                    'comm_3_diff_absolute_short', 0) or 0
                comm_4_diff_absolute_short = data.get(
                    'comm_4_diff_absolute_short', 0) or 0
                comm_5_diff_absolute_short = data.get(
                    'comm_5_diff_absolute_short', 0) or 0
                comm_6_diff_absolute_short = data.get(
                    'comm_6_diff_absolute_short', 0) or 0
                comm_7_diff_absolute_short = data.get(
                    'comm_7_diff_absolute_short', 0) or 0
                comm_8_diff_absolute_short = data.get(
                    'comm_8_diff_absolute_short', 0) or 0
                comm_9_diff_absolute_short = data.get(
                    'comm_9_diff_absolute_short', 0) or 0
                comm_10_diff_absolute_short = data.get(
                    'comm_10_diff_absolute_short', 0) or 0

                # Extract extra headers
                sentiment = data.get('sentiment', 'Neutral')
                is_contract = data.get('isContract', False)

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
                    pair_pct_change=pair_pct_change,
                    pair_comm_pct_change=pair_comm_pct_change,
                    pair_2_week_change=pair_2_week_change,
                    pair_3_week_change=pair_3_week_change,
                    pair_4_week_change=pair_4_week_change,
                    pair_5_week_change=pair_5_week_change,
                    pair_6_week_change=pair_6_week_change,
                    pair_7_week_change=pair_7_week_change,
                    pair_8_week_change=pair_8_week_change,
                    pair_9_week_change=pair_9_week_change,
                    pair_10_week_change=pair_10_week_change,
                    pair_comm_2_week_change=pair_comm_2_week_change,
                    pair_comm_3_week_change=pair_comm_3_week_change,
                    pair_comm_4_week_change=pair_comm_4_week_change,
                    pair_comm_5_week_change=pair_comm_5_week_change,
                    pair_comm_6_week_change=pair_comm_6_week_change,
                    pair_comm_7_week_change=pair_comm_7_week_change,
                    pair_comm_8_week_change=pair_comm_8_week_change,
                    pair_comm_9_week_change=pair_comm_9_week_change,
                    pair_comm_10_week_change=pair_comm_10_week_change,
                    pair_pct_change_open_interest=pair_pct_change_open_interest,
                    pair_2_week_change_open_interest=pair_2_week_change_open_interest,
                    pair_3_week_change_open_interest=pair_3_week_change_open_interest,
                    pair_4_week_change_open_interest=pair_4_week_change_open_interest,
                    pair_5_week_change_open_interest=pair_5_week_change_open_interest,
                    pair_6_week_change_open_interest=pair_6_week_change_open_interest,
                    pair_7_week_change_open_interest=pair_7_week_change_open_interest,
                    pair_8_week_change_open_interest=pair_8_week_change_open_interest,
                    pair_9_week_change_open_interest=pair_9_week_change_open_interest,
                    pair_10_week_change_open_interest=pair_10_week_change_open_interest,
                    noncomm_diff_absolute_long=noncomm_diff_absolute_long,
                    noncomm_diff_absolute_short=noncomm_diff_absolute_short,
                    noncomm_2_diff_absolute_long=noncomm_2_diff_absolute_long,
                    noncomm_3_diff_absolute_long=noncomm_3_diff_absolute_long,
                    noncomm_4_diff_absolute_long=noncomm_4_diff_absolute_long,
                    noncomm_5_diff_absolute_long=noncomm_5_diff_absolute_long,
                    noncomm_6_diff_absolute_long=noncomm_6_diff_absolute_long,
                    noncomm_7_diff_absolute_long=noncomm_7_diff_absolute_long,
                    noncomm_8_diff_absolute_long=noncomm_8_diff_absolute_long,
                    noncomm_9_diff_absolute_long=noncomm_9_diff_absolute_long,
                    noncomm_10_diff_absolute_long=noncomm_10_diff_absolute_long,
                    noncomm_2_diff_absolute_short=noncomm_2_diff_absolute_short,
                    noncomm_3_diff_absolute_short=noncomm_3_diff_absolute_short,
                    noncomm_4_diff_absolute_short=noncomm_4_diff_absolute_short,
                    noncomm_5_diff_absolute_short=noncomm_5_diff_absolute_short,
                    noncomm_6_diff_absolute_short=noncomm_6_diff_absolute_short,
                    noncomm_7_diff_absolute_short=noncomm_7_diff_absolute_short,
                    noncomm_8_diff_absolute_short=noncomm_8_diff_absolute_short,
                    noncomm_9_diff_absolute_short=noncomm_9_diff_absolute_short,
                    noncomm_10_diff_absolute_short=noncomm_10_diff_absolute_short,
                    comm_diff_absolute_long=comm_diff_absolute_long,
                    comm_diff_absolute_short=comm_diff_absolute_short,
                    comm_2_diff_absolute_long=comm_2_diff_absolute_long,
                    comm_3_diff_absolute_long=comm_3_diff_absolute_long,
                    comm_4_diff_absolute_long=comm_4_diff_absolute_long,
                    comm_5_diff_absolute_long=comm_5_diff_absolute_long,
                    comm_6_diff_absolute_long=comm_6_diff_absolute_long,
                    comm_7_diff_absolute_long=comm_7_diff_absolute_long,
                    comm_8_diff_absolute_long=comm_8_diff_absolute_long,
                    comm_9_diff_absolute_long=comm_9_diff_absolute_long,
                    comm_10_diff_absolute_long=comm_10_diff_absolute_long,
                    comm_2_diff_absolute_short=comm_2_diff_absolute_short,
                    comm_3_diff_absolute_short=comm_3_diff_absolute_short,
                    comm_4_diff_absolute_short=comm_4_diff_absolute_short,
                    comm_5_diff_absolute_short=comm_5_diff_absolute_short,
                    comm_6_diff_absolute_short=comm_6_diff_absolute_short,
                    comm_7_diff_absolute_short=comm_7_diff_absolute_short,
                    comm_8_diff_absolute_short=comm_8_diff_absolute_short,
                    comm_9_diff_absolute_short=comm_9_diff_absolute_short,
                    comm_10_diff_absolute_short=comm_10_diff_absolute_short,
                    sentiment=sentiment,
                    is_contract=is_contract
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
    general_headers = [
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
    ]

    pct_change_position_headers = [
        'pair_pct_change',
        'pair_comm_pct_change',
        'pair_2_week_change',
        'pair_3_week_change',
        'pair_4_week_change',
        'pair_5_week_change',
        'pair_6_week_change',
        'pair_7_week_change',
        'pair_8_week_change',
        'pair_9_week_change',
        'pair_10_week_change',
        'pair_comm_2_week_change',
        'pair_comm_3_week_change',
        'pair_comm_4_week_change',
        'pair_comm_5_week_change',
        'pair_comm_6_week_change',
        'pair_comm_7_week_change',
        'pair_comm_8_week_change',
        'pair_comm_9_week_change',
        'pair_comm_10_week_change',
    ]

    pct_change_open_interest = [
        'pair_pct_change_open_interest',
        'pair_2_week_change_open_interest',
        'pair_3_week_change_open_interest',
        'pair_4_week_change_open_interest',
        'pair_5_week_change_open_interest',
        'pair_6_week_change_open_interest',
        'pair_7_week_change_open_interest',
        'pair_8_week_change_open_interest',
        'pair_9_week_change_open_interest',
        'pair_10_week_change_open_interest',
    ]

    pct_change_diff_absolute_noncomm = [
        'noncomm_diff_absolute_long',
        'noncomm_diff_absolute_short',
        'noncomm_2_diff_absolute_long',
        'noncomm_3_diff_absolute_long',
        'noncomm_4_diff_absolute_long',
        'noncomm_5_diff_absolute_long',
        'noncomm_6_diff_absolute_long',
        'noncomm_7_diff_absolute_long',
        'noncomm_8_diff_absolute_long',
        'noncomm_9_diff_absolute_long',
        'noncomm_10_diff_absolute_long',
        'noncomm_2_diff_absolute_short',
        'noncomm_3_diff_absolute_short',
        'noncomm_4_diff_absolute_short',
        'noncomm_5_diff_absolute_short',
        'noncomm_6_diff_absolute_short',
        'noncomm_7_diff_absolute_short',
        'noncomm_8_diff_absolute_short',
        'noncomm_9_diff_absolute_short',
        'noncomm_10_diff_absolute_short'
    ]

    pct_change_diff_absolute_comm = [
        'comm_diff_absolute_long',
        'comm_diff_absolute_short',
        'comm_2_diff_absolute_long',
        'comm_3_diff_absolute_long',
        'comm_4_diff_absolute_long',
        'comm_5_diff_absolute_long',
        'comm_6_diff_absolute_long',
        'comm_7_diff_absolute_long',
        'comm_8_diff_absolute_long',
        'comm_9_diff_absolute_long',
        'comm_10_diff_absolute_long',
        'comm_2_diff_absolute_short',
        'comm_3_diff_absolute_short',
        'comm_4_diff_absolute_short',
        'comm_5_diff_absolute_short',
        'comm_6_diff_absolute_short',
        'comm_7_diff_absolute_short',
        'comm_8_diff_absolute_short',
        'comm_9_diff_absolute_short',
        'comm_10_diff_absolute_short'
    ]

    extras_headers = [
        'sentiment',
        'isContract'
    ]

    important_headers = general_headers + pct_change_diff_absolute_comm + \
        pct_change_diff_absolute_noncomm + \
        pct_change_open_interest + pct_change_position_headers + extras_headers

    important_data = analyzed_data[important_headers]
    symbol_dataframes = regroup_by_symbol(important_data)
    save_to_django_models(symbol_dataframes)
