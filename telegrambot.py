from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
import requests
from bs4 import BeautifulSoup
import re
from time import sleep
from collections import OrderedDict
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime,timedelta
from time import sleep
from random import random
from dateutil.relativedelta import relativedelta
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import fontManager
import io
import jieba #切詞工具
import numpy as np #如果要毒入自己的圖繪需要
import matplotlib.pyplot as plt #畫圖工具
from wordcloud import WordCloud #詞雲圖產生器
import os #確認電腦內有沒有安裝繁中詞庫
import matplotlib.dates as mdates
from collections import Counter


#函式：判斷使用者輸入是否為中文
def is_chinese_or_digit(char, dict_stock_list):
    #如果是名稱，return字典value
    if '\u4e00' <= char <= '\u9fff':
        return dict_stock_list[char]

    #如果是代號，return代號
    if '0' <= char <= '9':
        return char

#設定多重子圖規格
def k_bar_photo(financial_dict):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    vertical_spacing=0.1, subplot_titles=('走勢圖', 'Volume'),
                    row_width=[0.2, 0.7], specs=[[{"secondary_y": False}], [{"secondary_y": False}]])

    #給定繪製k線圖所需資訊，繪製k線並將上漲、下跌顏色設定成符合國內常用的漲紅跌綠
    candlesticks = go.Candlestick(
        x=[key for key in reversed(financial_dict['sixmonth_kbar'])],
        open=[financial_dict['sixmonth_kbar'][key][0] for key in reversed(financial_dict['sixmonth_kbar'])],
        high=[financial_dict['sixmonth_kbar'][key][1] for key in reversed(financial_dict['sixmonth_kbar'])],
        low=[financial_dict['sixmonth_kbar'][key][2] for key in reversed(financial_dict['sixmonth_kbar'])],
        close=[financial_dict['sixmonth_kbar'][key][3] for key in reversed(financial_dict['sixmonth_kbar'])],
        increasing=dict(line=dict(color='red'), fillcolor='red'),
        decreasing=dict(line=dict(color='green'), fillcolor='green'))

    #給定繪製成交量圖所需資訊，繪製成交量長條圖
    volume_bars = go.Bar(
        x=[key for key in reversed(financial_dict['sixmonth_kbar'])],
        y=[financial_dict['sixmonth_kbar'][key][4] for key in reversed(financial_dict['sixmonth_kbar'])],
        showlegend=False,
        marker={
            "color": "rgba(128,128,128,0.5)",
        }
        )

    # 將走勢圖添加到第一行
    fig.add_trace(candlesticks, row=1, col=1)
    fig.update_yaxes(title_text="Price $", secondary_y=False, showgrid=True, row=1, col=1)

    # 將Volume圖添加到第二行
    fig.add_trace(volume_bars, row=2, col=1)
    fig.update_yaxes(title_text="Volume $", secondary_y=False, showgrid=False, row=2, col=1)

    # 添加均線
    for period in [5, 10, 20]:
        ma_values = [financial_dict['sixmonth_kbar'][key][3] for key in reversed(financial_dict['sixmonth_kbar'])]
        ma_trace = go.Scatter(x=list(reversed(financial_dict['sixmonth_kbar'].keys())),
                                y=pd.Series(ma_values).rolling(window=period).mean(),
                                mode='lines',
                                name=f'{period}-day MA',
                                line=dict(width=1),
                                connectgaps=True)
        fig.add_trace(ma_trace, row=1, col=1)

    fig.update_layout(
        title=f'{financial_dict["stock_id"]} {financial_dict["stock_name"]} 近六個月股價日K線圖',
        height=800,
        width=1600,
        xaxis={"rangeslider": {"visible": False}},
        )

    fig.write_image("./fig1.png")
    return "./fig1.png"

#爬取PTT討論版
def crawl_page_detail(detail_url, session):
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        re = session.get(detail_url, headers=header)
        soup = BeautifulSoup(re.text, 'lxml')

        # 處理詳細頁面的爬取邏輯
        return soup

# PTT爬蟲並儲存資料
def ptt_title(financial_dict):
    # 設定爬取的起始日期（半年前的日期）
    start_date = (datetime.now() - relativedelta(months=6)) # 自動計算半年前的日期(from dateutil.relativedelta import relativedelta)

    # 根據字典裡的股票代號或股票名稱爬取相對應的討論版標題
    id = financial_dict['stock_id']
    name = financial_dict['stock_name']
    date_lst = [] # 爬取完的日期
    title_lst = [] # 爬取完的標題

    # 使用 Session 保持相同的 cookies
    session = requests.Session()

    # 設定起始頁面數字
    page_number = 1
    stock = quote(name, safe='') # 將中文轉換為 URL 可接受的格式(from urllib.parse import quote)
    check = True
    while True:
        first_page_url = f"https://www.ptt.cc/bbs/Stock/search?page={page_number}&q={name}"
        soup = crawl_page_detail(first_page_url, session)

        # 處理每一頁的內容，提取需要的資訊
        for i in soup.find_all('div', {'class': 'r-ent'}):
            date = i.find('div', {'class': 'meta'}).find('div', {'class': 'date'}).text
            title = i.find('div', {'class': 'title'})

            # 提取標題的超連結
            link = title.find('a')
            detail_url = f"https://www.ptt.cc{link['href']}"

            # 進入詳細頁面爬取更多資訊
            detail_soup = crawl_page_detail(detail_url, session)

            for meta_line in detail_soup.find_all('div', {'class': 'article-metaline'}):
                if '時間' in meta_line.find('span', {'class': 'article-meta-tag'}).text:
                    # 獲取發文的年份
                    post_year = meta_line.find('span', {'class': 'article-meta-value'}).text.split()[-1]
            end = date.split('/')

            # 判斷是否符合條件
            if int(post_year) == start_date.year:
                if int(end[0]) >= start_date.month:
                    date_lst.append(date)
                    title_lst.append(title.text.strip())  # 符合條件的標題存進list裡
            elif int(post_year) == start_date.year+1:
                date_lst.append(date)
                title_lst.append(title.text.strip())
            else:
                check = False
            break
        if check == False:
            break
        # 更新頁面數字，以繼續爬取下一頁
        page_number += 1

        # 避免爬取速度過快
        sleep(random())

    if not date_lst or not title_lst:
        print('此股票半年內無人討論')

    #把DCARD爬文的參數放在這就算不跑DCARD爬文之後還是能順利執行
    captured_titles = []
    captured_times = []
    return title_lst, date_lst


# DCARD爬蟲並儲存資料
def dcard_title(financial_dict):
    #設定遊覽器
    option = webdriver.ChromeOptions() # 設定 chromedriver
    #option.add_argument('--headless') # 無頭模式，開發完成之後再使用，可以完全背景執行，有機會變快。但無頭模式在某些網站會不能爬。
    option.add_experimental_option('excludeSwitches', ['enable-automation']) # 開發者模式。可以避開某些防爬機制，有開有保佑
    driver = webdriver.Chrome(options=option) # 啟動 chromedriver

    #爬蟲網址設定
    name = financial_dict['stock_name']
    url = "https://www.dcard.tw/search/posts?query="+name+"&forum=stock&sort=created&since=180&field=title"
    driver.get(url)
    #建立儲存文章標題與時間的資料
    captured_titles = []
    captured_times = []
    last_articles = ""
    # 等待頁面載入
    sleep(3)

    try:
        for i in range(10):
            # 等待文章元素出現
            wait = WebDriverWait(driver, 10)
            #抓取article這個tag
            articles = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "article")))

            #如果新抓取到的資料跟剛剛抓取到的一模一樣就請跳出
            if last_articles == articles:
                break

            #在article後往下抓a(文章標題在這)
            for article in articles:
                title = article.find_element(By.TAG_NAME, "a").text
                # 如果標題還沒有被抓取過，則儲存該文章
                if title not in captured_titles:
                    captured_titles.append(title)

            #article後往下抓time這個tag
            for article in articles:
                time = article.find_element(By.TAG_NAME, "time").get_attribute("datetime")
                if time not in captured_times:
                    captured_times.append(time)

            #將剛剛爬到的資料先存下來待會去跟新爬的資料作比對
            last_articles = articles

            #抓完後按下page_down按鈕並且等待3秒
            driver.find_element(By.CSS_SELECTOR, 'html').send_keys(Keys.PAGE_DOWN)
            sleep(2+random()*2)

    except Exception as e:
        print("Dcard股版無該股票相關討論")

    # 關閉瀏覽器
    driver.quit()
    return captured_titles, captured_times


#繪製EPS長條圖
def eps_bar_photo(financial_dict):
    matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei']
    matplotlib.rcParams['axes.unicode_minus'] = False
    ifont = "msjh.ttc"    
    
    eps = financial_dict['10season_eps']
    if eps!={}:
        eps_Q=[]
        eps_v=[]
        for item in eps:
            eps_Q.append(item)
            eps_v.append(eps[item])

        name = financial_dict['stock_name']
        plt.bar(eps_Q[::-1], eps_v[::-1])
        plt.title(f'{name}每季EPS')
        plt.xticks(rotation=45)
        # plt.xlabel('')
        plt.ylabel('EPS')
        for i in reversed(range(len(eps_Q))):
            plt.text(eps_Q[i],eps_v[i],str(eps_v[i]),fontsize=10, verticalalignment='center',horizontalalignment='center')
        
        img_eps = io.BytesIO()
        plt.savefig(img_eps, format='png')
        plt.close()
        img_eps.seek(0)
        return img_eps
    
#切割文章標題及匯出詞雲圖
def stock_wordcloud_photo(financial_dict):
    # 指定要檢查的檔案名稱
    target_file_name = 'dict.txt.big'
    # 獲取當前工作目錄中的檔案列表
    files_in_directory = os.listdir()
    # 檢查是否存在目標檔案
    if target_file_name not in files_in_directory:
        #繁中詞庫請去 https://github.com/fxsjy/jieba 找到 https://github.com/fxsjy/jieba/raw/master/extra_dict/dict.txt.big 下載存到工作目錄中
        url = 'https://github.com/fxsjy/jieba/raw/master/extra_dict/dict.txt.big'
        r = requests.get(url)
        with open('dict.txt.big', 'wb') as f:
            f.write(r.content)


    #設定繁體中文詞庫及把股票名加入建議詞庫
    jieba.set_dictionary("dict.txt.big") #將詞庫替換為繁中字庫
    jieba.suggest_freq(financial_dict['stock_name'], True) #把股票名加入建議詞庫

    #將之前抓到的captured_titles導入jieba切詞
    title = dcard_title(financial_dict)[0] + ptt_title(financial_dict)[0]
    ifont = "msjh.ttc"
    if title == []:
        print("PTT與DCARD近半年無相關討論")
    else:
        cut = jieba.cut("".join(title), cut_all=False)
        cut = " ".join(cut)

        print("共有",len(title),"則討論",sep="") #顯示總討論的文章數

        s = ["的","是","了","個","Re","嗎","分享","你","會","啦","很"]
        #生產詞雲圖，字體設定為標楷體正常
        #stopwords：可以把要去掉不要顯示的字存入一個list然後再指定給stopwords這個參數
        #font_path是顯示的字體，儲存字體路徑請見 C:\Windows\Fonts，請去該資料夾中找到想要的字體把名稱跟副檔名指定過來
        wordcloud = WordCloud(font_path = ifont ,stopwords=s,collocations=False,background_color='white',width = 800,height = 400).generate(cut)

        # 顯示詞雲圖:
        # the matplotlib way:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
        #wordcloud.to_file("詞雲圖.png")

        img_wordcloud = io.BytesIO()
        plt.savefig(img_wordcloud, format='png')
        plt.close()
        img_wordcloud.seek(0)
        return img_wordcloud

#討論趨勢圖
def discuss(financial_dict,date_lst, captured_times):
    #整理ptt時間資料
    current_date = datetime.now()
    dates = []
    for x in date_lst:
        x = x.strip().zfill(5)
        #先把年份帶今年轉成日期資料
        date_obj = datetime.strptime(f'{current_date.year}/{x}', '%Y/%m/%d')
        if date_obj > current_date:
                date_obj = date_obj.replace(year=current_date.year - 1)
        dates.append(date_obj)


    # 將時間字符串轉換為 datetime 對象，忽略時間戳部分
    dates = dates + [datetime.strptime(time.split('T')[0], '%Y-%m-%d') for time in captured_times]


    # 計算日期範圍
    start_date = datetime.now() - timedelta(days=180)
    end_date = datetime.now()

    # 將日期資料轉換成按週跟月，並且計數
    month_numbers = [(date.isocalendar()[0], date.month) for date in dates]
    months = Counter(month_numbers)

    # 創建一個空串列來儲存年份和週數組合
    all_months = []
    # 從今天往前遍歷到180天前的每一天
    current_date = end_date
    while current_date >= start_date:
        # 使用 isocalendar 獲取年份和週數和取得月份
        year, week, _ = current_date.isocalendar()
        m = current_date.month
        # 將組合添加到串列中，檢查重複

        if (year, m) not in all_months:
            all_months.append((year, m))

        # 向前遍歷一天
        current_date -= timedelta(days=1)

    #把每月計數依照時間週期組合填入串列
    month_counts = [months[month] for month in all_months]
    month_counts = month_counts[::-1]
    all_months = all_months[::-1]
    name = financial_dict['stock_name']

    # 直方圖 - 月
    # plt.figure(figsize=(10, 6))
    plt.bar(range(len(all_months)), month_counts, color='blue', tick_label=[f'{m[0]}-{m[1]}' for m in all_months])
    for i in range(len(all_months)):
        plt.text(i,month_counts[i],str(month_counts[i]),fontsize=10, verticalalignment='bottom',horizontalalignment='center')
    plt.xlabel('年-月')
    plt.xticks(rotation=45)
    plt.ylabel('幾篇')
    plt.title(f'每月有幾篇討論{name}的文章')
    img_discuss = io.BytesIO()
    plt.savefig(img_discuss, format='png')
    plt.close()
    img_discuss.seek(0)
    return img_discuss


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = '''
        歡迎來到投資小助手, 我會公佈你想要的股票資訊, 所以請耐心等待1~3分鐘

    指令說明：
    /chat_id (輸入股票代號或名稱)- 投資小助手會幫你整理這支股票的相關資訊，共會有9則資訊
    '''
    await update.message.reply_text(message)

async def chatID(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # try:
    input_mex = update.message.text.split()
    # print(input_mex)
    #爬goodinfo，找出股票代號、名稱、資本額(股本)、股價(k線圖)(6個月)、EPS(兩季)
    ##處理股票清單，若使用者輸入股票名稱，先轉成股票代碼餵給程式
    #解析網站
    url_stock_list = 'https://goodinfo.tw/tw/Lib.js/TW_STOCK_ID_NM_LIST.js'
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
    r_list = requests.get(url_stock_list, headers=header)
    r_list.encoding = 'UTF-8'
    soup_list = BeautifulSoup(r_list.text , 'html.parser')

    #提取JavaScript中的garrTW_LIST_STOCK_ID_NM内容，並將所有股票清單列入字典，以股票名稱為key、代號為value(爬取javascript規格，要用正規表達式)
    javascript_content = str(soup_list)
    matches = re.findall(r"var garrTW_LIST_STOCK_ID_NM = \['(.*?)'\];", javascript_content, re.DOTALL)

    #如果有匹配到結果，進行後續處理
    if matches:
        # 將garrTW_LIST_STOCK_ID_NM内容納入字典
        dict_stock_list = {item.split(' ', 1)[1]: item.split(' ', 1)[0] for item in matches[0].split("','")}


    # 判斷使用者輸入為何
    stock = is_chinese_or_digit(input_mex[1], dict_stock_list)
    # print(stock)
    url_stock = 'https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID=' + stock #股票代號、名稱、資本額(股本)網址
    url_kbar = 'https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID='+ stock + '&PERIOD=180' #六個月K線網址
    url_eps = 'https://goodinfo.tw/tw/StockFinDetail.asp?RPT_CAT=XX_M_QUAR&LAST_RPT_CAT=XX_M_QUAR&STOCK_ID='+ stock + '&QRY_TIME=' #EPS網址(單季)

    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}

    r_stock = requests.get(url_stock,headers= header)
    sleep(2)
    r_kbar = requests.get(url_kbar, headers=header)
    sleep(2)
    r_eps = requests.get(url_eps, headers=header)

    #解析以上三個網站
    r_stock.encoding = 'UTF-8'
    r_kbar.encoding = 'UTF-8'
    r_eps.encoding = 'UTF-8'

    soup_stock = BeautifulSoup(r_stock.text , 'html.parser')
    sleep(2)
    soup_kbar = BeautifulSoup(r_kbar.text , 'html.parser')
    sleep(2)
    soup_eps = BeautifulSoup(r_eps.text , 'html.parser')

    #找標頭:股票代號、名稱
    financial_dict = {}

    link = f'StockDetail.asp?STOCK_ID={stock}'
    all_head_stock = soup_stock.select(f'a[href="{link}"]')

    for element in all_head_stock:
        if element.text[0].isdigit():
            stock_id_name = element.text.split()
    financial_dict['stock_id'] = stock_id_name[0]
    financial_dict['stock_name'] = stock_id_name[1]


    #找產業類別、股本
    all_country_info_content = soup_stock.select('td[bgcolor="white"]')
    country_industry = all_country_info_content[1].text
    country_capital = all_country_info_content[4].text
    country_business = soup_stock.select('td[bgcolor="white"] p')[-1].text

    financial_dict['industry'] = country_industry
    financial_dict['capital'] = country_capital
    financial_dict['major business'] = country_business


    #找到10季eps
    all_season = soup_eps.select('table[id="tblFinDetail"] th nobr')
    all_season_text = [nobr.text for nobr in all_season[1:]] #將all_season轉換成文字
    # all_season_text[1:] #分別為哪10季eps
    all_season_title = soup_eps.select('td[title="滑鼠在此點一下, 可顯示公式說明"] nobr')
    # all_season_eps[6] #eps_title:每股稅後盈餘
    all_season_eps = soup_eps.select('table[id="tblFinDetail"] td nobr')[67:77]
    # all_season_float = [float(nobr.text) for nobr in all_season_eps]  #將all_season_eps轉換成浮點數
    all_season_float =[float(nobr.text) if nobr.text != '-' else 0 for nobr in all_season_eps]
    after_tax_eps = [{i:j} for i,j in zip(all_season_text, all_season_float)] #將這10季的每一季EPS資料轉成字典儲存
    financial_dict['10season_eps'] ={key:value for item in after_tax_eps for key, value in item.items()}

    #找到6個月內，每日的開高低收價格，以利製作K線
    date_sixmonth = soup_kbar.find('table', {'id' : "tblPriceDetail"})
    #將K線資料加入一個有序的字典
    financial_dict['sixmonth_kbar'] = OrderedDict()

    for row in date_sixmonth.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 5:
            if '/' in cells[0].text.strip():
                row_data = [cell.text.strip() for cell in cells[:5]]
                financial_dict['sixmonth_kbar'][row_data[0]] = row_data[1:]
                financial_dict['sixmonth_kbar'][row_data[0]].append(float(cells[8].text.strip().replace(',', '')) if cells[8].text.strip().replace(',', '') else 0)
    # print(financial_dict)
    
    
    await update.message.reply_text(f"股票代號：{financial_dict['stock_id']}")
    await update.message.reply_text(f"股票名稱：{financial_dict['stock_name']}")
    await update.message.reply_text(f"資本額：{financial_dict['capital']}")
    await update.message.reply_text(f"產業：{financial_dict['industry']}")
    await update.message.reply_text(f"公司業務：{financial_dict['major business']}")
    await update.message.reply_photo(k_bar_photo(financial_dict))
    await update.message.reply_photo(eps_bar_photo(financial_dict))
    await update.message.reply_photo(stock_wordcloud_photo(financial_dict))
    await update.message.reply_photo(discuss(financial_dict,ptt_title(financial_dict)[1], dcard_title(financial_dict)[1]))


token = '請去找botfather要'
app = ApplicationBuilder().token(token).read_timeout(30).write_timeout(30).build()
app.add_handler(CommandHandler("start", help))
app.add_handler(CommandHandler("chat_id", chatID))

app.run_polling()
