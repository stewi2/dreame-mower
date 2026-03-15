import argparse
import getpass
import json
import os
import sys

# Add parent directory to sys.path to allow imports from custom_components
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from custom_components.dreame_mower.dreame.cloud.cloud_device import DreameMowerCloudDevice

VALID_COUNTRIES = ["eu", "cn", "us", "ru", "sg"]
VALID_ACCOUNT_TYPES = ["dreame", "mova"]


def _prompt_country() -> str:
    options = ", ".join(VALID_COUNTRIES)
    while True:
        val = input(f"Region [{options}] (default: eu): ").strip() or "eu"
        if val in VALID_COUNTRIES:
            return val
        print(f"Invalid region. Choose one of: {options}")


def _prompt_account_type() -> str:
    options = ", ".join(VALID_ACCOUNT_TYPES)
    while True:
        val = input(f"Account type [{options}] (default: dreame): ").strip() or "dreame"
        if val in VALID_ACCOUNT_TYPES:
            return val
        print(f"Invalid account type. Choose one of: {options}")

def main():
    parser = argparse.ArgumentParser(description="List Dreame devices for your account")
    parser.add_argument("--username", default=None, help="Cloud username (email); prompted if omitted")
    parser.add_argument("--country", default=None, choices=VALID_COUNTRIES, help=f"Cloud region ({', '.join(VALID_COUNTRIES)}); default: eu")
    parser.add_argument("--account-type", default=None, choices=VALID_ACCOUNT_TYPES, help=f"Account type ({', '.join(VALID_ACCOUNT_TYPES)}); default: dreame")
    args = parser.parse_args()

    if args.username is None:
        args.username = input("Username (email): ")
    args.password = getpass.getpass("Password: ")
    if args.country is None:
        args.country = _prompt_country()
    if args.account_type is None:
        args.account_type = _prompt_account_type()

    # Create DreameMowerCloudDevice with minimal info
    protocol = DreameMowerCloudDevice(
        username=args.username,
        password=args.password,
        country=args.country,
        account_type=args.account_type,
        device_id=""  # Empty device_id for listing devices
    )

    protocol._cloud_base.connect()
    devices = protocol._cloud_base.get_devices()
    print(json.dumps(devices, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
