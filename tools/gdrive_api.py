"""
Google Drive API Client
=======================
Wrapper for Google Drive API to upload PDF reports.
"""

import os
from typing import Optional
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from loguru import logger

from config import APIConfig


class GoogleDriveClient:
    """Client pour uploader des fichiers sur Google Drive"""
    
    def __init__(
        self,
        credentials_path: Optional[str] = None,
        folder_id: Optional[str] = None
    ):
        """
        Initialize Google Drive client
        
        Args:
            credentials_path: Path to service account credentials JSON
            folder_id: Target folder ID on Drive (optional)
        """
        self.credentials_path = credentials_path or APIConfig.GOOGLE_CREDENTIALS_PATH
        self.folder_id = folder_id or APIConfig.GOOGLE_DRIVE_FOLDER_ID
        
        if not os.path.exists(self.credentials_path):
            raise ValueError(f"Credentials file not found: {self.credentials_path}")
        
        # Initialize credentials
        self.credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        # Build Drive service
        self.service = build('drive', 'v3', credentials=self.credentials)
        
        logger.info("Google Drive client initialized")
    
    def upload_file(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        mime_type: str = 'application/pdf',
        folder_id: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Upload a file to Google Drive
        
        Args:
            file_path: Local path to the file
            file_name: Name for the file on Drive (defaults to original name)
            mime_type: MIME type of the file
            folder_id: Target folder ID (overrides default)
            
        Returns:
            Tuple of (file_id, file_url)
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Determine file name
            if file_name is None:
                file_name = Path(file_path).name
            
            logger.info(f"Uploading file to Google Drive: {file_name}")
            
            # File metadata
            file_metadata = {
                'name': file_name,
            }
            
            # Add to specific folder if provided
            target_folder = folder_id or self.folder_id
            if target_folder:
                file_metadata['parents'] = [target_folder]
            
            # Upload file
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            file_url = file.get('webViewLink')
            
            # Make file shareable (anyone with link can view)
            self._make_shareable(file_id)
            
            logger.info(f"✅ File uploaded successfully: {file_url}")
            
            return file_id, file_url
            
        except HttpError as e:
            logger.error(f"Google Drive API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise
    
    def _make_shareable(self, file_id: str):
        """
        Make a file shareable (anyone with link can view)
        
        Args:
            file_id: Google Drive file ID
        """
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader',
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            logger.info(f"File {file_id} is now shareable")
            
        except HttpError as e:
            logger.warning(f"Failed to make file shareable: {e}")
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Google Drive
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            True if successful
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"File {file_id} deleted successfully")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    def list_files(self, folder_id: Optional[str] = None, max_results: int = 10) -> list:
        """
        List files in a folder
        
        Args:
            folder_id: Folder ID (defaults to configured folder)
            max_results: Maximum number of files to return
            
        Returns:
            List of file metadata
        """
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
            logger.error(f"Failed to list files: {e}")
            return []


# Utility function for testing
def test_gdrive_connection() -> bool:
    """Test Google Drive API connection"""
    try:
        client = GoogleDriveClient()
        
        # Try to list files (should work even if empty)
        files = client.list_files(max_results=1)
        
        logger.info(f"✅ Google Drive connection successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Google Drive connection failed: {e}")
        return False