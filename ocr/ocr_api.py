import cv2
import numpy as np
import math
import json
import time
from rknnlite.api import RKNNLite
import pyclipper
from shapely.geometry import Polygon

# 模型与字典路径
DET_MODEL_PATH = 'ocr_models/det_model_int8.rknn'   # 检测模型
REC_MODEL_PATH = 'ocr_models/rec_v4_fp16_wide.rknn' # 识别模型
DICT_PATH = 'ocr_models/ppocr_keys_v1.txt'           # 字符字典

CAMERA_ID = 0

# 检测模型输入尺寸 (H, W)
DET_INPUT_SIZE = (640, 640)
# 识别模型输入尺寸 (H, W)，宽度足够大以容纳长文本
REC_INPUT_SIZE = (48, 1024)
SEGMENTATION_THRESHOLD = 0.3   # 分割图二值化阈值
MIN_BOX_SIZE = 3               # 最小检测框尺寸（像素），过滤噪点
POLYGON_EXPAND_RATIO = 1.8    # 多边形扩张系数，用于框膨胀


class BookOCR:

    def __init__(self, det_path=DET_MODEL_PATH, rec_path=REC_MODEL_PATH, dict_path=DICT_PATH):
        self.det_rknn = RKNNLite()
        ret = self.det_rknn.load_rknn(det_path)
        if ret != 0:
            raise RuntimeError(f"检测模型加载失败: {det_path}")
        ret = self.det_rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
        if ret != 0:
            raise RuntimeError("检测模型 NPU 初始化失败")

        self.rec_rknn = RKNNLite()
        ret = self.rec_rknn.load_rknn(rec_path)
        if ret != 0:
            raise RuntimeError(f"识别模型加载失败: {rec_path}")
        ret = self.rec_rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
        if ret != 0:
            raise RuntimeError("识别模型 NPU 初始化失败")

        with open(dict_path, 'r', encoding='utf-8') as f:
            keys = [line.strip('\n').strip('\r') for line in f.readlines()]
        self.keys = ['blank'] + keys + [' ']
        self.blank_idx = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def _get_mini_boxes(self, contour):
        """将轮廓转为四点框 [左上, 右上, 右下, 左下]，返回框和短边长度"""
        bounding_box = cv2.minAreaRect(contour)
        points = sorted(list(cv2.boxPoints(bounding_box)), key=lambda x: x[0])

        # 按 y 坐标排序，确定四点顺序
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

    def _get_rotate_crop_image(self, img, points):
        """透视变换：将四点框区域矫正为水平矩形切片"""
        points = np.array(points, dtype=np.float32)
        # 计算矫正后宽高（取对边最大值）
        img_crop_width = int(max(np.linalg.norm(points[0] - points[1]),
                                 np.linalg.norm(points[2] - points[3])))
        img_crop_height = int(max(np.linalg.norm(points[0] - points[3]),
                                  np.linalg.norm(points[1] - points[2])))

        pts_std = np.float32([[0, 0], [img_crop_width, 0],
                              [img_crop_width, img_crop_height], [0, img_crop_height]])
        M = cv2.getPerspectiveTransform(points, pts_std)
        dst_img = cv2.warpPerspective(img, M, (img_crop_width, img_crop_height),
                                      borderMode=cv2.BORDER_REPLICATE, flags=cv2.INTER_CUBIC)
        return dst_img

    def _resize_and_pad(self, img, target_h=REC_INPUT_SIZE[0], target_w=REC_INPUT_SIZE[1]):
        """等比缩放 + 右侧灰边填充至固定尺寸（保持宽高比）"""
        h, w = img.shape[:2]
        ratio = w / float(h)
        new_w = min(int(math.ceil(target_h * ratio)), target_w)

        resized_img = cv2.resize(img, (new_w, target_h))

        padded_img = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        padded_img[:] = 127
        padded_img[:, 0:new_w, :] = resized_img
        return padded_img

    def _group_lines(self, results_with_boxes):
        """按中心点 y 坐标聚类行，同行内按 x 排序，拼接为文本"""
        if not results_with_boxes:
            return ""

        processed = []
        for text, box in results_with_boxes:
            cy = np.mean(box[:, 1])   # 框中心 y
            cx = np.mean(box[:, 0])   # 框中心 x
            h = np.max(box[:, 1]) - np.min(box[:, 1])  # 框高度
            processed.append({'text': text, 'cx': cx, 'cy': cy, 'h': h})

        # 按 y 排序后，用 0.5 倍平均高度判断是否属于同一行
        processed.sort(key=lambda item: item['cy'])

        lines = []
        current_line = [processed[0]]

        for i in range(1, len(processed)):
            item = processed[i]
            prev_item = current_line[-1]

            avg_h = (item['h'] + prev_item['h']) / 2.0
            if abs(item['cy'] - prev_item['cy']) < avg_h * 0.5:
                current_line.append(item)
            else:
                lines.append(current_line)
                current_line = [item]

        lines.append(current_line)

        # 每行内按 x 从左到右排序，拼接文本
        formatted_text = ""
        for line in lines:
            line.sort(key=lambda item: item['cx'])
            line_text = "".join([item['text'] for item in line])
            formatted_text += line_text + "\n"

        return formatted_text.strip()

    def recognize(self, img):
        """完整 OCR 流程：检测文本框 → 切片 → 识别 → 按行拼接"""
        orig_h, orig_w = img.shape[:2]

        # --- 文本检测（Detection）---
        img_resized = cv2.resize(img, DET_INPUT_SIZE)
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

        img_input = np.expand_dims(img_rgb, axis=0)
        outputs = self.det_rknn.inference(inputs=[img_input])
        pred_map = np.squeeze(outputs[0])  # 分割图 (H, W)

        # 二值化 + 找轮廓
        segmentation_map = (pred_map > SEGMENTATION_THRESHOLD).astype(np.uint8) * 255
        contours, _ = cv2.findContours(segmentation_map, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        # 轮廓 → 四点框，映射回原图尺寸
        boxes = []
        for contour in contours:
            points, sside = self._get_mini_boxes(contour)
            if sside < MIN_BOX_SIZE:
                continue

            points = np.array(points)
            poly = Polygon(points)
            if poly.area <= 0:
                continue

            # pyclipper 扩张多边形，避免框切到文字
            distance = poly.area * POLYGON_EXPAND_RATIO / poly.length
            offset = pyclipper.PyclipperOffset()
            offset.AddPath(points, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
            expanded = offset.Execute(distance)
            if len(expanded) == 0:
                continue

            out_box, _ = self._get_mini_boxes(np.array(expanded[0]))
            out_box = np.array(out_box)
            # 坐标从 640x640 映射回原图
            out_box[:, 0] = np.clip(out_box[:, 0] / DET_INPUT_SIZE[0] * orig_w, 0, orig_w)
            out_box[:, 1] = np.clip(out_box[:, 1] / DET_INPUT_SIZE[1] * orig_h, 0, orig_h)
            boxes.append(out_box)

        # 按 y → x 排序
        boxes = sorted(boxes, key=lambda x: (x[0][1], x[0][0]))

        # --- 文本识别（Recognition）---
        results_with_boxes = []
        for box in boxes:
            crop_img = self._get_rotate_crop_image(img, box)
            if crop_img.shape[0] == 0 or crop_img.shape[1] == 0:
                continue

            crop_padded = self._resize_and_pad(crop_img)
            crop_rgb = cv2.cvtColor(crop_padded, cv2.COLOR_BGR2RGB)
            crop_input = np.expand_dims(crop_rgb, axis=0)

            # 推理 + CTC 贪婪解码（去 blank 和重复）
            rec_out = np.squeeze(self.rec_rknn.inference(inputs=[crop_input])[0])
            argmax_idx = np.argmax(rec_out, axis=1)

            text = ""
            for i in range(len(argmax_idx)):
                curr_idx = argmax_idx[i]
                if curr_idx != self.blank_idx and not (i > 0 and curr_idx == argmax_idx[i-1]):
                    if curr_idx < len(self.keys):
                        text += self.keys[curr_idx]

            if text.strip():
                results_with_boxes.append((text, box))

        # 按行聚类并拼接
        formatted_text = self._group_lines(results_with_boxes)
        raw_list = [item[0] for item in results_with_boxes]

        return raw_list, formatted_text

    def recognize_from_file(self, img_path):
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"无法读取图像文件: {img_path}")
        return self.recognize(img)

    def release(self):
        if hasattr(self, 'det_rknn'):
            self.det_rknn.release()
        if hasattr(self, 'rec_rknn'):
            self.rec_rknn.release()


def enhance_text_image(img):
    """CLAHE 自适应直方图均衡化，增强文本对比度"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast_img = clahe.apply(blurred)
    return cv2.cvtColor(contrast_img, cv2.COLOR_GRAY2BGR)


def capture_from_camera(camera_id=CAMERA_ID, save_path="camera_capture.jpg"):
    """打开摄像头，等待自动对焦后抓拍一帧并保存"""
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


def braille_translation_interface(json_str):
    pass


def main():
    ocr_engine = BookOCR(DET_MODEL_PATH, REC_MODEL_PATH, DICT_PATH)

    try:
        frame = capture_from_camera(CAMERA_ID)
        frame = enhance_text_image(frame)

        start_time = time.time()
        raw_list, formatted_text = ocr_engine.recognize(frame)
        cost_time = time.time() - start_time

        output_data = {
            "status": "success",
            "device": "OrangePi 5 (RK3588)",
            "cost_time_ms": int(cost_time * 1000),
            "block_count": len(raw_list),
            "sentences": raw_list,
            "full_text": formatted_text
        }

        json_result = json.dumps(output_data, ensure_ascii=False, indent=4)
        braille_translation_interface(json_result)

    except Exception as e:
        pass

    finally:
        ocr_engine.release()


if __name__ == '__main__':
    main()
