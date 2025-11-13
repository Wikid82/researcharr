"""Small helper to extract a test file ordering from a junit XML.

This tool is only used during triage. It uses defusedxml to avoid
vulnerable stdlib XML parsing (Bandit B405/B314) and writes its output
into the system temp directory.
"""

import logging
import os
import tempfile

import defusedxml
from defusedxml import ElementTree

# Ensure stdlib XML parsers are defused before any parsing occurs.
defusedxml.defuse_stdlib()

logging.basicConfig(level=logging.INFO)

P = "artifacts/pairwise/random_12.xml"


def main(xml_path: str = P) -> str:
    tree = ElementTree.parse(xml_path)
    root = tree.getroot()
    files = []
    for tc in root.findall(".//testcase"):
        cls = tc.get("classname")
        if not cls:
            continue
        path = cls.replace(".", "/") + ".py"
        files.append(path)
        if tc.find("failure") is not None:
            break

    out_path = os.path.join(tempfile.gettempdir(), "ordering.txt")
    with open(out_path, "w") as fh:
        fh.write("\n".join(files))

    logging.info("Wrote %s with %d files", out_path, len(files))
    return out_path


if __name__ == "__main__":
    main()
