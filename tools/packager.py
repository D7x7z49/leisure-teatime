from pathlib import Path
import tarfile
import zlib
import base64

def collect_files(dirs, extra_files=None):
    """收集指定目录下的所有文件，并添加自身脚本"""
    files_to_embed = []
    # 打包目录下的文件
    for dir_path in dirs:
        for filepath in Path(dir_path).rglob("*"):
            if filepath.is_file():
                files_to_embed.append(str(filepath))
    # 添加自身脚本
    self_path = str(Path(__file__).resolve())
    if self_path not in files_to_embed:
        files_to_embed.append(self_path)
    # 添加额外文件
    if extra_files:
        for extra_file in extra_files:
            extra_path = str(Path(extra_file).resolve())
            if extra_path not in files_to_embed and Path(extra_file).exists():
                files_to_embed.append(extra_path)
    return files_to_embed

def generate_deploy(output_dir="dist"):
    # 指定需要打包的目录和额外文件
    dirs_to_pack = ["core", "tools"]
    extra_files = ["pyproject.toml", ".editorconfig"]
    files_to_embed = collect_files(dirs_to_pack, extra_files)

    # 打包并压缩
    with tarfile.open("temp.tar", "w") as tar:
        for filepath in files_to_embed:
            tar.add(filepath)
    with open("temp.tar", "rb") as f:
        compressed = zlib.compress(f.read(), level=9)
        b64_encoded = base64.b64encode(compressed).decode("ascii")
    Path("temp.tar").unlink()  # 删除临时文件

    # 确保输出目录存在
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "deploy.py"

    # 生成 deploy.py
    with output_path.open("w", encoding="utf-8") as f:
        f.write(f'''\
import zlib
import base64
import tarfile
from io import BytesIO

DATA = "{b64_encoded}"

def deploy():
    tar_data = zlib.decompress(base64.b64decode(DATA))
    with tarfile.open(fileobj=BytesIO(tar_data)) as tar:
        tar.extractall()

if __name__ == "__main__":
    deploy()
''')
    print(f"Generated {output_path} with {len(files_to_embed)} files packed.")
    print(f"Compressed size: {len(b64_encoded) / 1024:.2f} KB")

if __name__ == "__main__":
    generate_deploy()
