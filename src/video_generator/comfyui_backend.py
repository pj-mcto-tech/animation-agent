"""ComfyUI headless API backend (runs SDXL / animation workflows on the RTX 3060 Ti node)."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, Optional

from src.core.media_utils import ffmpeg_executable
from src.video_generator.base import VideoBackend

logger = logging.getLogger(__name__)

DEFAULT_COMFYUI_HOST = "127.0.0.1:8188"


class ComfyUIBackend(VideoBackend):
    """Integrates with a ComfyUI instance to execute generative workflows."""

    name = "comfyui"

    def __init__(
        self,
        server_address: Optional[str] = None,
        workflow_template_path: Optional[str] = None,
        timeout: float = 3.0,
    ):
        self.server_address = (
            server_address or os.getenv("COMFYUI_HOST") or DEFAULT_COMFYUI_HOST
        )
        self.workflow_template_path = workflow_template_path
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())

    def is_available(self) -> bool:
        """Check if the ComfyUI server is reachable."""
        try:
            url = f"http://{self.server_address}/system_stats"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def queue_prompt(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"prompt": workflow_json, "client_id": self.client_id}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"http://{self.server_address}/prompt",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        url = f"http://{self.server_address}/history/{prompt_id}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_image(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        query = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
        url = f"http://{self.server_address}/view?{query}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read()

    def generate_video(
        self,
        prompt: str,
        duration: float,
        output_path: str,
        fps: int = 24,
        width: int = 832,
        height: int = 480,
        negative_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate keyframe and convert to video clip of target duration."""
        if not self.is_available():
            raise RuntimeError(f"ComfyUI server at {self.server_address} is unreachable.")

        workflow_path = self.workflow_template_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "workflows", "image_sdxl_simple.json"
        )
        if not os.path.isfile(workflow_path):
            raise FileNotFoundError(f"Workflow template not found: {workflow_path}")

        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        for _, node_data in workflow.items():
            if isinstance(node_data, dict) and node_data.get("class_type") == "CLIPTextEncode":
                if "inputs" in node_data and "text" in node_data["inputs"]:
                    node_data["inputs"]["text"] = prompt
                    break

        import websocket

        ws = websocket.WebSocket()
        ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
        resp = self.queue_prompt(workflow)
        prompt_id = resp["prompt_id"]

        while True:
            out = ws.recv()
            if isinstance(out, str):
                msg = json.loads(out)
                if msg.get("type") == "executing" and msg.get("data", {}).get("node") is None:
                    break
        ws.close()

        history = self.get_history(prompt_id).get(prompt_id, {})
        images_output = []
        for _, out_data in history.get("outputs", {}).items():
            for img in out_data.get("images", []):
                images_output.append(self.get_image(img["filename"], img.get("subfolder", ""), img.get("type", "output")))
                break

        if not images_output:
            raise RuntimeError("ComfyUI finished execution but yielded no output images.")

        temp_img_path = output_path + ".keyframe.png"
        with open(temp_img_path, "wb") as f:
            f.write(images_output[0])

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        cmd = [
            ffmpeg_executable(), "-y", "-loop", "1", "-i", temp_img_path,
            "-c:v", "libx264", "-t", str(duration), "-pix_fmt", "yuv420p",
            "-vf", f"scale={width}:{height}", "-r", str(fps), output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed converting ComfyUI keyframe to video: {result.stderr}")

        return output_path
