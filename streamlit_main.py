import streamlit as st
import pyupbit
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from class_mrha import MRHATradingSystem
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv

# config 폴더의 .env 파일 로드
load_dotenv()

# API 키 가져오기 - Streamlit Cloud Secrets를 우선적으로 사용
UPBIT_ACCESS_KEY = st.secrets.get("UPBIT_ACCESS_KEY", os.getenv('UPBIT_ACCESS_KEY'))
UPBIT_SECRET_KEY = st.secrets.get("UPBIT_SECRET_KEY", os.getenv('UPBIT_SECRET_KEY'))

# API 키 디버깅 정보 표시 (개발용)
st.sidebar.write("API 키 상태:")
st.sidebar.write(f"Access Key 설정: {'있음' if UPBIT_ACCESS_KEY else '없음'}")
st.sidebar.write(f"Secret Key 설정: {'있음' if UPBIT_SECRET_KEY else '없음'}")

# API 키가 없으면 에러 메시지 표시
if not UPBIT_ACCESS_KEY or not UPBIT_SECRET_KEY:
    st.error("""
        API keys not found. Please check:
        1. Streamlit Cloud Secrets 설정
        2. .env 파일 설정
        
        Streamlit Cloud에서 Secrets를 설정하는 방법:
        1. 앱의 'Manage app' 클릭
        2. 'Settings' 탭으로 이동
        3. 'Secrets' 섹션에서 다음 형식으로 입력:
        ```
        [secrets]
        UPBIT_ACCESS_KEY = "your_access_key"
        UPBIT_SECRET_KEY = "your_secret_key"
        ```
    """)
    st.stop()

# 페이지 설정
st.set_page_config(page_title="MRHA Trading System", layout="wide")

# MRHA 봇 실행을 위한 함수 (캐시 비활성화)
def run_mrha_bot(ticker, interval):
    try:
        bot = MRHATradingSystem(ticker, interval, count=365)
        bot.run_analysis()
        return bot
    except Exception as e:
        st.error(f"Error in MRHA bot: {str(e)}")
        return None

# 모든 코인에 대한 시그널을 계산하는 함수
def calculate_all_coin_signals():
    try:
        # 모든 코인 티커 가져오기
        tickers = pyupbit.get_tickers(fiat="KRW")
        
        # 중단 버튼을 위한 컨테이너
        stop_container = st.empty()
        if stop_container.button("Stop Analysis", key="stop_button_initial"):
            st.warning("Analysis stopped by user")
            return None
        
        # 진행 상황을 표시할 컨테이너 생성
        progress_container = st.empty()
        progress_bar = st.progress(0)
        status_text = st.empty()
        result_container = st.empty()
        
        # 데이터프레임 초기화
        data = []
        
        # 오늘부터 과거 10일까지의 날짜 리스트 생성
        dates = []
        for i in range(10):
            date = datetime.now() - timedelta(days=i)
            dates.append(date.strftime("%Y-%m-%d"))
        
        # 각 코인에 대해 시그널 계산
        for idx, ticker in enumerate(tickers):
            try:
                # 중단 버튼 상태 확인
                if stop_container.button("Stop Analysis", key=f"stop_button_{idx}"):
                    st.warning("Analysis stopped by user")
                    return None
                
                # 진행 상황 업데이트
                progress = (idx + 1) / len(tickers)
                progress_bar.progress(progress)
                status_text.text(f"Processing {ticker}... ({idx+1}/{len(tickers)})")
                
                # 현재 처리 중인 코인 표시
                progress_container.markdown(f"""
                    ### Processing Status
                    - Current Coin: **{ticker}**
                    - Progress: **{progress*100:.1f}%**
                    - Completed: **{idx}/{len(tickers)}**
                """)
                
                # 백테스팅과 동일한 방식으로 시그널 계산
                bot = MRHATradingSystem(ticker, "day", count=365)
                bot.run_analysis()
                
                # 최근 10일의 시그널 확인
                row = {"Coin": ticker}
                for date in dates:
                    # 해당 날짜의 시그널 찾기
                    signal = "HOLD"
                    for _, trade in bot.trades.iterrows():
                        trade_date = trade['Date'].strftime("%Y-%m-%d")
                        if trade_date == date:
                            signal = "BUY" if trade['Type'] == 'Buy' else "SELL"
                            break
                    row[date] = signal
                
                data.append(row)
                
                # 중간 결과 표시
                if len(data) > 0:
                    df = pd.DataFrame(data)
                    result_container.dataframe(df, use_container_width=True)
                
                time.sleep(0.1)  # API 호출 제한을 위한 지연
                
            except Exception as e:
                st.warning(f"Error processing {ticker}: {str(e)}")
                continue
        
        # 최종 결과 표시
        status_text.text("✅ Analysis Complete!")
        progress_container.markdown("""
            ### Analysis Complete
            All coins have been processed successfully.
        """)
        
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"Error calculating signals: {str(e)}")
        return None

# Upbit API를 통한 계좌 정보 가져오기
def get_account_info():
    try:
        st.write("API 키 확인 중...")
        st.write(f"Access Key 길이: {len(UPBIT_ACCESS_KEY) if UPBIT_ACCESS_KEY else 0}")
        st.write(f"Secret Key 길이: {len(UPBIT_SECRET_KEY) if UPBIT_SECRET_KEY else 0}")
        
        # API 호출 전 딜레이 추가
        time.sleep(1)
        
        upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
        st.write("계좌 정보 요청 중...")
        
        # API 응답 시간 측정
        start_time = time.time()
        balances = upbit.get_balances()
        end_time = time.time()
        
        st.write(f"API 응답 시간: {end_time - start_time:.2f}초")
        
        # API 응답이 문자열인 경우 처리
        if isinstance(balances, str):
            st.error(f"API 응답 오류: {balances}")
            return []
            
        if balances is None:
            st.error("계좌 정보를 가져올 수 없습니다. API 키를 확인해주세요.")
            return []
            
        # balances가 리스트가 아닌 경우 처리
        if not isinstance(balances, list):
            st.error(f"예상치 못한 API 응답 형식: {type(balances)}")
            st.write(f"API 응답 내용: {balances}")  # API 응답 내용 표시
            return []
            
        st.write(f"계좌 정보 수신 완료: {len(balances)}개의 항목")
        return balances
    except Exception as e:
        st.error(f"계좌 정보 조회 중 오류 발생: {str(e)}")
        st.error(f"오류 상세: {type(e).__name__}")
        import traceback
        st.error(f"스택 트레이스: {traceback.format_exc()}")
        return []

# 사이드바 설정
st.sidebar.title("MRHA Trading System")

# 사용 가능한 티커 가져오기
try:
    tickers = pyupbit.get_tickers(fiat="KRW")
    default_ticker = "KRW-BTC" if "KRW-BTC" in tickers else tickers[0]
    selected_ticker = st.sidebar.selectbox("Select Cryptocurrency", tickers, index=tickers.index(default_ticker))
except Exception as e:
    st.sidebar.error(f"Error fetching tickers: {str(e)}")
    st.stop()

# 메뉴 버튼들
menu = st.sidebar.radio(
    "Select Menu",
    ["Backtesting", "Run Top 10 Coins", "All Coin Signals", "Execute ODA"]
)

# 메인 컨텐츠
st.title("MRHA Trading System")

# 선택된 메뉴에 따라 다른 컨텐츠 표시
if menu == "Backtesting":
    st.header("MRHA Fibonacci Trading System Results")
    
    # Run Backtesting 버튼
    if st.sidebar.button("Run Backtesting"):
        mrha_bot = run_mrha_bot(selected_ticker, "day")
        
        if mrha_bot:
            # 차트 표시
            st.subheader("MRHA Fibonacci Trading System Chart")
            fig_mrha = mrha_bot.plot_results()
            st.plotly_chart(fig_mrha, use_container_width=True)
            
            # 백테스트 결과 표시
            st.subheader("MRHA Fibonacci Trading System Backtest Results")
            mrha_results = mrha_bot.get_results()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Final Portfolio Value", f"{mrha_results['Final Portfolio Value']:,.0f} KRW")
            col2.metric("Total Return", f"{mrha_results['Total Return']:.2f}%")
            col3.metric("Sharpe Ratio", f"{mrha_results['Sharpe Ratio']:.2f}")
            
            col4, col5, col6 = st.columns(3)
            col4.metric("Annualized Return", f"{mrha_results['Annualized Return']:.2f}%")
            col5.metric("Max Drawdown", f"{mrha_results['Max Drawdown']:.2f}%")
            col6.metric("Total Trades", mrha_results['Total Trades'])
            
            # 트레이드 히스토리 표시
            st.subheader("MRHA Fibonacci Trading System Trade History")
            st.dataframe(mrha_bot.trades, use_container_width=True)

elif menu == "Run Top 10 Coins":
    st.header("Top 10 Coins Analysis")
    
    if st.sidebar.button("Run Top 10 Coins"):
        # 상위 10개 코인 가져오기
        top_10_tickers = tickers[:10]
        
        # 중단 버튼을 위한 컨테이너
        stop_container = st.empty()
        if stop_container.button("Stop Analysis", key="stop_button_initial_top10"):
            st.warning("Analysis stopped by user")
            st.stop()
        
        # 진행 상황을 표시할 컨테이너 생성
        progress_container = st.empty()
        progress_bar = st.progress(0)
        status_text = st.empty()
        result_container = st.empty()
        
        # 데이터프레임 초기화
        data = []
        
        # 오늘부터 과거 10일까지의 날짜 리스트 생성
        dates = []
        for i in range(10):
            date = datetime.now() - timedelta(days=i)
            dates.append(date.strftime("%Y-%m-%d"))
        
        # 각 코인에 대해 시그널 계산
        for idx, ticker in enumerate(top_10_tickers):
            try:
                # 중단 버튼 상태 확인
                if stop_container.button("Stop Analysis", key=f"stop_button_{idx}_top10"):
                    st.warning("Analysis stopped by user")
                    st.stop()
                
                # 진행 상황 업데이트
                progress = (idx + 1) / len(top_10_tickers)
                progress_bar.progress(progress)
                status_text.text(f"Processing {ticker}... ({idx+1}/{len(top_10_tickers)})")
                
                # 현재 처리 중인 코인 표시
                progress_container.markdown(f"""
                    ### Processing Status
                    - Current Coin: **{ticker}**
                    - Progress: **{progress*100:.1f}%**
                    - Completed: **{idx}/{len(top_10_tickers)}**
                """)
                
                # 백테스팅과 동일한 방식으로 시그널 계산
                bot = MRHATradingSystem(ticker, "day", count=365)
                bot.run_analysis()
                
                # 최근 10일의 시그널 확인
                row = {"Coin": ticker}
                for date in dates:
                    # 해당 날짜의 시그널 찾기
                    signal = "HOLD"
                    for _, trade in bot.trades.iterrows():
                        trade_date = trade['Date'].strftime("%Y-%m-%d")
                        if trade_date == date:
                            signal = "BUY" if trade['Type'] == 'Buy' else "SELL"
                            break
                    row[date] = signal
                
                data.append(row)
                
                # 중간 결과 표시
                if len(data) > 0:
                    df = pd.DataFrame(data)
                    result_container.dataframe(df, use_container_width=True)
                
                time.sleep(0.1)  # API 호출 제한을 위한 지연
                
            except Exception as e:
                st.warning(f"Error processing {ticker}: {str(e)}")
                continue
        
        # 최종 결과 표시
        status_text.text("✅ Analysis Complete!")
        progress_container.markdown("""
            ### Analysis Complete
            Top 10 coins have been processed successfully.
        """)

elif menu == "All Coin Signals":
    st.header("All Coin Signals")
    
    if st.sidebar.button("Run All Coin"):
        df = calculate_all_coin_signals()
        if df is not None:
            st.dataframe(df, use_container_width=True)

elif menu == "Execute ODA":
    st.header("Order Execution")
    
    # 계좌 정보 표시
    balances = get_account_info()
    krw_balance = None  # krw_balance 변수 초기화
    
    if balances:
        st.subheader("Account Information")
        
        # KRW 잔고
        try:
            krw_balance = next((item for item in balances if isinstance(item, dict) and item.get('currency') == 'KRW'), None)
            if krw_balance:
                st.write(f"KRW Balance: {float(krw_balance.get('balance', 0)):,.0f} KRW")
        except Exception as e:
            st.error(f"KRW 잔고 조회 중 오류: {str(e)}")
        
        # 코인 잔고
        st.subheader("Coin Positions")
        for balance in balances:
            if isinstance(balance, dict) and balance.get('currency') != 'KRW':
                try:
                    ticker = f"KRW-{balance.get('currency')}"
                    current_price = pyupbit.get_current_price(ticker)
                    if current_price is not None:
                        total_value = float(balance.get('balance', 0)) * current_price
                        st.write(f"{ticker}: {float(balance.get('balance', 0)):,.8f} ({total_value:,.0f} KRW)")
                except Exception as e:
                    st.warning(f"{ticker} 가격 조회 중 오류 발생: {str(e)}")
    
    # 주문 실행
    st.subheader("Place Order")
    
    # 주문 유형 선택
    order_type = st.selectbox("Order Type", ["Buy", "Sell"])
    
    # 코인 선택
    selected_coin = st.selectbox("Select Coin", tickers)
    
    if order_type == "Buy":
        # 매수 주문
        if krw_balance:  # 이제 krw_balance가 정의되어 있음
            try:
                max_buy_amount = float(krw_balance.get('balance', 0))
                st.write(f"Maximum Buy Amount: {max_buy_amount:,.0f} KRW")
                
                buy_amount = st.number_input("Buy Amount (KRW)", min_value=0.0, max_value=max_buy_amount)
                if st.button("Execute Buy Order"):
                    try:
                        upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
                        result = upbit.buy_market_order(selected_coin, buy_amount)
                        st.success(f"Buy order executed: {result}")
                    except Exception as e:
                        st.error(f"매수 주문 실행 중 오류 발생: {str(e)}")
            except Exception as e:
                st.error(f"매수 금액 계산 중 오류: {str(e)}")
        else:
            st.warning("KRW 잔고 정보를 불러올 수 없습니다. 계좌 정보를 확인해주세요.")
    
    else:
        # 매도 주문
        try:
            coin_balance = next((item for item in balances if isinstance(item, dict) and item.get('currency') == selected_coin.replace("KRW-", "")), None)
            if coin_balance:
                sell_amount = st.number_input("Sell Amount", min_value=0.0, max_value=float(coin_balance.get('balance', 0)))
                if st.button("Execute Sell Order"):
                    try:
                        upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
                        result = upbit.sell_market_order(selected_coin, sell_amount)
                        st.success(f"Sell order executed: {result}")
                    except Exception as e:
                        st.error(f"매도 주문 실행 중 오류 발생: {str(e)}")
            else:
                st.warning(f"{selected_coin} 잔고 정보를 불러올 수 없습니다.")
        except Exception as e:
            st.error(f"매도 금액 계산 중 오류: {str(e)}")

# 정보 메시지 표시
st.sidebar.info("Select a menu option to proceed.") 
