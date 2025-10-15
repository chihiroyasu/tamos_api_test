# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# import os

# # APIのスコープ（アクセス範囲）を指定
# SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

# # 資格情報ファイルのパス
# TOKEN_PATH = '1Idc_rFvxje-hNuYjzHG2i61FYTzeZnyr'

# def authenticate():
#     flow = InstalledAppFlow.from_client_secrets_file(
#         'credentials.json', SCOPES)
#     credentials = flow.run_local_server(port=0)
#     with open(TOKEN_PATH, 'w') as token:
#         token.write(credentials.to_json())

# def get_drive_files():
#     creds = None
#     # 資格情報の読み込み
#     if os.path.exists(TOKEN_PATH):
#         creds = Credentials.from_authorized_user_file(TOKEN_PATH)

#     # 認証されていない場合は認証を行う
#     if not creds or not creds.valid:
#         authenticate()
#         creds = Credentials.from_authorized_user_file(TOKEN_PATH)

#     # Drive APIのビルド
#     service = build('drive', 'v3', credentials=creds)

#     # ファイル一覧を取得
#     results = service.files().list(
#         pageSize=10, fields="files(id, name, webViewLink)").execute()
#     files = results.get('files', [])

#     if not files:
#         print('No files found.')
#     else:
#         print('Files:')
#         for file in files:
#             print(f"Name: {file['name']}, URL: {file['webViewLink']}")

# if __name__ == '__main__':
#     get_drive_files()







# from google.oauth2 import service_account
# from googleapiclient.discovery import build

# SCOPES = ['https://www.googleapis.com/auth/drive']
# SHARE_FOLDER_ID = '1-TrWD1mqMZGeNw-ST7-_0vhSTL_5WzzJ'

# # サービスアカウントのJSONファイルを指定して認証情報を取得
# sa_creds = service_account.Credentials.from_service_account_file('credentials.json')
# scoped_creds = sa_creds.with_scopes(SCOPES)

# # Google Drive APIサービスの構築
# drive_service = build('drive', 'v3', credentials=scoped_creds)

# def list_files_in_folder(folder_id):
#     results = []
#     query = f"'{folder_id}' in parents and trashed = false"
    
#     # Google Drive APIを使用してファイルの一覧を取得
#     response = drive_service.files().list(
#         supportsAllDrives=True,
#         includeItemsFromAllDrives=True,
#         q=query,
#         fields="files(id, name)"
#     ).execute()

#     files = response.get('files', [])

#     for file in files:
#         results.append(file)

#     return results

# if __name__ == '__main__':
#     folder_id = SHARE_FOLDER_ID
#     image_files = list_files_in_folder(folder_id)

#     print("Image files in the folder:")
#     for image_file in image_files:
#         file_id = image_file['id']
#         file_name = image_file['name']
#         print(f"File ID: {file_id}, File Name: {file_name}")





# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from googleapiclient.discovery import build
# from google.oauth2 import service_account
# from fastapi.responses import JSONResponse

# app = FastAPI()

# # CORSミドルウェアを有効にする
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["https://100.119.204.18:3000", "https://0.0.0.0:3000", "http://localhost:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Google Drive API関連の設定
# SCOPES = ['https://www.googleapis.com/auth/drive']
# FOLDER_IDS = ['1-dKgQTNuxM4l1el-s4h0tgMxPJpoLIAR', '1-YCLL65pizIEjBGebsfdU48VE7lv63nL', '1-TrWD1mqMZGeNw-ST7-_0vhSTL_5WzzJ']  # 各フォルダのIDを追加

# sa_creds = service_account.Credentials.from_service_account_file('credentials.json')
# scoped_creds = sa_creds.with_scopes(SCOPES)
# drive_service = build('drive', 'v3', credentials=scoped_creds)

# def list_files_in_folder(folder_id):
#     results = []
#     query = f"'{folder_id}' in parents and trashed = false"
    
#     # Google Drive APIを使用してファイルの一覧を取得
#     response = drive_service.files().list(
#         supportsAllDrives=True,
#         includeItemsFromAllDrives=True,
#         q=query,
#         fields="files(id, name)"
#     ).execute()

#     files = response.get('files', [])

#     for file in files:
#         results.append(file)

#     return results

# @app.get("/drive")
# async def get_all_drive_files():
#     all_files = {}
#     for folder_id in FOLDER_IDS:
#         folder_files = list_files_in_folder(folder_id)
#         all_files[folder_id] = [{"id": file['id'], "name": file['name']} for file in folder_files]

#     # 全フォルダのファイルのIDと名前の一覧をJSONで応答
#     return JSONResponse(content=all_files)

# @app.get("/drive/{folder_id}")
# async def get_drive_files(folder_id: str):
#     if folder_id not in FOLDER_IDS:
#         return JSONResponse(content={"error": "Invalid folder ID"})

#     folder_files = list_files_in_folder(folder_id)
#     # フォルダのファイルのIDと名前の一覧をJSONで応答
#     return JSONResponse(content={"folder_id": folder_id, "files": [{"id": file['id'], "name": file['name']} for file in folder_files]})

# @app.get("/")
# def read_root():
#     return {"Hello": "World"}

# # FastAPIをHTTPSで実行する
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=5000, ssl_keyfile="key.pem", ssl_certfile="cert.pem")








# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from googleapiclient.discovery import build
# from google.oauth2 import service_account
# from fastapi.responses import JSONResponse

# app = FastAPI()

# # CORSミドルウェアを有効にする
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["https://100.119.204.18:3000", "https://0.0.0.0:3000", "http://localhost:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Google Drive API関連の設定
# SCOPES = ['https://www.googleapis.com/auth/drive']
# FOLDER_IDS = {'1962June': '1-dKgQTNuxM4l1el-s4h0tgMxPJpoLIAR', '1962September': '1-YCLL65pizIEjBGebsfdU48VE7lv63nL', '1962December': '1-TrWD1mqMZGeNw-ST7-_0vhSTL_5WzzJ'}
# sa_creds = service_account.Credentials.from_service_account_file('credentials.json')
# scoped_creds = sa_creds.with_scopes(SCOPES)
# drive_service = build('drive', 'v3', credentials=scoped_creds)

# def list_files_in_folder(folder_id):
#     results = []
#     query = f"'{folder_id}' in parents and trashed = false"
    
#     # Google Drive APIを使用してファイルの一覧を取得
#     response = drive_service.files().list(
#         supportsAllDrives=True,
#         includeItemsFromAllDrives=True,
#         q=query,
#         fields="files(id, name)"
#     ).execute()

#     files = response.get('files', [])

#     for file in files:
#         results.append(file)

#     return results

# # 各フォルダに対してエンドポイントを作成
# for folder_name, folder_id in FOLDER_IDS.items():
#     @app.get(f"/drive/{folder_name}")
#     async def get_drive_files(folder_name: str = folder_name):
#         folder_files = list_files_in_folder(FOLDER_IDS.get(folder_name, ""))
#         # フォルダのファイルのIDと名前の一覧をJSONで応答
#         return JSONResponse(content={"folder_name": folder_name, "files": [{"id": file['id'], "name": file['name']} for file in folder_files]})

# @app.get("/")
# def read_root():
#     return {"Hello": "World"}

# # FastAPIをHTTPSで実行する
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=5000, ssl_keyfile="key.pem", ssl_certfile="cert.pem")













    
    
    
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Google Drive APIの認証情報を読み込む
credentials = service_account.Credentials.from_service_account_file(
    './credentials.json',
    scopes=['https://www.googleapis.com/auth/drive']
)

# Google Drive APIのクライアントを構築
drive_service = build('drive', 'v3', credentials=credentials)

def list_folders_in_folder(folder_id):
    results = []
    page_token = None

    while True:
        # フォルダ内のファイル一覧を取得
        response = drive_service.files().list(
            q=f"'{folder_id}' in parents",
            spaces='drive',
            fields='nextPageToken, files(id, name, appProperties)',
            pageToken=page_token
        ).execute()

        # ファイル一覧からフォルダのみを抽出
        folders = [file for file in response.get('files', []) if 'application/vnd.google-apps.folder' in file.get('appProperties', {}).values()]
        results.extend(folders)

        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break

    return results

# 特定のフォルダのIDを指定
target_folder_id = '1-JAKE91NwGvN41vUKngsZEQyBqdsUD-g'

# フォルダ内のフォルダID一覧を取得
folder_list = list_folders_in_folder(target_folder_id)

# 結果を表示
for folder in folder_list:
    print(f"Folder Name: {folder['name']}, Folder ID: {folder['id']}")

