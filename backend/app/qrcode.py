import qrcode
from PIL import Image


def merge_images_vertically(image1, image_path2):
    """
    将第一张图片和路径指定的第二张图片垂直拼接在一起，并返回合并后的图片。

    :param image1: 第一张图片的 Image 对象
    :param image_path2: 第二张图片的路径
    :return: 合并后的 Image 对象
    """

    # 打开第二张图片
    image2 = Image.open(image_path2)

    # 调整第二张图的宽度以匹配第一张图的宽度
    image2 = image2.resize((image1.width, int(image2.height * (image1.width / image2.width))))

    # 创建一个新的图像，宽度与第一张图一致，高度为两张图高度之和
    new_image = Image.new('RGB', (image1.width, image1.height + image2.height))

    # 把第一张图粘贴到新图的顶端
    new_image.paste(image1, (0, 0))
    # 把第二张图粘贴到新图的底端
    new_image.paste(image2, (0, image1.height))

    return new_image


#新二维码生成方式
def generate_qr_code_new(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((144, 144))
    return img

def generate_qr_code(data, file_name):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((144, 144))
    img.save(file_name)


def add_qr_code_to_image(image_path, qr_code_data, output_path):
    img = Image.open(image_path).convert("RGBA")
    qr_code_file = "temp_qr_code.png"
    generate_qr_code(qr_code_data, qr_code_file)
    qr_code_img = Image.open(qr_code_file).convert("RGBA")

    # 创建一个透明的图像作为占位符
    transparent_placeholder = Image.new("RGBA", (624, 144), (0, 0, 0, 0))

    # 计算二维码应该放置的位置
    qr_position = (img.width - qr_code_img.width, img.height)

    # 创建一个空白的图像，用于合并图片和二维码
    result_img = Image.new("RGBA", (img.width, img.height + qr_code_img.height))

    # 将原始图片粘贴到结果图像的顶部
    result_img.paste(img, (0, 0))

    # 将透明占位符粘贴到结果图像的指定位置
    result_img.paste(transparent_placeholder,
                     (img.width - qr_code_img.width - transparent_placeholder.width, img.height))

    # 将二维码粘贴到结果图像的底部
    result_img.paste(qr_code_img, qr_position, qr_code_img)

    # 保存结果图像
    result_img.save(output_path)

    # 关闭所有图像
    qr_code_img.close()
    img.close()
    result_img.close()
