"""
BookOCR - 基于 RK3588 NPU 的书籍文字识别模块。

从 ocr/ocr_api.py 迁移而来，模型路径改为从 config.yaml 读取，
日志接入 logger_manager，移除所有 print()。
"""

import cv2
import numpy as np
import math
import time
from typing import Tuple, List

from modules.logger_manager import logger_manager

try:
    from rknnlite.api import RKNNLite
except ImportError:
    RKNNLite = None

import pyclipper
from shapely.geometry import Polygon


class BookOCRError(Exception):
    """BookOCR 模块异常。"""


class BookOCR:
    """
    基于 RKNN Lite（RK3588 NPU）的书籍 OCR 识别器。

    检测算法：DBNet（热力图分割 + 轮廓提取）
    识别算法：CRNN + CTC 解码
    """

    # 识别模型输入尺寸 (H, W)，宽度足够大以容纳长文本
    REC_INPUT_SIZE = (48, 1024)

    def __init__(self, config_manager=None) -> None:
        self._logger = logger_manager.get_logger(__name__)

        if config_manager is None:
            from modules.config_manager import get_config_manager
            config_manager = get_config_manager()
        self._cfg = config_manager

        # 从 config.yaml 的 ocr 配置段读取路径
        self._det_path = self._cfg.ocr_det_model_path
        self._rec_path = self._cfg.ocr_rec_model_path
        self._dict_path = self._cfg.ocr_dict_path
        self._camera_id = self._cfg.ocr_camera_id
        self._save_path = self._cfg.ocr_save_path
        self._seg_threshold = self._cfg.ocr_segmentation_threshold
        self._min_box_size = self._cfg.ocr_min_box_size
        self._polygon_expand_ratio = self._cfg.ocr_polygon_expand_ratio

        self._logger.info(
            "BookOCR 初始化: det=%s, rec=%s, dict=%s",
            self._det_path, self._rec_path, self._dict_path,
        )

        self.det_rknn = None
        self.rec_rknn = None
        self.keys: List[str] = []
        self.blank_idx: int = 0

        self._load_dict()

    def recognize(self, img: np.ndarray) -> Tuple[List[str], str]:
        self._ensure_models_loaded()

        orig_h, orig_w = img.shape[:2]

        det_input_size = (640, 640)
        img_resized = cv2.resize(img, det_input_size)
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_input = np.expand_dims(img_rgb, axis=0)

        outputs = self.det_rknn.inference(inputs=[img_input])
        pred_map = np.squeeze(outputs[0])  # 分割图 (H, W)

        segmentation_map = (pred_map > self._seg_threshold).astype(np.uint8) * 255
        contours, _ = cv2.findContours(segmentation_map, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        boxes = []
        for contour in contours:
            points, sside = self._get_mini_boxes(contour)
            if sside < self._min_box_size:
                continue

            points = np.array(points)
            poly = Polygon(points)
            if poly.area <= 0:
                continue

            distance = poly.area * self._polygon_expand_ratio / poly.length
            offset = pyclipper.PyclipperOffset()
            offset.AddPath(points, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
            expanded = offset.Execute(distance)
            if len(expanded) == 0:
                continue

            out_box, _ = self._get_mini_boxes(np.array(expanded[0]))
            out_box = np.array(out_box)
            out_box[:, 0] = np.clip(out_box[:, 0] / det_input_size[0] * orig_w, 0, orig_w)
            out_box[:, 1] = np.clip(out_box[:, 1] / det_input_size[1] * orig_h, 0, orig_h)
            boxes.append(out_box)

        boxes = sorted(boxes, key=lambda x: (x[0][1], x[0][0]))

        results_with_boxes = []
        for box in boxes:
            crop_img = self._get_rotate_crop_image(img, box)
            if crop_img.shape[0] == 0 or crop_img.shape[1] == 0:
                continue

            crop_padded = self._resize_and_pad(crop_img)
            crop_rgb = cv2.cvtColor(crop_padded, cv2.COLOR_BGR2RGB)
            crop_input = np.expand_dims(crop_rgb, axis=0)

            rec_out = np.squeeze(self.rec_rknn.inference(inputs=[crop_input])[0])
            argmax_idx = np.argmax(rec_out, axis=1)

            text = ""
            for i in range(len(argmax_idx)):
                curr_idx = argmax_idx[i]
                if curr_idx != self.blank_idx and not (i > 0 and curr_idx == argmax_idx[i - 1]):
                    if curr_idx < len(self.keys):
                        text += self.keys[curr_idx]

            if text.strip():
                results_with_boxes.append((text, box))

        formatted_text = self._group_lines(results_with_boxes)
        raw_list = [item[0] for item in results_with_boxes]

        self._logger.debug(
            "OCR 识别完成: chars=%d, text_len=%d",
            len(raw_list), len(formatted_text),
        )
        return raw_list, formatted_text

    def recognize_from_file(self, img_path: str) -> Tuple[List[str], str]:
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"无法读取图像文件: {img_path}")
        return self.recognize(img)

    def release(self) -> None:
        if self.det_rknn is not None:
            self.det_rknn.release()
            self.det_rknn = None
            self._logger.debug("检测模型已释放")
        if self.rec_rknn is not None:
            self.rec_rknn.release()
            self.rec_rknn = None
            self._logger.debug("识别模型已释放")

    def _load_dict(self) -> None:
        with open(self._dict_path, "r", encoding="utf-8") as f:
            keys = [line.strip("\n").strip("\r") for line in f.readlines()]
        self.keys = ["blank"] + keys + [" "]
        self.blank_idx = 0
        self._logger.debug("字符字典加载完成: %d 个字符", len(self.keys))

    def _ensure_models_loaded(self) -> None:
        if self.det_rknn is not None and self.rec_rknn is not None:
            return

        if RKNNLite is None:
            raise BookOCRError("rknnlite 未安装，无法加载 RKNN 模型")

        self._logger.info("正在加载检测模型: %s", self._det_path)
        self.det_rknn = RKNNLite()
        ret = self.det_rknn.load_rknn(self._det_path)
        if ret != 0:
            raise BookOCRError(f"检测模型加载失败: {self._det_path}")
        ret = self.det_rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
        if ret != 0:
            raise BookOCRError("检测模型 NPU 初始化失败")

        self._logger.info("正在加载识别模型: %s", self._rec_path)
        self.rec_rknn = RKNNLite()
        ret = self.rec_rknn.load_rknn(self._rec_path)
        if ret != 0:
            raise BookOCRError(f"识别模型加载失败: {self._rec_path}")
        ret = self.rec_rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
        if ret != 0:
            raise BookOCRError("识别模型 NPU 初始化失败")

        self._logger.info("RKNN 模型加载完成")

    def _get_mini_boxes(self, contour):
        bounding_box = cv2.minAreaRect(contour)
        points = sorted(list(cv2.boxPoints(bounding_box)), key=lambda x: x[0])

        if points[1][1] > points[0][1]:
            index_1, index_4 = 0, 1
        else:
            index_1, index_4 = 1, 0
        if points[3][1] > points[2][1]:
            index_2, index_3 = 2, 3
        else:
            index_2, index_3 = 3, 2

        box = [points[index_1], points[index_2], points[index_3], points[index_4]]
        return box, min(bounding_box[1])

    def _get_rotate_crop_image(self, img: np.ndarray, points: np.ndarray) -> np.ndarray:
        points = np.array(points, dtype=np.float32)
        img_crop_width = int(max(
            np.linalg.norm(points[0] - points[1]),
            np.linalg.norm(points[2] - points[3]),
        ))
        img_crop_height = int(max(
            np.linalg.norm(points[0] - points[3]),
            np.linalg.norm(points[1] - points[2]),
        ))

        pts_std = np.float32([
            [0, 0], [img_crop_width, 0],
            [img_crop_width, img_crop_height], [0, img_crop_height],
        ])
        M = cv2.getPerspectiveTransform(points, pts_std)
        dst_img = cv2.warpPerspective(
            img, M, (img_crop_width, img_crop_height),
            borderMode=cv2.BORDER_REPLICATE, flags=cv2.INTER_CUBIC,
        )
        return dst_img

    def _resize_and_pad(
        self,
        img: np.ndarray,
        target_h: int = REC_INPUT_SIZE[0],
        target_w: int = REC_INPUT_SIZE[1],
    ) -> np.ndarray:
        h, w = img.shape[:2]
        ratio = w / float(h)
        new_w = min(int(math.ceil(target_h * ratio)), target_w)

        resized_img = cv2.resize(img, (new_w, target_h))

        padded_img = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        padded_img[:] = 127
        padded_img[:, 0:new_w, :] = resized_img
        return padded_img

    def _group_lines(self, results_with_boxes: List[Tuple[str, np.ndarray]]) -> str:
        if not results_with_boxes:
            return ""

        processed = []
        for text, box in results_with_boxes:
            cy = np.mean(box[:, 1])
            cx = np.mean(box[:, 0])
            h = np.max(box[:, 1]) - np.min(box[:, 1])
            processed.append({"text": text, "cx": cx, "cy": cy, "h": h})

        processed.sort(key=lambda item: item["cy"])

        lines = []
        current_line = [processed[0]]

        for i in range(1, len(processed)):
            item = processed[i]
            prev_item = current_line[-1]

            avg_h = (item["h"] + prev_item["h"]) / 2.0
            if abs(item["cy"] - prev_item["cy"]) < avg_h * 0.5:
                current_line.append(item)
            else:
                lines.append(current_line)
                current_line = [item]

        lines.append(current_line)

        formatted_text = ""
        for line in lines:
            line.sort(key=lambda item: item["cx"])
            line_text = "".join([item["text"] for item in line])
            formatted_text += line_text + "\n"

        return formatted_text.strip()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


def enhance_text_image(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast_img = clahe.apply(blurred)
    return cv2.cvtColor(contrast_img, cv2.COLOR_GRAY2BGR)


def capture_from_camera(
    camera_id: int = 0,
    save_path: str = "camera_capture.jpg",
) -> np.ndarray:
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 (ID: {camera_id})")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    for _ in range(30):
        cap.read()
        time.sleep(0.05)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError("无法读取摄像头画面")

    cv2.imwrite(save_path, frame)
    return frame
