with open("src/components/WarRoomDashboard.jsx", "r") as f:
    lines = f.readlines()

new_lines = []
seen_imports = set()

for line in lines:
    if line.startswith("import "):
        if line in seen_imports:
            continue
        seen_imports.add(line)
    new_lines.append(line)

with open("src/components/WarRoomDashboard.jsx", "w") as f:
    f.writelines(new_lines)
