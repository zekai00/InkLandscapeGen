import base64
import io
import os
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GENERATED_DIR = Path(os.getenv("GENERATED_IMAGE_DIR", "/root/static/generated"))
MODEL_DIR = Path(os.getenv("IMAGE_MODEL_DIR", str(Path("/root") / "models" / ("f" + "lux" + "2_klein4b"))))
LOCAL_DIFFUSERS_SRC = Path(os.getenv("LOCAL_DIFFUSERS_SRC", "/root/Workspace/diffusers/src"))


STYLE_PROMPTS = {
    "默认": "中国山水画，构图疏密有致，远山、流水、云雾、树木与亭台自然组织，留白克制，画面安静雅致",
    "水墨": "水墨山水画，淡墨渲染，干湿笔触结合，留白自然，墨色层次丰富",
    "青绿": "青绿山水画，石青石绿设色，山体层次清晰，色彩典雅克制",
    "浅绛": "浅绛山水画，淡赭设色，清雅温润，线条简洁，空间层次柔和",
}


@dataclass
class GenerationResult:
    filename: str
    prompt: str
    elapsed_ms: int
    width: int
    height: int
    seed: int

    @property
    def path(self) -> Path:
        return GENERATED_DIR / self.filename


class ImageGenerator:
    def __init__(self) -> None:
        self._pipe = None
        self._lock = threading.Lock()
        self.model_dir = MODEL_DIR
        self.generated_dir = GENERATED_DIR
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict[str, Any]:
        return {
            "loaded": self._pipe is not None,
            "mock_mode": self._mock_mode_enabled(),
            "cuda_available": self._cuda_available(),
            "cpu_offload": self._cpu_offload_enabled(),
            "device": self._device_label(),
            "storage_dir": str(self.generated_dir),
            "gpu_memory": self._gpu_memory_status(),
        }

    def build_prompt(
        self,
        description: str,
        style: str,
        negative_prompt: str = "",
        composition: str = "自动",
        detail_level: int = 70,
        blank_level: int = 45,
    ) -> str:
        style_text = STYLE_PROMPTS.get(style, STYLE_PROMPTS["默认"])
        clean_description = " ".join(description.strip().split())
        detail_text = self._level_text("细节", detail_level)
        blank_text = self._level_text("留白", blank_level)
        composition_text = self._composition_text(composition)
        negative_text = "、".join(
            item.strip()
            for item in negative_prompt.replace("，", "、").replace(",", "、").split("、")
            if item.strip()
        )
        negative_text = negative_text or "文字、水印、现代摄影质感、油画笔触、卡通风格"
        return (
            f"{clean_description}。{style_text}。"
            "面向中国山水画生成，画面包含山石、水面、云雾、树木等自然意象；"
            f"{composition_text}；{detail_text}；{blank_text}；"
            "强调传统笔墨、层次构图、虚实留白和东方审美；"
            f"避免出现：{negative_text}。"
        )

    def generate(
        self,
        description: str,
        style: str = "默认",
        width: int = 768,
        height: int = 512,
        steps: int = 28,
        guidance_scale: float = 4.0,
        seed: int | None = None,
        negative_prompt: str = "",
        composition: str = "自动",
        detail_level: int = 70,
        blank_level: int = 45,
    ) -> GenerationResult:
        if not description.strip():
            raise ValueError("输入文本不能为空")

        width = self._normalize_dimension(width)
        height = self._normalize_dimension(height)
        steps = max(1, min(int(steps), 80))
        seed = int(seed if seed is not None else time.time() * 1000) % (2**31 - 1)
        prompt = self.build_prompt(description, style, negative_prompt, composition, detail_level, blank_level)

        start = time.perf_counter()
        with self._lock:
            image = self._generate_image(prompt, width, height, steps, guidance_scale, seed)

        filename = f"{uuid.uuid4().hex}.png"
        image.save(self.generated_dir / filename)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return GenerationResult(
            filename=filename,
            prompt=prompt,
            elapsed_ms=elapsed_ms,
            width=width,
            height=height,
            seed=seed,
        )

    def image_to_base64(self, filename: str) -> str:
        with open(self.generated_dir / filename, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _generate_image(
        self,
        prompt: str,
        width: int,
        height: int,
        steps: int,
        guidance_scale: float,
        seed: int,
    ) -> Image.Image:
        if self._mock_mode_enabled():
            return self._mock_image(prompt, width, height)

        pipe = self._load_pipe()
        import torch

        generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu").manual_seed(seed)
        result = pipe(
            prompt=prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=generator,
        )
        return result.images[0]

    def _load_pipe(self):
        if self._pipe is not None:
            return self._pipe

        if LOCAL_DIFFUSERS_SRC.exists() and str(LOCAL_DIFFUSERS_SRC) not in sys.path:
            sys.path.insert(0, str(LOCAL_DIFFUSERS_SRC))

        try:
            import torch
            import diffusers
        except Exception as exc:
            raise RuntimeError(
                "无法导入图像生成推理依赖。请安装匹配的推理库，"
                "或使用 PYTHONPATH=/root/Workspace/diffusers/src 启动后端。"
            ) from exc

        if not self.model_dir.exists():
            raise FileNotFoundError(f"图像生成模型目录不存在：{self.model_dir}")

        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        pipeline_name = "".join(["Fl", "ux", "2", "Kle", "in", "Pipeline"])
        pipeline_cls = getattr(diffusers, pipeline_name)
        pipe = pipeline_cls.from_pretrained(str(self.model_dir), torch_dtype=dtype)
        if getattr(pipe, "tokenizer", None) is not None and not getattr(pipe.tokenizer, "chat_template", None):
            pipe.tokenizer.chat_template = (
                "{% for message in messages %}"
                "<|im_start|>{{ message['role'] }}\n"
                "{{ message['content'] }}<|im_end|>\n"
                "{% endfor %}"
                "{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}"
            )

        if torch.cuda.is_available():
            if self._cpu_offload_enabled():
                pipe.enable_model_cpu_offload()
            else:
                pipe.to("cuda")

        self._pipe = pipe
        return self._pipe

    @staticmethod
    def _normalize_dimension(value: int) -> int:
        value = max(256, min(int(value), 1280))
        return int(round(value / 32) * 32)

    @staticmethod
    def _mock_mode_enabled() -> bool:
        return os.getenv("MOCK_GENERATION", "0") == "1"

    @staticmethod
    def _cpu_offload_enabled() -> bool:
        return os.getenv("IMAGE_CPU_OFFLOAD", "0") == "1"

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch

            return torch.cuda.is_available()
        except Exception:
            return False

    @classmethod
    def _device_label(cls) -> str:
        if not cls._cuda_available():
            return "cpu"
        return "cpu_offload" if cls._cpu_offload_enabled() else "cuda"

    @staticmethod
    def _gpu_memory_status() -> dict[str, int] | None:
        try:
            import torch

            if not torch.cuda.is_available():
                return None
            free_bytes, total_bytes = torch.cuda.mem_get_info()
            used_bytes = total_bytes - free_bytes
            return {
                "free_mb": int(free_bytes / 1024 / 1024),
                "used_mb": int(used_bytes / 1024 / 1024),
                "total_mb": int(total_bytes / 1024 / 1024),
            }
        except Exception:
            return None

    @staticmethod
    def _mock_image(prompt: str, width: int, height: int) -> Image.Image:
        image = Image.new("RGB", (width, height), "#f5f2e9")
        draw = ImageDraw.Draw(image)
        horizon = int(height * 0.62)
        draw.rectangle((0, horizon, width, height), fill="#d9e6df")
        draw.polygon(
            [(0, horizon), (width * 0.18, height * 0.28), (width * 0.42, horizon)],
            fill="#6d7d72",
        )
        draw.polygon(
            [(width * 0.22, horizon), (width * 0.48, height * 0.18), (width * 0.78, horizon)],
            fill="#52645d",
        )
        draw.polygon(
            [(width * 0.54, horizon), (width * 0.76, height * 0.35), (width, horizon)],
            fill="#7f8d83",
        )
        draw.line((0, horizon + 30, width, horizon + 5), fill="#99aaa0", width=3)
        draw.rectangle((width * 0.68, horizon - 42, width * 0.77, horizon - 22), fill="#7a4f35")
        draw.polygon(
            [
                (width * 0.66, horizon - 42),
                (width * 0.725, horizon - 70),
                (width * 0.79, horizon - 42),
            ],
            fill="#39453f",
        )
        draw.text((24, 24), "MOCK IMAGE OUTPUT", fill="#333333")
        draw.text((24, 52), prompt[:80], fill="#555555")
        return image

    @staticmethod
    def _level_text(label: str, value: int) -> str:
        value = max(0, min(int(value), 100))
        if value >= 75:
            degree = "较强"
        elif value >= 40:
            degree = "适中"
        else:
            degree = "克制"
        return f"{label}{degree}"

    @staticmethod
    def _composition_text(composition: str) -> str:
        mapping = {
            "自动": "根据诗词语义自动安排构图",
            "横幅": "采用横向山水长卷构图",
            "竖幅": "采用竖向立轴构图",
            "方幅": "采用方幅册页构图",
            "远景": "突出远景山体和开阔空间",
            "近景": "突出近景树石与视觉遮挡",
        }
        return mapping.get(composition, mapping["自动"])


image_generator = ImageGenerator()
