import os
import cv2
import numpy as np

blur_size = 5               # Cannyのぼかしサイズ（奇数）
canny_th = [30, 70]         # Cannyの閾値
ratio_th = 0.35             # 面積/矩形面積の閾値
overlap_th = 0.5            # 重複除去の閾値
blur_grab_size = 7          # GrabCutのぼかしサイズ（奇数）
mask_size = [0, 0, 10, 10]  # マスク範囲（左上・右下座標）
th_size = [10, 40000]       # パッチの最小・最大面積

# 既存の関数はそのまま使用
def binary_canny(path, th1, th2):
    img = cv2.imread(path)
    preprocessed = cv2.cvtColor(cv2.GaussianBlur(img, (blur_size, blur_size), 0), cv2.COLOR_BGR2GRAY)
    kernel = np.ones((4, 4), np.uint8)
    image = cv2.Canny(preprocessed, th1, th2)
    image = cv2.dilate(image, kernel, iterations=1)
    return image

def resize_image(img, size):
    img_size = img.shape[:2]
    if img_size[0] > size[1] or img_size[1] > size[0]:
        return None
    row = (size[1] - img_size[0]) // 2
    col = (size[0] - img_size[1]) // 2
    resized = np.zeros(list(size) + [img.shape[2]], dtype=np.uint8)
    resized[row:(row + img.shape[0]), col:(col + img.shape[1])] = img
    return resized

def padding_position(x, y, w, h, p):
    return x - p, y - p, w + p * 2, h + p * 2

def non_max_suppression(position, areas, overlapThresh):
    if len(position) == 0:
        return [], []
    pick = []
    x1 = position[:, 0]
    y1 = position[:, 1]
    w = position[:, 2]
    h = position[:, 3]
    x2 = (np.array(x1) + np.array(w)).tolist()
    y2 = (np.array(y1) + np.array(h)).tolist()
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(areas)
    while len(idxs) > 0:
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)
        suppress = [last]
        for pos in range(0, last):
            j = idxs[pos]
            xx1 = max(x1[i], x1[j])
            yy1 = max(y1[i], y1[j])
            xx2 = min(x2[i], x2[j])
            yy2 = min(y2[i], y2[j])
            w = max(0, xx2 - xx1 + 1)
            h = max(0, yy2 - yy1 + 1)
            overlap = float(w * h) / area[j]
            if overlap > overlapThresh:
                suppress.append(pos)
        idxs = np.delete(idxs, suppress)
    return position[pick], np.array(areas)[pick].tolist()

def detect_contour(path, min_size, max_size):
    contoured = cv2.imread(path)
    forcrop = cv2.imread(path)
    sun = binary_canny(path, canny_th[0], canny_th[1])
    sun = cv2.bitwise_not(sun)
    contours, hierarchy = cv2.findContours(sun, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    crops = []; areas = []; position = []; sunspots_contours = []
    for c in contours:
        area = cv2.contourArea(c)
        x, y, w, h = cv2.boundingRect(c)
        if area < min_size or max_size < area or w > 200 or h > 200 or area / (w * h) < ratio_th:
            continue
        sunspots_contours.append(c)
        areas.append(area)
        position.append([x, y, w, h])
    position = np.array(position)
    NMS_position, NMS_areas = non_max_suppression(position, areas, overlap_th)
    for c, (x, y, w, h), area in zip(sunspots_contours, NMS_position, NMS_areas):
        x, y, w, h = padding_position(x, y, w, h, 5)
        cropped = forcrop[y:(y + h), x:(x + w)]
        cropped = resize_image(cropped, (200, 200))
        crops.append(cropped)
        cv2.drawContours(contoured, [c], -1, (0, 0, 255), 3)
        cv2.rectangle(contoured, (x, y), (x + w, y + h), (0, 255, 0), 3)
    return contoured, crops, NMS_areas

def grabcut_img(path):
    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1, minDist=20,
                               param1=50, param2=30, minRadius=50, maxRadius=500)
    if circles is not None:
        x, y, r = circles[0][0]
        rect = (int(x - r), int(y - r), int(2 * r), int(2 * r))
    else:
        h, w = img.shape[:2]
        rect = (w // 100, h // 10, w - w // 50, h - h // 5)
    blur_img = cv2.GaussianBlur(img, (blur_grab_size, blur_grab_size), 0)
    mask = np.zeros(img.shape[:2], np.uint8)
    bgModel = np.zeros((1, 65), np.float64)
    fgModel = np.zeros((1, 65), np.float64)
    cv2.grabCut(blur_img, mask, rect, bgModel, fgModel, 5, cv2.GC_INIT_WITH_RECT)
    if circles is not None:
        x, y, r = circles[0][0]
        cv2.circle(mask, (int(x), int(y)), int(r * 1.01), 1, thickness=-1)
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype(np.uint8)
    out = img * mask2[:, :, np.newaxis]
    return out

# 新しいメイン関数
def process_latest_image(image_path):
    """
    最新画像のパスを受け取り、contour_pathと面積の総和を返す関数
    Args:
        image_path (str): 最新画像のフルパス
    Returns:
        tuple: (contour_path, total_area)
            - contour_path (str): 輪郭検出済み画像の保存パス
            - total_area (float): 検出された領域の総面積（ピクセル）
    """
    # 出力ディレクトリ設定
    current_dir = os.path.dirname(image_path)
    contour_path_dir = os.path.join(current_dir, "contoured_images")
    mask_path_dir = os.path.join(current_dir, "masked_images")
    os.makedirs(contour_path_dir, exist_ok=True)
    os.makedirs(mask_path_dir, exist_ok=True)

    # 画像名抽出
    img_name = os.path.basename(image_path)
    
    # GrabCutで前景抽出
    masked = grabcut_img(image_path)
    masked_path = os.path.join(mask_path_dir, img_name)
    cv2.imwrite(masked_path, masked)

    # 輪郭検出と面積計算
    contoured, _, areas = detect_contour(masked_path, th_size[0], th_size[1])
    contour_path = os.path.join(contour_path_dir, img_name)
    cv2.imwrite(contour_path, contoured)

    # 面積の総和
    total_area = sum(areas) if areas else 0

    return contour_path, total_area

if __name__ == "__main__":
    latest_image_path = r"C:\Users\mizum\Downloads\test4\raw_images\Sunspot_20241110_163424.png"
    contour_path, total_area = process_latest_image(latest_image_path)
    print(f"Contour Path: {contour_path}")
    print(f"Total Area: {total_area} pixels")