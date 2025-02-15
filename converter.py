# 必要なモジュールをインポート
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

from PIL import Image, ImageOps

# グローバルロガーの設定
logger = logging.getLogger("converter_log")
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
    failed_files: list[str] = field(default_factory=list)
    elapsed_time: float = 0.0


def convert_single_image(filepath: Path, output_dir: Path) -> tuple[bool, int, int, str]:
    """
    単一の画像をWebPに変換する関数。JPEG, PNG 両対応。

    Args:
        filepath (Path): 変換するファイルのパス
        output_dir (Path): WebPファイルを保存するディレクトリのパス

    Returns:
        tuple[bool, int, int, str]: (変換成功/失敗, 元のサイズ, WebPのサイズ, ファイルパス) のタプル
    """
    webp_filepath = output_dir / filepath.with_suffix(".webp").name

    try:
        original_size = filepath.stat().st_size
        img = Image.open(filepath)
        img = ImageOps.exif_transpose(img)  # EXIF情報を正しく扱う
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


def convert_images_in_directory(input_dir: Path, output_dir: Path) -> ConversionResult:
    """
    指定ディレクトリ内のJPEG, PNG画像をWebPに変換し、別のディレクトリに出力する関数。
    サブディレクトリも再帰的に処理する。

    Args:
        input_dir (Path): 画像が格納されているディレクトリのパス
        output_dir (Path): WebPファイルを保存するディレクトリのパス

    Returns:
        ConversionResult: 変換結果
    """
    global g_root  # g_root をグローバル変数として宣言
    total_original_size = 0
    total_webp_size = 0
    converted_count = 0
    skipped_count = 0
    failed_files = []
    start_time = time.time()

    output_dir.mkdir(parents=True, exist_ok=True)

    image_extensions = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG', '*.png', '*.PNG']  # PNGも追加
    all_files = []
    # input_dir 以下のすべてのサブディレクトリを再帰的に探索
    for g_root_path, dirs, files in os.walk(input_dir):
        for file in files:
            if any(file.lower().endswith(ext.lower().replace('*', '')) for ext in image_extensions):
                filepath = Path(g_root_path) / file
                relative_path = filepath.relative_to(input_dir)
                # 出力ディレクトリのパスを計算
                target_output_dir = output_dir.joinpath(*[part + '_webp' for part in relative_path.parent.parts])

                target_output_dir.mkdir(parents=True, exist_ok=True)

                if not (target_output_dir / filepath.with_suffix(".webp").name).exists():
                    all_files.append((filepath, target_output_dir))
                else:
                    skipped_count += 1

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(convert_single_image, filepath, target_output_dir): (filepath, target_output_dir)
                   for filepath, target_output_dir in all_files}

        for future in as_completed(futures):
            filepath, _ = futures[future]
            try:
                success, original_size, webp_size, _ = future.result()
                if success:
                    total_original_size += original_size
                    total_webp_size += webp_size
                    converted_count += 1
                else:
                    failed_files.append(str(filepath))
                    # 変換に失敗した場合は元のファイルをコピー
                    try:
                        # target_output_dirを正しく計算
                        relative_path = filepath.relative_to(input_dir)
                        target_output_dir = output_dir.joinpath(*[part + '_webp' for part in relative_path.parent.parts()])
                        shutil.copy2(filepath, target_output_dir)
                        logger.warning(f"変換に失敗したため、{filepath}を{target_output_dir}にコピーしました。")

                    except Exception as e:
                        logger.error(f"{filepath}のコピーに失敗:{e}")

            except Exception as e:
                logger.exception(f"{filepath} の処理中にエラー: {e}")
                failed_files.append(str(filepath))

            g_converted_count_label.config(text=f"変換済みファイル数: {converted_count + skipped_count}/{len(all_files) + skipped_count}")
            g_root.update()  # ここでグローバル変数の g_root を使用

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



def browse_directory():
    """ファイルダイアログを開き、ディレクトリを選択"""
    directory = filedialog.askdirectory()
    if directory:
        g_directory_entry.delete(0, tk.END)
        g_directory_entry.insert(0, directory)


def convert_images_gui():
    """GUIからの変換処理"""
    input_dir_str = g_directory_entry.get()
    if not input_dir_str:
        messagebox.showwarning("警告", "ディレクトリを選択してください。")
        return

    input_dir = Path(input_dir_str)
    if not input_dir.is_dir():
        messagebox.showerror("エラー", "指定されたパスはディレクトリではありません。")
        return

    output_dir = input_dir.parent / (input_dir.name + "_webp")

    logger.info(f"変換開始: 入力ディレクトリ = {input_dir}, 出力ディレクトリ = {output_dir}")

    result = convert_images_in_directory(input_dir, output_dir)
    show_result_message(result, output_dir)


def show_result_message(result: ConversionResult, output_dir: Path):
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


def create_gui():
    """GUIを作成"""
    global g_root, g_directory_entry, g_converted_count_label

    g_root = tk.Tk()
    g_root.title("JPEG/PNG to WebP Converter")  # タイトルを修正

    directory_label = tk.Label(g_root, text="変換するディレクトリ (入力):")
    directory_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
    g_directory_entry = tk.Entry(g_root, width=50)
    g_directory_entry.grid(row=0, column=1, padx=5, pady=5)
    browse_button = tk.Button(g_root, text="参照...", command=browse_directory)
    browse_button.grid(row=0, column=2, padx=5, pady=5)

    convert_button = tk.Button(g_root, text="変換開始", command=convert_images_gui)
    convert_button.grid(row=1, column=1, pady=10)

    g_converted_count_label = tk.Label(g_root, text="変換済みファイル数: 0")
    g_converted_count_label.grid(row=2, column=1, pady=5)

    return g_root


if __name__ == "__main__":
    g_root = create_gui()
    g_root.mainloop()
