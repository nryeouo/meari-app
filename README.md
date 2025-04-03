# meari-app
マイク式画面音楽伴奏機の演奏を、ノート型コンピュータで利用できるようにするもの  

## 準備
FFmpegを入れる  
- 音程を変えるために必要

動画ファイルを用意する  

## 設置
ルートに`config.py`を作り、場所を書く  
```python
base_dir = "/path/to/your/dir" # meari-appの置き場所
video_files_dir = "/path/to/your/dir" # 動画フォルダの場所
```
