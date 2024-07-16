import cot_reports as cot
import pandas as pd
import numpy as np
import json
from .models import DateInterval, Data
from django.utils.timezone import make_aware


def filter_tff_df(final_data):
    # Filter the TFF report
    tff_report = final_data.copy()
    important_columns_tff = [
        'Market_and_Exchange_Names',
        'Report_Date_as_YYYY-MM-DD',
        'Open_Interest_All',
        'Dealer_Positions_Long_All',
        'Dealer_Positions_Short_All',
        'Asset_Mgr_Positions_Long_All',
        'Asset_Mgr_Positions_Short_All',
        'Lev_Money_Positions_Long_All',
        'Lev_Money_Positions_Short_All',
        'Other_Rept_Positions_Long_All',
        'Other_Rept_Positions_Short_All',
        'Tot_Rept_Positions_Long_All',
        'Tot_Rept_Positions_Short_All',
        'NonRept_Positions_Long_All',
        'NonRept_Positions_Short_All',
        'Conc_Gross_LE_4_TDR_Long_All',
        'Conc_Gross_LE_4_TDR_Short_All',
        'Conc_Gross_LE_8_TDR_Long_All',
        'Conc_Gross_LE_8_TDR_Short_All',
        'Conc_Net_LE_4_TDR_Long_All',
        'Conc_Net_LE_4_TDR_Short_All',
        'Conc_Net_LE_8_TDR_Long_All',
        'Conc_Net_LE_8_TDR_Short_All',
        'date'
    ]

    # Filter the dataframe
    filtered_tff_df = tff_report[important_columns_tff]
    filtered_tff_df["Symbol"] = filtered_tff_df['Market_and_Exchange_Names'].str.split(
        " - ").str[0]
    return filtered_tff_df


def analyze_tff_df(tff_df):
    # Convert date to datetime format if necessary
    tff_df['Report_Date_as_YYYY-MM-DD'] = pd.to_datetime(
        tff_df['Report_Date_as_YYYY-MM-DD'])

    # Calculate Net Positions
    tff_df['Net_Dealer_Positions'] = tff_df['Dealer_Positions_Long_All'] - \
        tff_df['Dealer_Positions_Short_All']
    tff_df['Net_Asset_Mgr_Positions'] = tff_df['Asset_Mgr_Positions_Long_All'] - \
        tff_df['Asset_Mgr_Positions_Short_All']
    tff_df['Net_Lev_Money_Positions'] = tff_df['Lev_Money_Positions_Long_All'] - \
        tff_df['Lev_Money_Positions_Short_All']
    tff_df['Net_Other_Rept_Positions'] = tff_df['Other_Rept_Positions_Long_All'] - \
        tff_df['Other_Rept_Positions_Short_All']
    tff_df['Net_NonRept_Positions'] = tff_df['NonRept_Positions_Long_All'] - \
        tff_df['NonRept_Positions_Short_All']

    # Calculate Sentiment Score
    tff_df['Sentiment_Score'] = (tff_df['Net_Dealer_Positions'] +
                                 tff_df['Net_Asset_Mgr_Positions'] +
                                 tff_df['Net_Lev_Money_Positions'] +
                                 tff_df['Net_Other_Rept_Positions'] +
                                 tff_df['Net_NonRept_Positions']) / tff_df['Open_Interest_All']

    # Calculate 7-Day Moving Average of Sentiment Score
    tff_df['Sentiment_7Day_MA'] = tff_df['Sentiment_Score'].rolling(
        window=7).mean()

    # Define Buy/Sell Signal Thresholds (adjusted for small values)
    mean_sentiment_score = tff_df['Sentiment_Score'].mean()
    std_sentiment_score = tff_df['Sentiment_Score'].std()

    buy_threshold = mean_sentiment_score + 2 * std_sentiment_score
    sell_threshold = mean_sentiment_score - 2 * std_sentiment_score

    # Calculate Buy/Sell Signals
    tff_df['Buy_Signal'] = np.where(
        tff_df['Sentiment_Score'] > buy_threshold, 1, 0)
    tff_df['Sell_Signal'] = np.where(
        tff_df['Sentiment_Score'] < sell_threshold, 1, 0)
    tff_df['Decision'] = np.where(tff_df['Buy_Signal'] == 1, 'Buy',
                                  np.where(tff_df['Sell_Signal'] == 1, 'Sell', 'Neutral'))

    # Calculate crowded positions
    tff_df['Crowded_Long_Positions'] = tff_df['Conc_Gross_LE_4_TDR_Long_All'] + \
        tff_df['Conc_Gross_LE_8_TDR_Long_All']
    tff_df['Crowded_Short_Positions'] = tff_df['Conc_Gross_LE_4_TDR_Short_All'] + \
        tff_df['Conc_Gross_LE_8_TDR_Short_All']

    # Calculate Speculative Positioning Index (SPI)
    tff_df['Speculative_Positioning_Index'] = (
        tff_df['Lev_Money_Positions_Long_All'] - tff_df['Lev_Money_Positions_Short_All']) / tff_df['Open_Interest_All']

    # Calculate Commitment of Traders Ratio (COT Ratio)
    tff_df['COT_Ratio'] = (tff_df['Dealer_Positions_Long_All'] + tff_df['Dealer_Positions_Short_All']) / \
        (tff_df['Asset_Mgr_Positions_Long_All'] +
         tff_df['Asset_Mgr_Positions_Short_All'])

    # Calculate Net Speculative Position
    tff_df['Net_Speculative_Position'] = tff_df['Lev_Money_Positions_Long_All'] - \
        tff_df['Lev_Money_Positions_Short_All']

    # Calculate Commercial/Non-Commercial Positioning Ratio
    tff_df['Comm_NonComm_Ratio'] = (tff_df['Dealer_Positions_Long_All'] + tff_df['Dealer_Positions_Short_All']) / (
        tff_df['Lev_Money_Positions_Long_All'] + tff_df['Lev_Money_Positions_Short_All'])

    # Calculate Percentage of Open Interest by Speculative Positions
    tff_df['Pct_OI_Spec_Positions'] = ((tff_df['Lev_Money_Positions_Long_All'] +
                                       tff_df['Lev_Money_Positions_Short_All']) / tff_df['Open_Interest_All']) * 100

    # Calculate overall decision and sentiment
    overall_sentiment_threshold = 0.1
    tff_df['Overall_Sentiment'] = tff_df['Sentiment_Score'].mean()
    tff_df['Overall_Decision'] = np.where(tff_df['Overall_Sentiment'] > overall_sentiment_threshold, 'Buy',
                                          np.where(tff_df['Overall_Sentiment'] < -overall_sentiment_threshold, 'Sell', 'Neutral'))

    tff_df = tff_df.fillna(0)
    # Display results
    return tff_df


def filter_and_analyze_tff_data(final_data):
    tff_df = filter_tff_df(final_data)
    analyzed_tff_df = analyze_tff_df(tff_df)
    # print(analyzed_tff_df.head()[["Symbol", "Decision", 'Sentiment_Score', 'Crowded_Long_Positions', 'Crowded_Short_Positions']])
    return analyzed_tff_df

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
    reports_type = ['traders_in_financial_futures_fut']
    date_header = ['As_of_Date_In_Form_YYMMDD']
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
                if not data['COT_Ratio']:
                    data['COT_Ratio'] = 0
                date = data['date']
                date_obj = make_aware(pd.to_datetime(date, unit='ms'))
                print(f"Date is {date_obj}")
                date_interval, created = DateInterval.objects.get_or_create(
                    date=date_obj)
                date_interval.save()

                data = Data.objects.create(
                    date_interval=date_interval,
                    symbol=data['Symbol'],
                    decision=data['Decision'],
                    sentiment_score=data['Sentiment_Score'],
                    crowded_long_positions=data['Crowded_Long_Positions'],
                    crowded_short_positions=data['Crowded_Short_Positions'],
                    speculative_positioning_index=data['Speculative_Positioning_Index'],
                    cot_ratio=data['COT_Ratio'],
                    net_speculative_position=data['Net_Speculative_Position'],
                    comm_noncomm_ratio=data['Comm_NonComm_Ratio'],
                    pct_oi_spec_positions=data['Pct_OI_Spec_Positions'],
                    overall_decision=data['Overall_Decision'],
                    overall_sentiment=data['Overall_Sentiment']
                )
                data.save()
                print("saved")
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
    analyzed_data = filter_and_analyze_tff_data(final_data[0])
    important_data = analyzed_data[[
        "date",
        "Symbol",
        "Decision",
        'Sentiment_Score',
        'Crowded_Long_Positions',
        'Crowded_Short_Positions',
        'Speculative_Positioning_Index',
        'COT_Ratio',
        'Net_Speculative_Position',
        'Comm_NonComm_Ratio',
        'Pct_OI_Spec_Positions',
        'Overall_Decision',
        'Overall_Sentiment'
    ]]
    symbol_dataframes = regroup_by_symbol(important_data)
    save_to_django_models(symbol_dataframes)
