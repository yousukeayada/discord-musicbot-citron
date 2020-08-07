from __future__ import print_function
import os
import os.path
import io
import queue
import asyncio

import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import discord
import youtube_dl
import MySQLdb
import requests
from bs4 import BeautifulSoup

import commands
import settings



# -------------google drive 認証-------------------------------------------------
# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

"""Shows basic usage of the Drive v3 API.
Prints the names and ids of the first 10 files the user has access to.
"""
creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_secrets.json', SCOPES)
        creds = flow.run_console()
    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('drive', 'v3', credentials=creds)
# --------------------------------------------------------------------------------


# 自分のBotのアクセストークンに置き換えてください
TOKEN = settings.TOKEN

# 接続に必要なオブジェクトを生成
client = discord.Client()

voice = None
audio_queue = queue.Queue()
audiofile_list = []
# 再生キューに曲があるか確認
def check_queue(e):
    os.remove(audiofile_list.pop(0))
    try:
        if not audio_queue.empty():
            audio_source = audio_queue.get()
            voice.play(audio_source,after=check_queue)
    except:
        print(e)

# 起動時に動作する処理
@client.event
async def on_ready():
    # 起動したらターミナルにログイン通知が表示される
    print('ログインしました')

# メッセージ受信時に動作する処理
@client.event
async def on_message(message):
    global voice
    # メッセージ送信者がBotだった場合は無視する
    if message.author.bot:
        return


    if message.content.startswith('/play'):
        voice_channel = client.get_channel(message.guild.voice_channels[0].id)
        voice_client = message.guild.voice_client

        search_word=message.content.split(" ",1)
        # print(search_word[0])
        if search_word[1].startswith('https://www.youtube.com'): #youtubeの場合
            url = search_word[1]
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl':  '%(title)s.%(ext)s' ,
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'},
                    {'key': 'FFmpegMetadata'},
                ],
            }
            ydl = youtube_dl.YoutubeDL(ydl_opts)
            data = ydl.extract_info(url, download=False)
            filename = data['title'] + ".mp3"

            if not os.path.exists(filename):
                await message.channel.send("ダウンロードしてくるからちょっと待ってて！")
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            
            audio_source = discord.FFmpegPCMAudio(filename)
            audiofile_list.append(filename)
            if not voice: #ボイチャ接続
                voice = await voice_channel.connect()
            # 再生中、一時停止中はキューに入れる
            if audio_queue.empty() and not voice.is_playing() and not voice.is_paused():
                await message.channel.send("**"+data['title']+"**を再生するよー♪")
                voice.play(audio_source,after=check_queue)
            else:
                await message.channel.send("**"+filename+"**を再生リストに入れておくね！")
                audio_queue.put(audio_source)
        else: #youtube以外の場合
            results = service.files().list(q="mimeType != 'application/vnd.google-apps.folder' and name contains '"+search_word[1]+"'",
                pageSize=10, fields="nextPageToken, files(id, name)").execute()
            items = results.get('files', [])

            if len(items) == 0:
                await message.channel.send("その曲はないみたい")
            elif len(items) == 1: #1曲のときのみ再生する
                filename = items[0]['name']
                if not os.path.exists(filename):
                    request = service.files().get_media(fileId=items[0]['id']) #httpリクエストを返す
                    fh = io.FileIO(filename, "wb")
                    downloader = MediaIoBaseDownload(fh, request)
                    await message.channel.send("ダウンロードしてくるからちょっと待ってて！")
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                        print ("Download %d%%." % int(status.progress() * 100))

                audio_source = discord.FFmpegPCMAudio(filename)
                audiofile_list.append(filename)
                if not voice: #ボイチャ接続
                    voice = await voice_channel.connect()
                # 再生中、一時停止中はキューに入れる
                if audio_queue.empty() and not voice.is_playing() and not voice.is_paused():
                    await message.channel.send("**"+filename+"**を再生するよー♪")
                    voice.play(audio_source,after=check_queue)
                else:
                    await message.channel.send("**"+filename+"**を再生リストに入れておくね！")
                    audio_queue.put(audio_source)
            elif len(items) >= 2: #10曲まで表示する
                msg = "**どれにするー？**\n----------------------------\n"
                for item in items:
                    msg += item['name'] + "\n"
                msg += "----------------------------"
                await message.channel.send(msg)
    

    if message.content.startswith('/stop'):
        # voice_client = message.guild.voice_client
        if voice.is_playing():
            await message.channel.send("曲、止めちゃうの？")
            voice.stop()
        else:
            await message.channel.send("もう止まってるよ？")


    if message.content.startswith('/pause'):
        # voice_client = message.guild.voice_client
        if voice.is_paused():
            await message.channel.send("再開は/resumeだよー")
        else:
            await message.channel.send("一時停止ｸﾞｻｧｰｯ!")
            voice.pause()


    if message.content.startswith('/resume'):
        # voice_client = message.guild.voice_client
        if voice.is_paused():
            await message.channel.send("再開するよ！")
            voice.resume()
        else:
            await message.channel.send("再生中だよー")


    if message.content.startswith('/list'):
        if audiofile_list != []:
            msg = "今の再生リストはこんな感じだよー\n----------------------------\n"
            for i in range(0,len(audiofile_list)):
                msg += "**"+str(i+1)+".** "+audiofile_list[i] + "\n"
            msg += "----------------------------"
            await message.channel.send(msg)
        else:
            await message.channel.send("静かだねぇ〜")


    if message.content.startswith('/profile'):
        key = message.content.split(" ",1)
        data = ('%'+key[1]+'%', '%'+key[1]+'%')
        sql = "SELECT * FROM idol where name like %s or kana like %s"
        # データベースへの接続とカーソルの生成
        DB = settings.DB
        connection = MySQLdb.connect(
            host=DB["host"],
            user=DB["user"],
            passwd=DB["pass"],
            db=DB["db"],
        # テーブル内部で日本語を扱うために追加
            charset='utf8'
        )
        cursor = connection.cursor(MySQLdb.cursors.DictCursor)
        # 一覧の表示
        cursor.execute(sql,data)
        rows = cursor.fetchall()
        if len(rows) == 0:
            await message.channel.send("その名前の子はいないよ〜")
        for row in rows:
            await message.channel.send(row['name']+"さんのプロフィールはこちら！")
            await message.channel.send(
                "名前："+row['name']+"（"+row['kana']+"）\n"+
                "年齢："+str(row['age'])+"\t誕生日："+row['birthday']+"\t星座："+row['constellation']+"\n"+
                "身長："+str(row['height'])+"cm\t体重："+str(row['weight'])+"kg\n"+
                "スリーサイズ："+str(row['B'])+"/"+str(row['W'])+"/"+str(row['H'])+"\n"+
                "血液型："+row['blood']+"\t利き手："+row['handed']+"\n"+
                "出身："+row['hometown']+"\n"+
                "趣味："+row['hobby']+"\n"+
                "特技："+row['talent']+"\n"+
                "CV："+row['cv'])
            # print(row)


    # ex) /search 3 <keyword>、/search <keyword>
    if message.content.startswith('/search'):
        msg = message.content.split(" ")
        if msg[1].isnumeric():
            search_word = message.content.split(" ",2)[2]
            num_img = int(msg[1])
            if num_img > 5:
                num_img = 5
            elif num_img < 1:
                num_img = 1
        else:
            search_word = message.content.split(" ",1)[1]
            num_img = 1
        
        print("search word : "+search_word)
        param = {'q': search_word}
        response = requests.get("http://images.google.com/images",params=param)
        print(str(response.status_code)+response.reason)
        response.raise_for_status() #ステータスコードが200番台以外なら例外起こす．
        soup = BeautifulSoup(response.text, 'html.parser')
        elements = soup.select("img[src*='http']")
        # print(elements)
        await message.channel.send(num_img + "件探してくるね！")
        for i in range(num_img):
            img = elements[i]
            await message.channel.send(img.attrs['src'])



    if message.content.startswith('/yuzu'):
        await message.channel.send("なになに？柚とお話したいの？")


    if message.content.startswith('/name'):
        await message.channel.send(client.user.display_name)
        await client.user.edit(username="DJ_Citron")
        await message.channel.send(client.user.display_name)


    if message.content == '/bye':
        await message.channel.send("じゃあねー♪")
        voice_client = message.guild.voice_client
        if voice_client:
            await voice_client.disconnect()
            print("ボイスチャンネルから切断しました")
        print("ログアウトします")
        await client.logout()


    if message.content == '/help':
        msg = "柚の使い方はこちら♪\n"
        for i in commands.commands.items():
            msg += "`"+i[0]+"` : "+i[1]+"\n"
        await message.channel.send(msg)



# Botの起動とDiscordサーバーへの接続
client.run(TOKEN)