import logging
import os
import shutil
import time
import tkinter as tk
from concurrent.futures import (
    ProcessPoolExecutor,
    as_completed,
)
from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from tkinter import (
    filedialog,
    messagebox,
)
from typing import List, Tuple

from PIL import Image, ImageOps


# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


@dataclass
class ConversionResult:
    """変換結果を格納するデータクラス"""
    success: bool
    total_original_size: int = 0
    total_webp_size: int = 0
    converted_count: int = 0
    skipped_count: int = 0
    failed_files: List[str] = field(default_factory=list)
    elapsed_time: float = 0.0


def convert_single_image(filepath: Path, output_dir: Path) -> Tuple[bool, int, int, str]:
    """
    単一の画像をWebPに変換する関数。JPEG, PNG 両対応。

    Args:
        filepath (Path): 変換するファイルのパス
        output_dir (Path): WebPファイルを保存するディレクトリのパス

    Returns:
        tuple[bool, int, int, str]: (変換成功/失敗, 元のサイズ, WebPのサイズ, ファイルパス) のタプル
    """
    webp_filepath = output_dir / f"{filepath.stem}{filepath.suffix}.webp"

    try:
        original_size = filepath.stat().st_size
        img = Image.open(filepath)
        img = ImageOps.exif_transpose(img)
        img.save(webp_filepath, "webp")
        webp_size = webp_filepath.stat().st_size
        logger.info(f"変換成功: {filepath} -> {webp_filepath}")
        return True, original_size, webp_size, str(filepath)

    except FileNotFoundError:
        error_msg = f"ファイルが見つかりません: {filepath}"
        logger.error(error_msg)
        return False, 0, 0, str(filepath)
    except Exception as e:
        error_msg = f"変換中にエラーが発生: {filepath}: {e}"
        logger.exception(error_msg)
        return False, 0, 0, str(filepath)


def convert_images_in_directory(input_dir: Path, output_dir: Path, gui: 'ConverterGUI') -> ConversionResult:
    """
    指定ディレクトリ内のJPEG, PNG画像をWebPに変換し、別のディレクトリに出力する関数。
    サブディレクトリも再帰的に処理する。

    Args:
        input_dir (Path): 画像が格納されているディレクトリのパス
        output_dir (Path): WebPファイルを保存するディレクトリのパス
        gui (ConverterGUI): GUIインスタンス

    Returns:
        ConversionResult: 変換結果
    """
    total_original_size = 0
    total_webp_size = 0
    converted_count = 0
    skipped_count = 0
    failed_files: List[str] = []
    start_time = time.time()

    output_dir.mkdir(parents=True, exist_ok=True)

    image_extensions = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG', '*.png', '*.PNG']
    all_files = []

    for root_path, dirs, files in os.walk(input_dir):
        for file in files:
            if any(file.lower().endswith(ext.lower().replace('*', '')) for ext in image_extensions):
                filepath = Path(root_path) / file
                relative_path = filepath.relative_to(input_dir)
                # 出力ディレクトリのパスを計算 (サブディレクトリ名に _webp を追加)
                target_output_dir = output_dir.joinpath(*[part + '_webp' for part in relative_path.parent.parts])

                target_output_dir.mkdir(parents=True, exist_ok=True)
                # WebPファイルのパスを生成
                webp_filepath = target_output_dir / f"{filepath.stem}{filepath.suffix}.webp"

                if not webp_filepath.exists():
                    all_files.append((filepath, target_output_dir))
                else:
                    skipped_count += 1
                    logger.info(f"既存のWebPファイルが存在するためスキップ: {filepath}")

    total_files_count = len(all_files) + skipped_count
    gui.update_converted_count_label(0, total_files_count)

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(convert_single_image, filepath, target_output_dir): (filepath, target_output_dir)
                   for filepath, target_output_dir in all_files}

        for i, future in enumerate(as_completed(futures)):
            filepath, _ = futures[future]
            try:
                success, original_size, webp_size, _ = future.result()
                if success:
                    total_original_size += original_size
                    total_webp_size += webp_size
                    converted_count += 1
                else:
                    failed_files.append(str(filepath))
                    try:
                        shutil.copy2(filepath, target_output_dir)
                        logger.warning(f"変換に失敗したため、{filepath}を{target_output_dir}にコピーしました。")

                    except Exception as e:
                        logger.error(f"{filepath}のコピーに失敗:{e}")
            except Exception as e:
                logger.exception(f"{filepath} の処理中にエラー: {e}")
                failed_files.append(str(filepath))

            gui.update_converted_count_label(converted_count + skipped_count, total_files_count)

    end_time = time.time()
    elapsed_time = end_time - start_time

    return ConversionResult(
        success=len(failed_files) == 0,
        total_original_size=total_original_size,
        total_webp_size=total_webp_size,
        converted_count=converted_count,
        skipped_count=skipped_count,
        elapsed_time=elapsed_time,
        failed_files=failed_files
    )


class ConverterGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("JPEG/PNG to WebP Converter")

        self.directory_label = tk.Label(root, text="変換するディレクトリ (入力):")
        self.directory_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.directory_entry = tk.Entry(root, width=50)
        self.directory_entry.grid(row=0, column=1, padx=5, pady=5)
        self.browse_button = tk.Button(root, text="参照...", command=self.browse_directory)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)

        self.convert_button = tk.Button(root, text="変換開始", command=self.convert_images_gui)
        self.convert_button.grid(row=1, column=1, pady=10)

        self.converted_count_label = tk.Label(root, text="変換済みファイル数: 0")
        self.converted_count_label.grid(row=2, column=1, pady=5)

    def browse_directory(self):
        """ファイルダイアログを開き、ディレクトリを選択"""
        directory = filedialog.askdirectory()
        if directory:
            self.directory_entry.delete(0, tk.END)
            self.directory_entry.insert(0, directory)

    def convert_images_gui(self):
        """GUIからの変換処理"""
        input_dir_str = self.directory_entry.get()
        if not input_dir_str:
            messagebox.showwarning("警告", "ディレクトリを選択してください。")
            return

        input_dir = Path(input_dir_str)
        if not input_dir.is_dir():
            messagebox.showerror("エラー", "指定されたパスはディレクトリではありません。")
            return

        output_dir = input_dir.parent / (input_dir.name + "_webp")

        logger.info(f"変換開始: 入力ディレクトリ = {input_dir}, 出力ディレクトリ = {output_dir}")

        result = convert_images_in_directory(input_dir, output_dir, self)
        self.show_result_message(result, output_dir)
        self.update_converted_count_label(result.converted_count + result.skipped_count, result.converted_count + result.skipped_count)


    def show_result_message(self, result: ConversionResult, output_dir: Path):
        """変換結果をメッセージボックスで表示"""
        if result.success:
            reduction = result.total_original_size - result.total_webp_size
            reduction_percent = (reduction / result.total_original_size) * 100 if result.total_original_size > 0 else 0
            original_size_mb = result.total_original_size / (1024 * 1024)
            webp_size_mb = result.total_webp_size / (1024 * 1024)
            reduction_mb = reduction / (1024 * 1024)

            message = (
                f"変換が完了しました。\n\n"
                f"変換したファイル数: {result.converted_count} 枚\n"
                f"スキップしたファイル数: {result.skipped_count} 枚\n"
                f"元の合計サイズ: {original_size_mb:.2f} MB\n"
                f"WebPの合計サイズ: {webp_size_mb:.2f} MB\n"
                f"削減されたサイズ: {reduction_mb:.2f} MB ({reduction_percent:.2f}% 削減)\n"
                f"処理時間: {result.elapsed_time:.2f} 秒\n"
                f"出力ディレクトリ: {output_dir}"
            )
            if result.failed_files:
                message += "\n\n変換に失敗したファイル (出力ディレクトリにコピーされました):\n" + "\n".join(result.failed_files)
            messagebox.showinfo("完了", message)
            logger.info(message)
        else:
            message = "変換中にエラーが発生しました。ログを確認してください。"
            messagebox.showerror("エラー", message)
            logger.error(message)
        logger.info("変換終了")

    def update_converted_count_label(self, converted_count: int, total_files: int):
        self.converted_count_label.config(text=f"変換済みファイル数: {converted_count}/{total_files}")
        self.root.update()


if __name__ == "__main__":
    root = tk.Tk()
    gui = ConverterGUI(root)
    root.mainloop()
