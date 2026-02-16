import os
import pickle
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from core.db_manager import DBManager


class YouTubeUploader:
    def __init__(self):
        self.db = DBManager()
        # This scope allows us to Manage (Upload/Edit) your YouTube videos
        self.SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        self.api_service_name = "youtube"
        self.api_version = "v3"
        self.client_secrets_file = "client_secrets.json"
        self.token_file = "token.pickle"  # Stores your login session

        self.youtube = self.get_authenticated_service()

    def get_authenticated_service(self):
        """Handles the OAuth2 Login flow seamlessly."""
        creds = None
        # 1. Check if we have a saved login token
        if os.path.exists(self.token_file):
            with open(self.token_file, "rb") as token:
                creds = pickle.load(token)

        # 2. If no valid login, open browser to log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, self.SCOPES
                )
                # Opens a local web server to catch the login response
                creds = flow.run_local_server(port=0)

            # 3. Save the login for next time
            with open(self.token_file, "wb") as token:
                pickle.dump(creds, token)

        return build(self.api_service_name, self.api_version, credentials=creds)

    def upload_video(self):
        # 1. Find a video that is packaged and ready
        task = self.db.collection.find_one({"status": "completed_packaged"})

        if not task:
            print("📭 No packaged videos found to upload.")
            return

        print(f"🚀 Starting Upload for: {task['title']}")

        video_path = task.get("final_video_path")
        if not os.path.exists(video_path):
            print("❌ Error: Video file not found on disk.")
            return

        # 2. Prepare Metadata (Title, Description, Tags)
        # Category ID 28 = Science & Technology
        request_body = {
            "snippet": {
                "categoryId": "28",
                "title": task["title"][:100],  # YouTube limit is 100 chars
                "description": f"{task['content'][:4000]}\n\n#Shorts\n\nSource: {task.get('source_url', '')}",
                "tags": task.get("tags", "").split(",") + ["Shorts", "AI", "Tech"],
            },
            "status": {
                # ⚠️ 'private' is safest for testing. Change to 'public' when confident.
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False,
            },
        }

        # 3. Upload File
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

        request = self.youtube.videos().insert(
            part="snippet,status", body=request_body, media_body=media
        )

        try:
            print("   ⏳ Uploading... (This may take a minute)")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"      Uploaded {int(status.progress() * 100)}%")

            # 4. Success Handling
            if "id" in response:
                video_id = response["id"]
                print(f"   ✅ Upload Successful! Video ID: {video_id}")
                print(f"   🔗 Link: https://youtu.be/{video_id}")

                # 5. Update Database with the new YouTube ID
                self.db.collection.update_one(
                    {"_id": task["_id"]},
                    {
                        "$set": {
                            "status": "uploaded",
                            "youtube_id": video_id,
                            "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    },
                )
            else:
                print(f"   ❌ Upload failed with unexpected response: {response}")

        except Exception as e:
            print(f"   ❌ API Error: {e}")


if __name__ == "__main__":
    uploader = YouTubeUploader()
    uploader.upload_video()
