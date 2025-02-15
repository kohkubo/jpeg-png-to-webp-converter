# JPEG/PNG to WebP Converter

This is a Python script that converts JPEG and PNG images in a specified directory to WebP format. It uses multiprocessing to speed up the conversion process and provides a simple GUI for ease of use.

## Features

-   **Converts JPEG and PNG images to WebP**: Supports common image formats.
-   **Recursive directory processing**:  Processes all images within the specified directory and its subdirectories.  Each subdirectory will have a corresponding output directory with the suffix "_webp".
-   **Multiprocessing**: Uses multiple processes to convert images concurrently, significantly reducing conversion time.
-   **EXIF data handling**:  Preserves EXIF data during conversion using `ImageOps.exif_transpose()`.
-   **Error handling**:  Handles file not found and other potential errors gracefully. Logs errors and attempts to copy unconverted files to the output directory.
-   **GUI**: Provides a simple graphical user interface for selecting the input directory and starting the conversion.
-   **Progress display**: Shows the number of converted files in real-time.
-   **Skip existing WebP files**: Avoids redundant conversions by checking for existing WebP files in the output directory.
-   **Conversion result reporting**: Displays a detailed summary after conversion, including the number of converted files, skipped files, total original size, total WebP size, size reduction, processing time, and output directory.  Also lists any files that failed to convert.
-   **Logging**: Logs detailed information, warnings, and errors to the console.

## Requirements

-   Python 3.7+
-   Pillow (PIL) library

You can install Pillow using pip:

```bash
pip install Pillow
```

## How to Use

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/kohkubo/jpeg-png-to-webp-converter.git
    cd jpeg-png-to-webp-converter
    ```

2.  **Run the script:**

    ```bash
    python converter.py
    ```

3.  **Using the GUI:**

    -   Click the "参照..." button to select the directory containing the JPEG/PNG images you want to convert.
    -   Click the "変換開始" button to start the conversion process.
    -   The output WebP files will be saved in a new directory with the same name as the input directory, appended with "_webp".  Subdirectories will also have corresponding "_webp" directories.
    -   A message box will display the conversion results after the process is complete.

## Code Overview

-   **`ConversionResult` dataclass**: Stores the conversion results (success, sizes, counts, failed files, time).
-   **`convert_single_image(filepath, output_dir)`**: Converts a single image file to WebP.
-   **`convert_images_in_directory(input_dir, output_dir)`**:  Recursively converts all images in a directory to WebP, using multiprocessing.  Handles subdirectory creation in the output.
-   **`browse_directory()`**: Opens a directory selection dialog.
-   **`convert_images_gui()`**:  Handles the conversion process initiated from the GUI.
-   **`show_result_message(result, output_dir)`**: Displays the conversion results in a message box.
-   **`create_gui()`**: Creates the graphical user interface.
-   **`if __name__ == "__main__":` block**:  The main entry point of the script.  Creates the GUI and starts the main event loop.
- **Logging:** The script uses the `logging` module to provide detailed information, warnings, and error messages to the console. This helps in understanding the progress and troubleshooting any issues.

## Notes

-   The script creates an output directory with the same name as the input directory, appended with "_webp".
-   If a WebP file with the same name already exists in the output directory, the conversion of that image will be skipped.
- If a file cannot be converted, the program will log the error and then will attempt to copy the original image to the output directory, so no files are lost.
- The GUI is built using the `tkinter` library, which is included with most standard Python installations.
- The script is designed to be robust and handle various error conditions.
