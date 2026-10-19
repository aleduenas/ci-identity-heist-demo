"""Export metadata from the running local realm, including its real public certificate."""
import argparse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("identity/generated/metadata.xml"))
    args = parser.parse_args()
    url = "http://localhost:8081/realms/mybank/protocol/saml/descriptor"
    with urllib.request.urlopen(url, timeout=15) as response:
        metadata = response.read(1_000_001)
    if len(metadata) > 1_000_000:
        raise ValueError("Unexpected metadata size")
    root = ElementTree.fromstring(metadata)
    certificate = root.find(".//{http://www.w3.org/2000/09/xmldsig#}X509Certificate")
    if certificate is None or not certificate.text:
        raise ValueError("Running realm did not publish a signing certificate")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(metadata)
    print(f"Exported live realm metadata to {args.output}")


if __name__ == "__main__":
    main()
