from flask import Flask, request, render_template_string

app = Flask(__name__)


@app.route('/cn-painting/view')
def view_image():
    image_name = request.args.get("image", "default.png")  # 获取 URL 参数
    image_url = f"http://fduimc.sv6.tunnelfrp.com/cn-painting/api/images/{image_name}"

    html = f"""
    <html>
    <body style="margin:0; text-align:center;">
        <img src="{image_url}" style="max-width:100%;">
    </body>
    </html>
    """
    return render_template_string(html)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
