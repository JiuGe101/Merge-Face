import json
import base64
import requests
import cv2
import os
import time
import shutil
import tqdm
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter

# from urllib3 import Retry

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
logging.basicConfig(filename='my.log', level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT)

s = requests.session()
# s.config['keep_alive'] = False
max_retries = 3  # 重试3次
s.mount('http://', HTTPAdapter(max_retries=max_retries))
s.mount('https://', HTTPAdapter(max_retries=max_retries))


# 算法
# 构建模型
# 训练模型  ---> 需要数据集

# 找到人脸数据


def find_face(imgpath):
    http_url = 'https://api-cn.faceplusplus.com/facepp/v3/detect'
    # 参数
    data = {
        'api_key': 'WgHeBkMbaU0mmU9Hq-ucR7Rei0vKngnh',
        'api_secret': '1y3U2gxCm77LLUjiZ-RumGw0wqMJZQ4k',
        'img_url': imgpath,
        'return_landmark': 1
    }
    # 文件
    files = {'image_file': open(imgpath, 'rb')}  # rb表示二进制的读取
    # 携带数据的请求我们通常使用post请求
    resp = requests.post(http_url, data=data, files=files, timeout=60)
    # while resp.status_code == 403:
    #     # time.sleep(1)
    #     resp = requests.post(http_url, data=data, files=files, timeout=20)
    # print(resp.status_code)
    # req_con是个json格式的数据
    req_con = resp.text
    # print(req_con)
    # 类型转换
    this_dict = json.loads(req_con)
    faces = this_dict['faces']
    # print(faces)
    if not faces:
        return False
    else:
        list0 = faces[0]
        # 得到人脸框的数据
        rectangle = list0['face_rectangle']
        # print(rectangle)
        return rectangle


# 拟合，拼接人脸
def merge_face(img_url1, img_url2, img_url3, number):
    """
    :param img_url1: 第一张图像
    :param img_url2: 第二张图像
    :param img_url3: 合并后的效果图
    :param number:相似度
    :return:
    """
    # 分别获取第一张图片和第二张图片的人脸数据
    ff1 = find_face(img_url1)
    ff2 = find_face(img_url2)
    if ff1 is False:
        shutil.copyfile(img_url1, img_url3)
        return False
    # 因为参数需要是字符串类型，而ff1和ff2都是字典，我们需要格式转换
    rectangle1 = str(str(ff1['top']) + "," + str(ff1['left']) + "," + str(ff1['width']) + "," + str(ff1['height']))
    rectangle2 = str(str(ff2['top']) + "," + str(ff2['left']) + "," + str(ff2['width']) + "," + str(ff2['height']))
    # print(rectangle1)
    # print(rectangle2)
    with open(img_url1, 'rb') as f1:
        f1_64 = base64.b64encode(f1.read())  # 编码
    with open(img_url2, 'rb') as f2:
        f2_64 = base64.b64encode(f2.read())  # 编码
    # 合并，我们需要使用另一个接口
    url_add = 'https://api-cn.faceplusplus.com/imagepp/v1/mergeface'

    data = {
        'api_key': 'WgHeBkMbaU0mmU9Hq-ucR7Rei0vKngnh',
        'api_secret': '1y3U2gxCm77LLUjiZ-RumGw0wqMJZQ4k',
        'template_base64': f1_64, 'template_rectangle': rectangle1,
        'merge_base64': f2_64, 'merge_rectangle': rectangle2,
        'merge_rate': number,
        # 'feature_rate': 0
    }
    resp = requests.post(url_add, data=data, timeout=60)
    # while resp.status_code != 200:
    #     # print(resp.status_code)
    #     resp = requests.post(url_add, data=data, timeout=20)
    # print(resp.status_code,type(resp.status_code))
    # print(resp.status_code)
    req_con = resp.text
    # req_dict = json.loads(req_con)
    # 把json转化为字典，作用和上面那个一样，殊途同归
    req_dict = json.JSONDecoder().decode(req_con)
    # print(req_dict)
    result = req_dict['result']
    imgdata = base64.b64decode(result)
    # return img_url3
    with open(img_url3, 'wb') as file:  # 用wb写入这张图像
        file.write(imgdata)


def vedio_slice(img_path, video_path):
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened() != True:
        exit(-1)
    num = 0
    while True:
        slice_path = original_video_slice_path + r'\{:0>6d}.jpg'.format(num)
        ret, img = cap.read()
        if ret != True:
            print('切分视频完成')
            break
        if os.path.exists(slice_path):
            print('file {:0>6d}.jpg is exist'.format(num))
            num += 1
            continue
        else:
            cv2.imwrite(original_video_slice_path + r'\{:0>6d}.jpg'.format(num), img)
            # merge_face(temp_video_path, img_path, r'img\merge_jpg\{:0>4d}.jpg'.format(num), 100)
            num += 1
            print(num)


def video_merge_face():
    all_task = []
    files = os.listdir(original_video_slice_path)
    with ThreadPoolExecutor(max_workers=1) as pool:
        for file in files:
            logging.info(file)
            video_merge_result_file = f'{video_merge_result_path}\\{file}'
            if os.path.exists(video_merge_result_file):
                # print(f'{file} is exist!!!')
                continue
            else:
                all_task.append(
                    pool.submit(merge_face, f'{original_video_slice_path}\\{file}', img1, video_merge_result_file, 99))


def img2mp4():
    size = (720, 1280)  # 这个是图片的尺寸，一定要和要用的图片size一致
    # 完成写入对象的创建，第一个参数是合成之后的视频的名称，第二个参数是可以使用的编码器，第三个参数是帧率即每秒钟展示多少张图片，第四个参数是图片大小信息
    fourcc = cv2.VideoWriter.fourcc('m', 'p', '4', 'v')
    videowrite = cv2.VideoWriter('test.mp4', fourcc, 30, size)  # 20是帧数，size是图片尺寸
    img_array = []
    files = os.listdir(video_merge_result_path)
    for file in files:
        img = cv2.imread(f'{video_merge_result_path}\\{file}')
        if img is None:
            print(file + " is error!")
            continue
        # img_array.append(img)
        videowrite.write(img)
    # for i in range(600):  # 把读取的图片文件写进去
    #     videowrite.write(img_array[i])
    videowrite.release()
    print('end!')


if __name__ == "__main__":
    img1 = r"img\4.jpg"
    img3 = r"img\result.jpg"
    video_path = r'E:\video\肌肉金轮.mp4'
    original_video_slice_path = r'img\original_vedio_slice'
    video_merge_result_path = r'img\merge_jpg'
    vedio_slice(img1, video_path)
    print('正在换脸')
    video_merge_face()
    print('正在合成视频')
    img2mp4()
    # merge_face(img1, img2, img3, 100)
