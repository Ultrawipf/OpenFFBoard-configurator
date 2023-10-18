'''
Please install:
pip install pyexcel_ods
and change the ts_file variable to the path of the ts file you want to convert.
'''
ts_file = "zh_CN.ts"

import xml.etree.ElementTree as ET
import pyexcel_ods
from io import BytesIO

# Load the .ts file using ElementTree
tree = ET.parse(ts_file)
root = tree.getroot()

# Initialize lists to store extracted data
context_list = []
source_list = []
translation_list = []

# Extract data from the XML tree
for context in root.findall(".//context"):
    context_name = context.find("name").text.strip()
    for message in context.findall(".//message"):
        source = message.find("source").text.strip()
        translation_elem = message.find("translation")
        translation = translation_elem.text.strip() if translation_elem is not None and translation_elem.text is not None else ""
        
        context_list.append(context_name)
        source_list.append(source)
        translation_list.append(translation)

# Create a dictionary with the extracted data
data = {
    "Context": context_list,
    "Source": source_list,
    "Translation": translation_list
}

# Create a BytesIO stream to write ODS content
ods_stream = BytesIO()

# Save the data to an ODS file using pyexcel-ods
pyexcel_ods.save_data(ods_stream, {"Sheet 1": [list(data.keys())] + list(zip(*data.values()))})

# Save the BytesIO stream to an ODS file
ods_file = ts_file.replace(".ts", ".ods")
with open(ods_file, "wb") as f:
    f.write(ods_stream.getvalue())

print(f"Converted {ts_file} to {ods_file}")
