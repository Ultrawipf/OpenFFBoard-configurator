# SUMMARY

1. `pylupdate6 -ts ./translations/zh_CN.ts .` : update py&ui string into ts file.
2. there is 2 ways to translation ts file:

   a. with Qt Linguist(recommend for now if you are familiar with github and installed pyqt stuff): run `linguist` and open the ts file, you will get a nice UI for translation and preview.

   or 

   b. convert into ods for google sheets, run`./translations/tool_ts_to_ods.py zh_CN.ts`(you need to provide the filename as a command line argument) for later translation in google sheets. After translating in google sheets, run `./translations/tool_ods_to_ts.py zh_CN.ods`(you need to provide the filename as a command line argument) to convert back. You will need pyexcel_ods installed (run `pip install pyexcel_ods`)

3. After ts file is translated, run `lrelease ./translations/zh_CN.ts` : ts to qm
4. python will load qm file automatically at startup or manually with `QTranslator.load()`.

---

## PyQt6 Internationalization

In PyQt6, internationalization (i18n) typically involves translating the text of your application into different languages so that users can choose their preferred language to use the application. Here are the general steps to correctly internationalize a PyQt6 application:

1. Prepare Translation Files:
   - First, you need to install Qt's internationalization tool (Linguist), which you can find on Qt's official website.
   - Use Linguist to create a translation file (.ts file). This file will contain all the text in your application that needs to be translated.

2. Use Translation Files in the Application:
   - In your PyQt6 application, use `QtCore.QLocale` to determine the user's preferred language.
   - Use `QtCore.QTranslator` to load the appropriate translation file based on the user's preferred language setting.

3. Mark Text for Translation in the User Interface:
   - In your PyQt6 interface files (.ui files), use the `tr()` function to wrap the text that needs to be translated.

4. Extract Text and Generate Translations:
   - Use the `pylupdate6` tool to extract text marked with `tr()` from your PyQt6 project and update it in the translation file (.ts).
   - Use the Linguist tool to open the translation file and provide translations for each text item.

5. Compile Translation Files:
   - Use the `lrelease` tool to compile the translation file (.ts) into binary files (.qm).

6. Load Translation Files in the Application:
   - In your application, use `QtCore.QTranslator` to load the compiled translation file (.qm).

7. Allow Language Switching in the Application:
   - Provide a user interface option for users to choose the language of the application.
   - When the user selects a different language, reload the corresponding translation file.

These are the general steps, and the specific implementation may vary based on your application's structure and requirements. Be sure to refer to the PyQt6 documentation for more detailed information and sample code. Additionally, using version control systems like Git to track translation files and work on translations is a good practice.

---

`pylupdate6` is a tool used to extract text strings from Python applications and generate translation files. Here's an example demonstrating how to use `pylupdate6`:

Assuming you have a simple Python application that includes text strings that need to be translated. First, make sure that your application uses the `tr()` function to mark these text strings for translation, as mentioned earlier.

Suppose your Python application code looks like this:

```python
# myapp.py

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        button = QPushButton("Click me", self)
        button.clicked.connect(self.onClick)

    def onClick(self):
        print("Button clicked")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec())
```

To use `pylupdate6` to extract text strings from this application, you can follow these steps:

1. Ensure that your application's code uses the `tr()` function to mark text that needs to be translated.

2. Open a terminal and navigate to the directory containing your application's code.

3. Run the following command to generate a `.ts` file:

   ```bash
   pylupdate6 main.py -ts zh_CN.ts
   ```

   This will extract text strings marked with `tr()` from `myapp.py` and save them in the `zh_CN.ts` file.

4. You can use the Qt Linguist tool to open the `zh_CN.ts` file and provide translations for each extracted text string.

5. Once the translations are completed, use the `lrelease` tool to compile the `.ts` file into binary `.qm` files, which are needed at runtime.

   ```bash
   lrelease zh_CN.ts
   ```

Now, your application is ready to support internationalization, and it can display translated text based on the user's preferred language. Make sure to distribute the `.qm` files along with your application and load the appropriate translation file at runtime.