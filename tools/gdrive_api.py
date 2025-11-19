"""
Google Drive API Client - OAuth User Flow
==========================================
Upload files to personal Google Drive using OAuth.
"""

import os
import pickle
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from loguru import logger

from config import APIConfig


SCOPES = ['https://www.googleapis.com/auth/drive.file']


class GoogleDriveClient:
    """OAuth-based Google Drive client for personal accounts"""
    
    def __init__(
        self,
        credentials_path: Optional[str] = None,
        folder_id: Optional[str] = None
    ):
        """
        Initialize with OAuth credentials
        
        Args:
            credentials_path: Path to oauth_credentials.json
            folder_id: Target folder ID (optional)
        """
        self.credentials_path = credentials_path or APIConfig.GOOGLE_CREDENTIALS_PATH
        self.folder_id = folder_id or APIConfig.GOOGLE_DRIVE_FOLDER_ID
        self.token_path = Path(self.credentials_path).parent / "token.pickle"
        
        if not os.path.exists(self.credentials_path):
            raise ValueError(f"OAuth credentials not found: {self.credentials_path}")
        
        self.credentials = self._get_credentials()
        self.service = build('drive', 'v3', credentials=self.credentials)
        
        logger.info("Google Drive OAuth client initialized")
    
    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth credentials"""
        creds = None
        
        # Load saved token
        if self.token_path.exists():
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or get new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing access token...")
                creds.refresh(Request())
            else:
                logger.info("Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save token
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
            logger.info("Token saved")
        
        return creds
    
    def upload_file(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        mime_type: str = 'application/pdf',
        folder_id: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Upload file to Google Drive
        
        Returns:
            (file_id, file_url)
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            file_name = file_name or Path(file_path).name
            
            logger.info(f"Uploading: {file_name}")
            
            file_metadata = {'name': file_name}
            
            target_folder = folder_id or self.folder_id
            if target_folder:
                file_metadata['parents'] = [target_folder]
            
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            file_url = file.get('webViewLink')
            
            self._make_shareable(file_id)
            
            logger.info(f"✅ Uploaded: {file_url}")
            
            return file_id, file_url
            
        except HttpError as e:
            logger.error(f"Drive API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise
    
    def _make_shareable(self, file_id: str):
        """Make file shareable (anyone with link)"""
        try:
            self.service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            logger.info(f"File shareable: {file_id}")
            
        except HttpError as e:
            logger.warning(f"Share failed: {e}")
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file"""
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted: {file_id}")
            return True
        except HttpError as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    def list_files(self, folder_id: Optional[str] = None, max_results: int = 10) -> list:
        """List files in folder"""
        try:
            target_folder = folder_id or self.folder_id
            query = f"'{target_folder}' in parents" if target_folder else None
            
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, webViewLink, createdTime)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} files")
            
            return files
            
        except HttpError as e:
            logger.error(f"List failed: {e}")
            return []


def test_gdrive_connection() -> bool:
    """Test OAuth connection"""
    try:
        client = GoogleDriveClient()
        files = client.list_files(max_results=1)
        logger.info("✅ Drive OAuth working")
        return True
    except Exception as e:
        logger.error(f"❌ OAuth failed: {e}")
        return False
