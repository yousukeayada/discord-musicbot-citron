## 概要
- Discord で動作する音楽 Bot （+α）です。
- ローカルファイルではなく、Google Drive 上のファイルを検索します。
- Heroku へのデプロイを想定しています。
- [Qiita](https://qiita.com/ysk0832/items/372e5beb80df7f752bb5)

## コマンド一覧
|コマンド|説明|
|-|-|
|/play <曲名の一部> or \<URL>|再生キューに入れる．２曲以上見つかればその候補を表示|
|/stop|曲を終了する|
|/pause|一時停止する|
|/resume|再開する|
|/list|再生キューを表示する|

## 使い方
最終的なディレクトリ構成
```bash
discord-musicbot-citron
├── Procfile
├── citron.py
├── client_secrets.json #ダウンロードしてくる
├── commands.py
├── requirements.txt
├── runtime.txt
├── settings.py #自分で作る
└── token.pickle #実行時に作られる
```
```bash
# クローン
git clone https://github.com/yousukeayada/discord-musicbot-citron.git
cd discord-musicbot-citron

# パッケージインストール
pip install -r requirements.txt

# 設定ファイル作成
touch settings.py
```

設定ファイルの中身は以下のようにする。（適宜自分のものと置き換える）
```python
TOKEN = "XXXXXXXXXXXXXX"

DB = {
    "host": "XXXX",
    "user": "XXXX",
    "pass": "XXXX",
    "db": "XXXX"
}
```

次に、[Drive API のクイックスタート](https://developers.google.com/drive/api/v3/quickstart/python)を参考に`credentials.json`をダウンロードし、`client_secrets.json`に名前を変更する。

これで実行すると自分の Google Drive にアクセスできるようになり、`token.pickle`というファイルが作成されているはず
```bash
python citron.py
```

あとは Heroku にデプロイするだけです。