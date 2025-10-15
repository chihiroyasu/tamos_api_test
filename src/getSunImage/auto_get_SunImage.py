import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime, timedelta, timezone
import time

SCOPES = ['https://www.googleapis.com/auth/drive']

credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/src/credentials.json")
print("Using credentials file:", credentials_path)  # デバッグ用
sa_creds = service_account.Credentials.from_service_account_file(credentials_path)
scoped_creds = sa_creds.with_scopes(SCOPES)
drive_service = build('drive', 'v3', credentials=scoped_creds)

# 最新画像のファイルidを取得する
def get_seestar_image(folder_id):
    results = []
    query = f"'{folder_id}' in parents and trashed = false"
    
    response = drive_service.files().list(
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        q=query,
        fields="files(id, name)"
    ).execute()
    files = response.get('files', [])
    for file in files:
        results.append(file)
    result = results[0]
    # print(result)
    return result
    
# get_seestar_image('1UByJCfA0SMTIqMrldrRejWo0ZBaFgDBC')


def download_file_with_service_account(json_keyfile_path, file_id, download_path):
    """
    Downloads a file from Google Drive using a service account and saves it to the specified path.
    
    Args:
        json_keyfile_path (str): Path to the service account JSON key file.
        file_id (str): ID of the file to download.
        download_path (str): Path where the downloaded file should be saved.
    
    Returns:
        bool: True if the download and save were successful, False otherwise.
    """
    try:
        creds = service_account.Credentials.from_service_account_file(json_keyfile_path)
        service = build("drive", "v3", credentials=creds)
        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")

        print("ダウンロード")
        with open(download_path, "wb") as f:
            f.write(file_content.getvalue())
        
        print(f"{download_path}")
        return True

    except HttpError as error:
        print(f"An error occurred: {error}")
        return False


if __name__ == "__main__":
    latest_file_info = get_seestar_image('1UByJCfA0SMTIqMrldrRejWo0ZBaFgDBC')
    print(latest_file_info)
    file_id = latest_file_info["id"]
    json = "/home/user/toms-server/tamc/services/backend/src/getSunImage/takemanualobservation-ca0d2f5bfc53.json"
    # file_id = "192MK9Bl51micmnHvfg6gfwEdjTzsqMlP"
    JST = timezone(timedelta(hours=+9), 'JST')
    year = time.strftime("%Y")
    mon = time.strftime("%m")
    now = datetime.now(JST)
    formatted_time = now.strftime('%Y%m%d')
    file_name = f"{formatted_time}.png"
    path = f"/mnt/data/sunspot/{year}/{mon}/{file_name}"
    success = download_file_with_service_account(json, file_id, path)
    if success:
        print("Downloadできた")

