import torch
from diffusers import StableDiffusionPipeline

# 加载模型
local_model_path_v1 = (
    "/root/Workspace/models--runwayml--stable-diffusion-v1-5/snapshots/1d0c4ebf6ff58a5caecab40fa1406526bca4b5b9"
)
pipe = StableDiffusionPipeline.from_pretrained(local_model_path_v1)
pipe.to("cuda")

# 写入每一层的参数到文本文件
def write_model_parameters_to_file(model, filename):
    with open(filename, 'w') as f:
        for name, param in model.named_parameters():
            if param.requires_grad:
                f.write(f"Layer: {name}, Size: {param.size()}\n")

# 指定输出文件名
output_file = 'model_parameters.txt'

# 调用函数写入参数
write_model_parameters_to_file(pipe.unet, output_file)

print(f"Model parameters written to {output_file}")