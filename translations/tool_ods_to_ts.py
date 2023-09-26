import xml.etree.ElementTree as ET
import pyexcel_ods
from io import BytesIO

# Specify the path to your ODS file
ods_file = "zh_CN.ods"

# Load the ODS file using pyexcel-ods
ods_data = pyexcel_ods.get_data(ods_file)
data = ods_data["Sheet 1"]

# Create an ElementTree for the .ts structure
root = ET.Element("TS")
root.set("version", "2.1")
root.set("language", "zh_CN")
root.set("sourcelanguage", "en_US")

current_context = None
context_elem = None

# Iterate through the data and create XML structure
for row in data:
    if len(row) < 3 or row[0] == "Context" or not row[1]:
        continue  # Skip rows without enough columns or header row

    context_name, source, translation = map(str.strip, row)

    if current_context != context_name:
        context_elem = ET.SubElement(root, "context")
        name_elem = ET.SubElement(context_elem, "name")
        name_elem.text = context_name
        current_context = context_name

    message_elem = ET.SubElement(context_elem, "message")
    source_elem = ET.SubElement(message_elem, "source")
    source_elem.text = source

    if translation:
        translation_elem = ET.SubElement(message_elem, "translation")
        translation_elem.text = translation

# Create an ElementTree from the root
tree = ET.ElementTree(root)

# Save the ElementTree as a .ts file
ts_file = ods_file.replace(".ods", ".ts")
tree.write(ts_file, encoding="utf-8", xml_declaration=True)
print(f"Converted {ods_file} to {ts_file}")
