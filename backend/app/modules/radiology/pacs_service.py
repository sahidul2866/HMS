import base64
import json
from urllib import parse, request

from app.core.config import get_settings


class OrthancPACSService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.orthanc_base_url
        self.auth_header = self._basic_auth(self.settings.orthanc_username, self.settings.orthanc_password)

    def upload_instance(self, content: bytes) -> dict:
        response = self._call("POST", "/instances", content, "application/dicom")
        return json.loads(response.decode("utf-8")) if response else {}

    def get_study(self, orthanc_study_id: str) -> dict:
        response = self._call("GET", f"/studies/{orthanc_study_id}")
        return json.loads(response.decode("utf-8")) if response else {}

    def list_studies(self) -> list[str]:
        response = self._call("GET", "/studies")
        return json.loads(response.decode("utf-8")) if response else []

    def get_series(self, orthanc_series_id: str) -> dict:
        response = self._call("GET", f"/series/{orthanc_series_id}")
        return json.loads(response.decode("utf-8")) if response else {}

    def get_instance(self, orthanc_instance_id: str) -> dict:
        response = self._call("GET", f"/instances/{orthanc_instance_id}")
        return json.loads(response.decode("utf-8")) if response else {}

    def list_dicomweb_studies(self) -> list[dict]:
        root = self.settings.orthanc_dicomweb_root.rstrip("/")
        response = self._call("GET", f"{root}/studies")
        return json.loads(response.decode("utf-8")) if response else []

    def build_orthanc_viewer_url(self, *, orthanc_study_id: str | None, study_uid: str) -> str:
        if self.settings.dicom_viewer_url_template:
            return self.settings.dicom_viewer_url_template.format(
                study_uid=study_uid,
                orthanc_study_id=orthanc_study_id or "",
                orthanc_base_url=self.settings.orthanc_base_url,
                orthanc_dicomweb_root=self.settings.orthanc_dicomweb_root,
                orthanc_dicomweb_url=f"{self.settings.orthanc_base_url}{self.settings.orthanc_dicomweb_root}",
            )
        query = parse.urlencode(
            {
                "StudyInstanceUID": study_uid,
                "orthanc": self.settings.orthanc_base_url,
                "dicomweb": f"{self.settings.orthanc_base_url}{self.settings.orthanc_dicomweb_root}",
                "orthancStudyId": orthanc_study_id or "",
            }
        )
        return f"{self.settings.dicom_viewer_base_url}?{query}"

    def _call(self, method: str, path: str, data: bytes | None = None, content_type: str | None = None) -> bytes:
        headers = {"Authorization": self.auth_header}
        if content_type:
            headers["Content-Type"] = content_type
        req = request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        with request.urlopen(req, timeout=15) as resp:
            return resp.read()

    @staticmethod
    def _basic_auth(username: str, password: str) -> str:
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
        return f"Basic {token}"
