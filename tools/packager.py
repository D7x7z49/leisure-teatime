from io import BytesIO
from pathlib import Path
import tarfile
import zlib
import base64
import tempfile
import sys
from datetime import datetime
from typing import List, Optional

# 进度条显示 (兼容无tqdm环境)
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

class PackagerError(Exception):
    """打包工具自定义异常基类"""
    pass

def collect_files(dirs: List[str], extra_files: Optional[List[str]] = None) -> List[Path]:
    """收集需要打包的文件路径"""
    file_paths = []

    # 处理目录
    for dir_path in dirs:
        dir_path = Path(dir_path)
        if not dir_path.exists():
            raise PackagerError(f"Directory not found: {dir_path}")
        if not dir_path.is_dir():
            raise PackagerError(f"Not a directory: {dir_path}")

        for filepath in tqdm(list(dir_path.rglob("*")), desc=f"Scanning {dir_path}"):
            if filepath.is_file() and not filepath.name.startswith("."):
                file_paths.append(filepath.resolve())

    # 添加自身脚本
    self_path = Path(__file__).resolve()
    if self_path not in file_paths:
        file_paths.append(self_path)

    # 处理额外文件
    if extra_files:
        for ef in extra_files:
            ef_path = Path(ef).resolve()
            if ef_path.exists() and ef_path not in file_paths:
                file_paths.append(ef_path)
            else:
                print(f"Warning: Extra file not found - {ef}", file=sys.stderr)

    return sorted(set(file_paths), key=lambda x: str(x))

def create_tar_archive(files: List[Path]) -> bytes:
    """创建内存中的tar归档"""
    tar_buffer = BytesIO()

    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:  # 使用gzip压缩
        for filepath in tqdm(files, desc="Packing files"):
            try:
                arcname = str(filepath.relative_to(Path.cwd()))
                tar.add(filepath, arcname=arcname)
            except Exception as e:
                raise PackagerError(f"Failed to add {filepath}: {str(e)}")

    tar_buffer.seek(0)
    return tar_buffer.getvalue()

def generate_deploy_script(compressed_data: bytes, output_dir: Path) -> Path:
    """生成部署脚本"""
    script_template = f'''\
#!/usr/bin/env python3
"""
Auto-generated deployment script - Created at {datetime.now().isoformat()}
DO NOT MODIFY THIS FILE DIRECTLY
"""

import zlib
import base64
import tarfile
from io import BytesIO
from pathlib import Path
import sys

# Base64 encoded compressed data (size: {len(compressed_data):,} bytes)
DATA = (
    "{base64.b64encode(compressed_data).decode('ascii')}"
)

def deploy(output_dir: Path = Path.cwd(), overwrite: bool = False):
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Deploying to: {{output_dir}}")
    print(f"Total payload size: {len(compressed_data) / 1024:.1f} KB")

    try:
        decoded = base64.b64decode(DATA)
        decompressed = zlib.decompress(decoded)

        with tarfile.open(fileobj=BytesIO(decompressed)) as tar:
            members = tar.getmembers()
            print(f"Extracting {{len(members)}} files...")

            for member in tar:
                target = output_dir / member.name
                if target.exists() and not overwrite:
                    print(f"Skipping existing: {{target}}")
                    continue
                tar.extract(member, path=output_dir)
                print(f"Extracted: {{target}}")

        print("Deployment completed successfully")

    except Exception as e:
        print(f"Deployment failed: {{str(e)}}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=Path, default=Path.cwd())
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    deploy(args.output, args.force)
'''

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "deploy.py"

    with output_path.open("w", encoding="utf-8") as f:
        # 优化数据格式：每行80字符
        encoded = base64.b64encode(compressed_data).decode("ascii")
        data_lines = [f'    "{encoded[i:i+80]}"' for i in range(0, len(encoded), 80)]

        f.write(script_template.replace(
            '    "{base64.b64encode(compressed_data).decode(\'ascii\')}"',
            "\n".join(data_lines)
        ))

    output_path.chmod(0o755)  # 添加可执行权限
    return output_path

def generate_deploy(output_dir: str = "dist", compression_level: int = 9):
    """主打包函数"""
    start_time = datetime.now()

    try:
        # 收集文件
        dirs_to_pack = ["core", "tools"]
        extra_files = ["pyproject.toml", ".editorconfig"]
        files = collect_files(dirs_to_pack, extra_files)

        print(f"Found {len(files)} files to package")
        print(f"Total size before compression: {sum(f.stat().st_size for f in files) / 1024**2:.2f} MB")

        # 创建压缩包
        raw_data = create_tar_archive(files)
        compressed = zlib.compress(raw_data, level=compression_level)

        # 生成部署脚本
        output_path = generate_deploy_script(compressed, Path(output_dir))

        # 输出统计信息
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\nSuccessfully generated {output_path}")
        print(f"Compression ratio: {len(compressed)/len(raw_data)*100:.1f}%")
        print(f"Total time: {duration:.2f} seconds")

    except PackagerError as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    generate_deploy()
