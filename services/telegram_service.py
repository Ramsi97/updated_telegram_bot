import httpx
from app.config import settings
from pathlib import Path
from typing import Optional

class TelegramService:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"{settings.API_BASE_URL}/bot{token}"
        self.file_url = f"{settings.API_BASE_URL}/file/bot{token}"

    async def send_message(self, chat_id: int, text: str) -> Optional[int]:
        """Send text message to Telegram chat with detailed error reporting"""
        try:
            print(f"📤 Attempting to send message to chat {chat_id}: {text[:50]}...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                    timeout=30.0
                )
                
                print(f"📡 Telegram API response status: {response.status_code}")
                print(f"📡 Telegram API response text: {response.text}")
                
                if response.status_code == 200:
                    data = response.json()
                    message_id = data.get("result", {}).get("message_id")
                    print(f"✅ Message sent successfully! Message ID: {message_id}")
                    return message_id
                else:
                    error_data = response.json()
                    print(f"❌ Telegram API error: {error_data}")
                    return None
                    
        except httpx.TimeoutException:
            print("❌ Timeout while sending message to Telegram")
            return None
        except Exception as e:
            print(f"❌ Unexpected error sending message: {e}")
            return None

    async def edit_message(self, chat_id: int, message_id: int, new_text: str) -> bool:
        """Edit a previously sent message with new text"""
        try:
            print(f"✏️ Editing message {message_id} in chat {chat_id} → {new_text[:50]}...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/editMessageText",
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "text": new_text
                    },
                    timeout=30.0
                )

                print(f"📡 Telegram edit API response status: {response.status_code}")
                print(f"📡 Telegram edit API response text: {response.text}")

                if response.status_code == 200:
                    print("✅ Message edited successfully!")
                    return True
                else:
                    error_data = response.json()
                    print(f"❌ Failed to edit message: {error_data}")
                    return False

        except httpx.TimeoutException:
            print("❌ Timeout while editing Telegram message")
            return False
        except Exception as e:
            print(f"❌ Unexpected error editing message: {e}")
            return False

    async def send_photo_bytes(self, chat_id: int, image_bytes: bytes, filename: str = "image.jpg") -> bool:
        """Send photo using image bytes with detailed error reporting"""
        try:
            print(f"📤 Attempting to send photo to chat {chat_id}")
            print(f"   Image size: {len(image_bytes)} bytes")
            print(f"   Filename: {filename}")
            
            async with httpx.AsyncClient() as client:
                files = {"photo": (filename, image_bytes, "image/jpeg")}
                response = await client.post(
                    f"{self.base_url}/sendPhoto",
                    data={"chat_id": chat_id},
                    files=files,
                    timeout=60.0  # Increase timeout for large images
                )
                
                print(f"📡 Telegram photo API response status: {response.status_code}")
                print(f"📡 Telegram photo API response text: {response.text}")
                
                if response.status_code == 200:
                    print("✅ Photo sent successfully!")
                    return True
                else:
                    error_data = response.json()
                    print(f"❌ Telegram photo API error: {error_data}")
                    return False
                    
        except httpx.TimeoutException:
            print("❌ Timeout while sending photo to Telegram")
            return False
        except Exception as e:
            print(f"❌ Unexpected error sending photo: {e}")
            return False

    async def send_photo(self, chat_id: int, image_path: Path) -> bool:
        """Send photo from file path"""
        try:
            async with httpx.AsyncClient() as client:
                with open(image_path, "rb") as f:
                    files = {"photo": f}
                    response = await client.post(
                        f"{self.base_url}/sendPhoto",
                        data={"chat_id": chat_id},
                        files=files
                    )
                    return response.status_code == 200
        except Exception as e:
            print(f"Failed to send photo from file: {e}")
            return False

    async def download_file(self, file_id: str) -> bytes:
        """Download file from Telegram"""
        try:
            async with httpx.AsyncClient() as client:
                file_info = await client.get(
                    f"{self.base_url}/getFile",
                    params={"file_id": file_id}
                )
                file_path = file_info.json()["result"]["file_path"]
                
                file_data = await client.get(f"{self.file_url}/{file_path}")
                return file_data.content
                
        except Exception as e:
            raise Exception(f"Failed to download file from Telegram: {str(e)}")

    async def set_webhook(self) -> bool:
        """Set webhook URL with Telegram"""
        try:
            async with httpx.AsyncClient() as client:
                webhook_url = f"{settings.WEBHOOK_URL}/api/v1/webhook"
                response = await client.post(
                    f"{self.base_url}/setWebhook",
                    json={"url": webhook_url}
                )
                print(f"Webhook set to: {webhook_url}")
                return response.status_code == 200
        except Exception as e:
            print(f"Failed to set webhook: {e}")
            return False

    async def get_me(self) -> Optional[dict]:
        """Test bot authentication and get bot info"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/getMe")
                if response.status_code == 200:
                    return response.json()["result"]
                return None
        except Exception as e:
            print(f"Failed to get bot info: {e}")
            return None
