# meari-app
マイク式画面音楽伴奏機の演奏を、ノート型コンピュータで利用できるようにするもの  

## 準備
FFmpegを入れる  
- 音程を変えるために必要

動画ファイルを用意する  
お好みでBGMファイル（`*.mp3`）を用意する  

## 設置
ルートに`config.py`を作り、場所を書く  
```python
base_dir = "/path/to/your/dir" # meari-appの置き場所
video_files_dir = "/path/to/your/dir" # 動画フォルダの場所。下に bgm フォルダを配置可能
resv_api_url = "https://example.com/api/v1/" #予約システム連携用
```

`python3 -m pip install -r requirements.txt`  

## 使用開始
1. `python3 flask_server.py`  
2. Webブラウザで`127.0.0.1:5556`に接続  
3. ［프로그람시동］ボタンを押す

## 選曲
1. 数字4桁を入れると自動確定  
2. `-`/`+`で音程を調整したら`Enter`
  
間違えたとき、演奏を中断するときは`Esc`  
音程が`0`以外だと変換処理が走り、再生までに少し時間が掛かる  

## おまけ
選曲番号`98**`で`**`分間のタイマー  
`Esc`で停止

## 使用終了
ターミナルで`Control`+`C`
